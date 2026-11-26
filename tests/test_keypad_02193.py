"""0.2.1.93: Bedien-Tastenfeld (Pico H, USB-CDC) für CarenDMR Easy."""
from __future__ import annotations

import ast
import json
import tempfile
from pathlib import Path

from carendmr.application.keypad_service import (
    ACTION_CONNECT,
    ACTION_EXIT,
    ACTION_FAVORITE_1,
    ACTION_PTT,
    ACTION_VOLUME_UP,
    DEFAULT_KEY_MAP,
    RASPBERRY_PI_USB_VID,
    FavoriteSelector,
    KeyActionMapper,
    KeyMessage,
    KeypadConfig,
    KeypadEvent,
    KeypadService,
    favorite_announcement,
    load_keypad_config,
    parse_line,
)
from carendmr.domain import FavoriteChannel

ROOT = Path(__file__).resolve().parents[1]


class FakeLink:
    """Serielle Verbindung ohne Gerät: liefert vorgegebene Zeilen."""

    def __init__(self, lines=(), *, answer_hello=True):
        self.lines = [line.encode("ascii") for line in lines]
        self.answer_hello = answer_hello
        self.written: list[str] = []
        self.closed = False

    def readline(self) -> bytes:
        return self.lines.pop(0) if self.lines else b""

    def write(self, data: bytes) -> int:
        text = data.decode("ascii")
        self.written.append(text.strip())
        if text.strip() == "HELLO" and self.answer_hello:
            self.lines.insert(0, b"HELLO CARENKEY 1.0\n")
        return len(data)

    def close(self) -> None:
        self.closed = True


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self) -> float:
        self.value += 0.1
        return self.value


def _favorites():
    return [
        FavoriteChannel(91, 2, "group", "World-wide", "World-wide", position=0),
        FavoriteChannel(9990, 2, "private", "", "Papagei", position=1),
        FavoriteChannel(262, 2, "group", "Deutschland", "Deutschland", position=2),
    ]


# --- Protokoll ------------------------------------------------------------

def test_parse_key_lines_and_hello():
    assert parse_line("KEY 3 DOWN\n") == KeyMessage(3, "down")
    assert parse_line("key 11 long") == KeyMessage(11, "long")
    assert parse_line("HELLO CARENKEY 1.0") == "1.0"
    for junk in ("", "KEY x DOWN", "KEY 1 PRESS", "KEY -1 UP", "HALLO", "KEY 1"):
        assert parse_line(junk) is None


# --- Konfiguration --------------------------------------------------------

def test_default_key_map_matches_wish_of_26_11_2026():
    assert len(DEFAULT_KEY_MAP) == 12
    assert DEFAULT_KEY_MAP[0] == ACTION_PTT
    assert DEFAULT_KEY_MAP[11] == ACTION_EXIT
    assert KeypadConfig().long_press_seconds == 2.0


def test_example_json_equals_defaults():
    raw = json.loads((ROOT / "config" / "keypad.example.json").read_text(encoding="utf-8"))
    config = KeypadConfig.from_dict(raw)
    assert config.keys == DEFAULT_KEY_MAP
    assert config.port == "auto"
    assert config.long_press_seconds == 2.0


def test_config_ignores_unknown_actions_and_clamps_long_press():
    config = KeypadConfig.from_dict(
        {"keys": {"0": "ptt", "1": "rm -rf", "x": "connect"}, "long_press_seconds": 99}
    )
    assert config.keys == {0: ACTION_PTT}
    assert config.long_press_seconds == 10.0


def test_missing_local_file_uses_defaults():
    with tempfile.TemporaryDirectory() as folder:
        assert load_keypad_config(Path(folder)) == KeypadConfig()


# --- Tasten → Aktionen ----------------------------------------------------

def test_ptt_reports_down_and_up():
    mapper = KeyActionMapper(KeypadConfig())
    assert mapper.translate(KeyMessage(0, "down")) == KeypadEvent(ACTION_PTT, "down")
    assert mapper.translate(KeyMessage(0, "up")) == KeypadEvent(ACTION_PTT, "up")
    assert mapper.translate(KeyMessage(0, "long")) is None


def test_exit_only_on_long_press():
    mapper = KeyActionMapper(KeypadConfig())
    assert mapper.translate(KeyMessage(11, "down")) is None
    assert mapper.translate(KeyMessage(11, "up")) is None
    assert mapper.translate(KeyMessage(11, "long")) == KeypadEvent(ACTION_EXIT)


def test_other_keys_fire_once_on_press():
    mapper = KeyActionMapper(KeypadConfig())
    assert mapper.translate(KeyMessage(1, "down")) == KeypadEvent(ACTION_VOLUME_UP)
    assert mapper.translate(KeyMessage(1, "up")) is None
    assert mapper.translate(KeyMessage(1, "long")) is None
    assert mapper.translate(KeyMessage(9, "down")) == KeypadEvent(ACTION_CONNECT)
    assert mapper.translate(KeyMessage(5, "down")) == KeypadEvent(ACTION_FAVORITE_1)
    assert mapper.translate(KeyMessage(42, "down")) is None


# --- Favoriten ------------------------------------------------------------

def test_favorite_selector_direct_and_stepping_wraps():
    selector = FavoriteSelector(_favorites())
    assert selector.select(2).target == 9990
    assert selector.select(4) is None  # nicht belegt
    assert selector.index == 1
    assert selector.step(+1).target == 262
    assert selector.step(+1).target == 91  # rundherum
    assert selector.step(-1).target == 262


def test_favorite_selector_starts_at_current_channel():
    selector = FavoriteSelector(_favorites())
    selector.sync_to(9990, 2, "private")
    assert selector.step(+1).target == 262


def test_favorite_selector_without_favorites():
    selector = FavoriteSelector(())
    assert selector.step(+1) is None
    assert selector.select(1) is None


def test_announcement_names_favorite_digits_and_call_type():
    text = favorite_announcement(_favorites()[1], 2)
    assert text == "Favorit 2, Papagei, Talkgroup 9 9 9 0, Timeslot 2, Privatruf."


# --- Serielle Anbindung ---------------------------------------------------

def _service(link, ports=(("COM7", RASPBERRY_PI_USB_VID),), config=None):
    opened = []

    def opener(port, baudrate):
        opened.append((port, baudrate))
        return link

    service = KeypadService(
        config or KeypadConfig(), opener=opener, lister=lambda: list(ports), clock=FakeClock()
    )
    return service, opened


def test_connect_with_handshake_sends_long_press_time():
    link = FakeLink()
    service, opened = _service(link)
    status = []
    service._on_status = lambda ok, message: status.append((ok, message))
    assert service.connect_once()
    assert opened == [("COM7", 115200)]
    assert service.connected and service.port == "COM7"
    assert service.firmware_version == "1.0"
    assert link.written[:2] == ["HELLO", "LONG 2000"]
    assert status == [(True, "Tastenfeld verbunden.")]


def test_only_raspberry_pi_ports_are_probed_in_auto_mode():
    service, opened = _service(FakeLink(), ports=(("COM3", 0x1234), ("COM4", None)))
    assert not service.connect_once()
    assert opened == []


def test_fixed_port_is_used_as_configured():
    service, opened = _service(FakeLink(), ports=(), config=KeypadConfig(port="COM9"))
    assert service.connect_once()
    assert opened == [("COM9", 115200)]


def test_device_without_hello_answer_is_closed():
    link = FakeLink(answer_hello=False)
    service, _ = _service(link)
    assert not service.connect_once()
    assert link.closed and not service.connected


def test_key_lines_become_events_and_ack_is_sent():
    link = FakeLink()
    service, _ = _service(link)
    events = []
    service._on_event = events.append
    service.connect_once()
    link.lines += [b"KEY 0 DOWN\n", b"KEY 0 UP\n", b"KEY 11 LONG\n"]
    for _ in range(3):
        service.poll_once()
    assert events == [
        KeypadEvent(ACTION_PTT, "down"),
        KeypadEvent(ACTION_PTT, "up"),
        KeypadEvent(ACTION_EXIT),
    ]
    service.acknowledge(True)
    service.acknowledge(False)
    assert link.written[-2:] == ["ACK", "ERR"]


def test_read_error_reports_disconnect():
    class BrokenLink(FakeLink):
        def readline(self):
            if self.lines:
                return self.lines.pop(0)
            raise OSError("USB abgezogen")

    link = BrokenLink()
    service, _ = _service(link)
    status = []
    service._on_status = lambda ok, message: status.append((ok, message))
    service.connect_once()
    service.poll_once()
    assert not service.connected and link.closed
    assert status[-1] == (False, "Tastenfeld getrennt.")
    assert service.send("ACK") is False


def test_disabled_keypad_does_not_start():
    service, _ = _service(FakeLink(), config=KeypadConfig(enabled=False))
    assert service.start(lambda event: None) is False


def test_service_module_is_qt_free():
    source = (ROOT / "carendmr" / "application" / "keypad_service.py").read_text(encoding="utf-8")
    assert "PySide6" not in source
    # pyserial wird erst beim Öffnen geladen – Easy startet auch ohne.
    tree = ast.parse(source)
    top_level = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert all("serial" not in ast.dump(node) for node in top_level)


# --- Bootstrap und Easy ---------------------------------------------------

def test_bootstrap_builds_easy_services():
    source = (ROOT / "carendmr" / "bootstrap.py").read_text(encoding="utf-8")
    assert "def build_easy_services(core: RadioCore) -> EasyServices:" in source
    assert 'FavoriteService(config / "favorites.local.json")' in source
    assert "KeypadService(load_keypad_config(config))" in source


def _easy() -> str:
    return (ROOT / "carendmr" / "ui_qt" / "easy_window.py").read_text(encoding="utf-8")


def test_easy_takes_keypad_from_bootstrap_and_creates_no_services():
    text = _easy()
    assert "services or build_easy_services(self.radio_core)" in text
    assert "KeypadService(" not in text
    assert "FavoriteService(" not in text


def test_easy_passes_keypad_events_to_qt_thread():
    text = _easy()
    assert 'self._updates.put(("keypad", event))' in text
    assert 'elif kind == "keypad":' in text
    assert "self._handle_keypad_event(value)" in text


def test_easy_ptt_hold_to_talk_and_stop_on_keypad_loss():
    text = _easy()
    assert 'self._keypad_ptt(event.phase == "down")' in text
    assert "if not connected and self._keypad_ptt_held:" in text
    assert "self._cancel_pending_tx()" in text
    assert "self._stop_tx()" in text


def test_easy_favorites_only_select_and_announce():
    text = _easy()
    body = text.split("def _keypad_apply_favorite", 1)[1].split("\n    def ", 1)[0]
    assert "self._connect" not in body
    assert "favorite_announcement(favorite, number)" in body
    assert "Zum Wechseln der Talkgroup erst trennen." in text


def test_easy_exit_and_close_stop_keypad():
    text = _easy()
    assert "self.keypad.stop()" in text
    assert "if event.action == ACTION_EXIT:" in text


def test_firmware_files_present_and_match_protocol():
    folder = ROOT / "hardware" / "keypad"
    code = (folder / "code.py").read_text(encoding="utf-8")
    pins = (folder / "pins.py").read_text(encoding="utf-8")
    boot = (folder / "boot.py").read_text(encoding="utf-8")
    for source in (code, pins, boot):
        ast.parse(source)
    assert "usb_cdc.enable(console=True, data=True)" in boot
    assert '"HELLO CARENKEY "' in code
    assert '"KEY %d LONG"' in code
    assert pins.count("board.GP") == len(DEFAULT_KEY_MAP) + 3
