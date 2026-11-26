"""Bedien-Tastenfeld (Pico 2 H, USB-CDC seriell) – Qt-frei.

Das Tastenfeld meldet Tastendrücke als Textzeilen über eine serielle
USB-Schnittstelle (CDC). Dieser Dienst

* sucht das Gerät (Handshake ``HELLO`` → ``HELLO CARENKEY <version>``),
* liest die Zeilen ``KEY <n> DOWN|UP|LONG`` in einem Hintergrund-Thread,
* übersetzt Tastennummern über ``config/keypad.local.json`` in Aktionen und
* schickt Quittungen zurück (``ACK``, ``ERR``, ``VIB``, ``TONE``).

Er bedient den Funk nicht selbst. Die Oberfläche bekommt nur
``KeypadEvent``-Objekte und führt sie über den ``OperatingController`` aus.
Der Rückruf kommt aus dem Lese-Thread; die Oberfläche muss ihn in ihren
eigenen Thread übergeben.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Callable, Iterable, Protocol, Sequence

from carendmr.domain import FavoriteChannel

# Aktionen, die eine Taste auslösen kann.
ACTION_PTT = "ptt"
ACTION_VOLUME_UP = "volume_up"
ACTION_VOLUME_DOWN = "volume_down"
ACTION_FAVORITE_NEXT = "favorite_next"
ACTION_FAVORITE_PREVIOUS = "favorite_previous"
ACTION_FAVORITE_1 = "favorite_1"
ACTION_FAVORITE_2 = "favorite_2"
ACTION_FAVORITE_3 = "favorite_3"
ACTION_FAVORITE_4 = "favorite_4"
ACTION_CONNECT = "connect"
ACTION_DISCONNECT = "disconnect"
ACTION_EXIT = "exit"

KNOWN_ACTIONS = frozenset({
    ACTION_PTT, ACTION_VOLUME_UP, ACTION_VOLUME_DOWN,
    ACTION_FAVORITE_NEXT, ACTION_FAVORITE_PREVIOUS,
    ACTION_FAVORITE_1, ACTION_FAVORITE_2, ACTION_FAVORITE_3, ACTION_FAVORITE_4,
    ACTION_CONNECT, ACTION_DISCONNECT, ACTION_EXIT,
})

# Aktionen, die nur bei langem Druck auslösen (Schutz gegen Versehen).
LONG_PRESS_ACTIONS = frozenset({ACTION_EXIT})

# Tastennummer = Index in der Pinliste der Firmware (hardware/keypad/pins.py).
DEFAULT_KEY_MAP: dict[int, str] = {
    0: ACTION_PTT,
    1: ACTION_VOLUME_UP,
    2: ACTION_VOLUME_DOWN,
    3: ACTION_FAVORITE_NEXT,
    4: ACTION_FAVORITE_PREVIOUS,
    5: ACTION_FAVORITE_1,
    6: ACTION_FAVORITE_2,
    7: ACTION_FAVORITE_3,
    8: ACTION_FAVORITE_4,
    9: ACTION_CONNECT,
    10: ACTION_DISCONNECT,
    11: ACTION_EXIT,
}

DEFAULT_LONG_PRESS_SECONDS = 2.0
DEFAULT_BAUDRATE = 115200
# USB-Hersteller-ID von Raspberry Pi (Pico, Pico 2) – nur für die Vorauswahl.
RASPBERRY_PI_USB_VID = 0x2E8A
HELLO_PREFIX = "HELLO CARENKEY"


# --- Konfiguration --------------------------------------------------------

@dataclass(frozen=True)
class KeypadConfig:
    enabled: bool = True
    port: str = "auto"
    baudrate: int = DEFAULT_BAUDRATE
    long_press_seconds: float = DEFAULT_LONG_PRESS_SECONDS
    keys: dict[int, str] = field(default_factory=lambda: dict(DEFAULT_KEY_MAP))

    @classmethod
    def from_dict(cls, raw: object) -> "KeypadConfig":
        if not isinstance(raw, dict):
            return cls()
        keys = dict(DEFAULT_KEY_MAP)
        raw_keys = raw.get("keys")
        if isinstance(raw_keys, dict):
            keys = {}
            for number, action in raw_keys.items():
                try:
                    index = int(number)
                except (TypeError, ValueError):
                    continue
                action = str(action).strip().lower()
                if index >= 0 and action in KNOWN_ACTIONS:
                    keys[index] = action
        try:
            long_press = float(raw.get("long_press_seconds", DEFAULT_LONG_PRESS_SECONDS))
        except (TypeError, ValueError):
            long_press = DEFAULT_LONG_PRESS_SECONDS
        try:
            baudrate = int(raw.get("baudrate", DEFAULT_BAUDRATE))
        except (TypeError, ValueError):
            baudrate = DEFAULT_BAUDRATE
        port = str(raw.get("port", "auto") or "auto").strip() or "auto"
        return cls(
            enabled=bool(raw.get("enabled", True)),
            port=port,
            baudrate=baudrate if baudrate > 0 else DEFAULT_BAUDRATE,
            long_press_seconds=min(10.0, max(0.5, long_press)),
            keys=keys,
        )

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "port": self.port,
            "baudrate": self.baudrate,
            "long_press_seconds": self.long_press_seconds,
            "keys": {str(number): action for number, action in sorted(self.keys.items())},
        }


def load_keypad_config(config_dir: Path) -> KeypadConfig:
    """Liest ``keypad.local.json``; fehlt sie, gelten die Vorgaben."""
    path = Path(config_dir) / "keypad.local.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return KeypadConfig()
    return KeypadConfig.from_dict(raw)


# --- Protokoll ------------------------------------------------------------

@dataclass(frozen=True)
class KeyMessage:
    key: int
    kind: str  # "down", "up", "long"


def parse_line(line: str) -> KeyMessage | str | None:
    """``KEY n DOWN|UP|LONG`` → KeyMessage, ``HELLO CARENKEY x`` → Versionstext."""
    text = str(line).strip()
    if not text:
        return None
    if text.upper().startswith(HELLO_PREFIX):
        return text[len(HELLO_PREFIX):].strip() or "?"
    parts = text.split()
    if len(parts) != 3 or parts[0].upper() != "KEY":
        return None
    try:
        key = int(parts[1])
    except ValueError:
        return None
    kind = parts[2].lower()
    if key < 0 or kind not in {"down", "up", "long"}:
        return None
    return KeyMessage(key, kind)


@dataclass(frozen=True)
class KeypadEvent:
    """Was die Oberfläche ausführen soll.

    ``phase`` ist ``"press"`` für einmalige Aktionen, bei PTT ``"down"`` bzw.
    ``"up"``.
    """

    action: str
    phase: str = "press"


class KeyActionMapper:
    """Übersetzt Tastenmeldungen in KeypadEvents."""

    def __init__(self, config: KeypadConfig) -> None:
        self.config = config

    def translate(self, message: KeyMessage) -> KeypadEvent | None:
        action = self.config.keys.get(message.key)
        if action is None:
            return None
        if action == ACTION_PTT:
            if message.kind in {"down", "up"}:
                return KeypadEvent(ACTION_PTT, message.kind)
            return None
        if action in LONG_PRESS_ACTIONS:
            return KeypadEvent(action) if message.kind == "long" else None
        return KeypadEvent(action) if message.kind == "down" else None


# --- Favoriten-Auswahl ----------------------------------------------------

class FavoriteSelector:
    """Blättert durch die Favoriten; wählt nur aus, verbindet nicht."""

    def __init__(self, favorites: Sequence[FavoriteChannel] = ()) -> None:
        self._favorites: tuple[FavoriteChannel, ...] = tuple(favorites)
        self._index: int | None = None

    def set_favorites(self, favorites: Sequence[FavoriteChannel]) -> None:
        self._favorites = tuple(favorites)
        if self._index is not None and self._index >= len(self._favorites):
            self._index = None

    @property
    def favorites(self) -> tuple[FavoriteChannel, ...]:
        return self._favorites

    @property
    def index(self) -> int | None:
        return self._index

    def sync_to(self, target: int, timeslot: int, call_type: str) -> None:
        """Merkt sich den Favoriten, der dem aktuellen Kanal entspricht."""
        for position, favorite in enumerate(self._favorites):
            if (favorite.target, favorite.timeslot, favorite.call_type) == (int(target), int(timeslot), str(call_type)):
                self._index = position
                return

    def select(self, number: int) -> FavoriteChannel | None:
        """Favorit 1, 2, 3 … (1-basiert); None, wenn nicht belegt."""
        position = int(number) - 1
        if not 0 <= position < len(self._favorites):
            return None
        self._index = position
        return self._favorites[position]

    def step(self, direction: int) -> FavoriteChannel | None:
        if not self._favorites:
            return None
        if self._index is None:
            self._index = 0 if direction >= 0 else len(self._favorites) - 1
        else:
            self._index = (self._index + (1 if direction >= 0 else -1)) % len(self._favorites)
        return self._favorites[self._index]


def favorite_announcement(favorite: FavoriteChannel, number: int | None = None) -> str:
    """Ansagetext, z. B. „Favorit 2, Papagei, Talkgroup 9 9 9 0, Privatruf.“"""
    digits = " ".join(str(favorite.target))
    call = "Privatruf" if favorite.call_type == "private" else "Gruppenruf"
    parts = []
    if number is not None:
        parts.append(f"Favorit {number}")
    name = favorite.display_name
    if name and name != str(favorite.target):
        parts.append(name)
    parts.append(f"Talkgroup {digits}")
    parts.append(f"Timeslot {favorite.timeslot}")
    parts.append(call)
    return ", ".join(parts) + "."


# --- Serielle Anbindung ---------------------------------------------------

class SerialLink(Protocol):
    def readline(self) -> bytes: ...
    def write(self, data: bytes) -> int | None: ...
    def close(self) -> None: ...


PortOpener = Callable[[str, int], SerialLink]
PortLister = Callable[[], Iterable[tuple[str, int | None]]]


def _pyserial_opener(port: str, baudrate: int) -> SerialLink:
    import serial  # pyserial

    return serial.Serial(port, baudrate=baudrate, timeout=0.2, write_timeout=0.5)


def _pyserial_lister() -> list[tuple[str, int | None]]:
    from serial.tools import list_ports  # pyserial

    return [(info.device, info.vid) for info in list_ports.comports()]


class KeypadService:
    """Verbindet sich mit dem Tastenfeld und meldet Tastenereignisse."""

    RECONNECT_SECONDS = 3.0
    HANDSHAKE_SECONDS = 1.5

    def __init__(
        self,
        config: KeypadConfig,
        *,
        opener: PortOpener | None = None,
        lister: PortLister | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self.mapper = KeyActionMapper(config)
        self._opener = opener or _pyserial_opener
        self._lister = lister or _pyserial_lister
        self._clock = clock
        self._link: SerialLink | None = None
        self._port: str | None = None
        self._firmware: str | None = None
        self._write_lock = Lock()
        self._stop = Event()
        self._thread: Thread | None = None
        self._on_event: Callable[[KeypadEvent], None] | None = None
        self._on_status: Callable[[bool, str], None] | None = None

    # Öffentliche Schnittstelle --------------------------------------------
    @property
    def connected(self) -> bool:
        return self._link is not None

    @property
    def port(self) -> str | None:
        return self._port

    @property
    def firmware_version(self) -> str | None:
        return self._firmware

    def start(
        self,
        on_event: Callable[[KeypadEvent], None],
        on_status: Callable[[bool, str], None] | None = None,
    ) -> bool:
        """Startet die Gerätesuche im Hintergrund. False, wenn abgeschaltet."""
        if not self.config.enabled or self._thread is not None:
            return False
        self._on_event = on_event
        self._on_status = on_status
        self._stop.clear()
        self._thread = Thread(target=self._run, name="CarenDMR-Keypad", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        self._close_link()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=2.0)

    def acknowledge(self, ok: bool = True) -> None:
        """Quittung am Tastenfeld: hoher Ton (OK) bzw. tiefer Doppelton mit Vibration."""
        self.send("ACK" if ok else "ERR")

    def vibrate(self, milliseconds: int) -> None:
        self.send(f"VIB {max(0, int(milliseconds))}")

    def tone(self, frequency_hz: int, milliseconds: int) -> None:
        self.send(f"TONE {max(0, int(frequency_hz))} {max(0, int(milliseconds))}")

    def send(self, command: str) -> bool:
        link = self._link
        if link is None:
            return False
        try:
            with self._write_lock:
                link.write((command.strip() + "\n").encode("ascii", "replace"))
            return True
        except Exception:
            self._drop_link("Tastenfeld getrennt.")
            return False

    # Gerätesuche ----------------------------------------------------------
    def candidate_ports(self) -> list[str]:
        if self.config.port.lower() != "auto":
            return [self.config.port]
        try:
            ports = list(self._lister())
        except Exception:
            return []
        # Nur Raspberry-Pi-Geräte ansprechen; fremde serielle Geräte (z. B.
        # Funkgeräte) bekommen kein HELLO. Andere Boards: Port fest eintragen.
        return [device for device, vid in ports if vid == RASPBERRY_PI_USB_VID]

    def connect_once(self) -> bool:
        """Sucht einmal nach dem Tastenfeld; True, wenn verbunden."""
        for port in self.candidate_ports():
            if self._stop.is_set():
                return False
            try:
                link = self._opener(port, self.config.baudrate)
            except Exception:
                continue
            version = self._handshake(link)
            if version is None:
                try:
                    link.close()
                except Exception:
                    pass
                continue
            self._link = link
            self._port = port
            self._firmware = version
            self.send(f"LONG {int(round(self.config.long_press_seconds * 1000))}")
            self._report_status(True, "Tastenfeld verbunden.")
            return True
        return False

    def _handshake(self, link: SerialLink) -> str | None:
        try:
            link.write(b"HELLO\n")
        except Exception:
            return None
        deadline = self._clock() + self.HANDSHAKE_SECONDS
        while self._clock() < deadline and not self._stop.is_set():
            try:
                raw = link.readline()
            except Exception:
                return None
            if not raw:
                continue
            parsed = parse_line(raw.decode("ascii", "replace"))
            if isinstance(parsed, str):
                return parsed
        return None

    def poll_once(self) -> None:
        """Liest eine Zeile und meldet das passende Ereignis."""
        link = self._link
        if link is None:
            return
        try:
            raw = link.readline()
        except Exception:
            self._drop_link("Tastenfeld getrennt.")
            return
        if not raw:
            return
        parsed = parse_line(raw.decode("ascii", "replace"))
        if isinstance(parsed, KeyMessage):
            event = self.mapper.translate(parsed)
            if event is not None and self._on_event is not None:
                self._on_event(event)
        elif isinstance(parsed, str):
            self._firmware = parsed

    def _run(self) -> None:
        while not self._stop.is_set():
            if self._link is None:
                if not self.connect_once():
                    self._stop.wait(self.RECONNECT_SECONDS)
                    continue
            self.poll_once()

    def _drop_link(self, message: str) -> None:
        was_connected = self._link is not None
        self._close_link()
        if was_connected and not self._stop.is_set():
            self._report_status(False, message)

    def _close_link(self) -> None:
        link = self._link
        self._link = None
        self._port = None
        if link is not None:
            try:
                link.close()
            except Exception:
                pass

    def _report_status(self, connected: bool, message: str) -> None:
        if self._on_status is not None:
            try:
                self._on_status(connected, message)
            except Exception:
                pass
