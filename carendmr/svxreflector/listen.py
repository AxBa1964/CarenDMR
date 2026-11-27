"""Konsolen-Empfang im FM-Funknetz: ``python main.py --fm-listen``.

Meldet sich an, wählt die Talkgroup (Vorgabe 20 „Testarea“), sagt an, wer
spricht, und gibt den Ton aus. Sendet nichts.
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

from . import protocol as p
from .client import (
    AudioFlushed,
    AudioPacket,
    Connected,
    Disconnected,
    FmConnectionError,
    SvxReflectorClient,
)
from .config import FmConfigError, FmFunknetzConfig, load_fm_config
from .opus import OpusDecoder, OpusError, OpusUnavailableError

MAX_LISTEN_SECONDS = 3600.0


@dataclass
class FmListenStats:
    talker_starts: int = 0
    audio_packets: int = 0
    decoded_samples: int = 0
    concealed_frames: int = 0
    decode_errors: int = 0
    talkers: list[str] = field(default_factory=list)
    disconnect_reason: str = ""


def _fmt_seconds(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


class FmReceiver:
    """Verbindet Client, Opus-Decoder und Ausgabe (ohne Konsole testbar)."""

    def __init__(
        self,
        config: FmFunknetzConfig,
        *,
        decoder: OpusDecoder,
        output,  # BufferedPcmOutput-ähnlich: start(), write(samples), close()
        say: Callable[[str], None] = print,
        client_factory=SvxReflectorClient,
    ) -> None:
        self.config = config
        self.stats = FmListenStats()
        self._decoder = decoder
        self._output = output
        self._say = say
        self._events: "queue.Queue[object]" = queue.Queue()
        self._client = client_factory(config, self._events.put)
        self._talker: str | None = None
        self._talker_since = 0.0
        self.disconnected = threading.Event()

    def start(self) -> Connected:
        connected = self._client.connect()
        self._output.start()
        return connected

    def process(self, timeout: float = 0.2) -> None:
        """Verarbeitet anstehende Ereignisse (im Haupt-Thread aufrufen)."""
        try:
            event = self._events.get(timeout=timeout)
        except queue.Empty:
            return
        self._handle(event)
        while True:
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                return
            self._handle(event)

    def _handle(self, event: object) -> None:
        if isinstance(event, Connected):
            self._say(
                f"Angemeldet als {self.config.callsign} bei {self.config.host}, "
                f"Talkgroup {event.talkgroup}."
            )
        elif isinstance(event, p.TalkerStart):
            if event.callsign == self.config.callsign:
                return
            if event.talkgroup not in (0, self._client.talkgroup):
                return
            self._talker = event.callsign
            self._talker_since = time.monotonic()
            self.stats.talker_starts += 1
            self.stats.talkers.append(event.callsign)
            self._say(f"{event.callsign} spricht (Talkgroup {event.talkgroup or self._client.talkgroup}).")
        elif isinstance(event, p.TalkerStop):
            if event.callsign != self._talker:
                return
            duration = time.monotonic() - self._talker_since
            self._say(f"{event.callsign} fertig nach {_fmt_seconds(duration)} Sekunden.")
            self._talker = None
        elif isinstance(event, p.RequestQsy):
            self._say(f"Der Server wechselt auf Talkgroup {event.talkgroup}.")
        elif isinstance(event, AudioPacket):
            self.stats.audio_packets += 1
            try:
                for _ in range(event.lost_before):
                    self._output.write(self._decoder.decode(None))
                    self.stats.concealed_frames += 1
                samples = self._decoder.decode(event.opus)
            except OpusError:
                self.stats.decode_errors += 1
                return
            self.stats.decoded_samples += len(samples)
            self._output.write(samples)
        elif isinstance(event, AudioFlushed):
            pass
        elif isinstance(event, Disconnected):
            self.stats.disconnect_reason = event.reason
            self._say(f"Verbindung beendet: {event.reason}")
            self.disconnected.set()

    def close(self) -> None:
        self._client.close()
        try:
            self._output.close()
        finally:
            self._decoder.close()


def run_fm_listen(project_root: Path, *, seconds: float | None = None, talkgroup: int | None = None) -> int:
    """Konsolen-Ablauf. Rückgabe 0 = Anmeldung erfolgreich."""
    from carendmr.app_paths import native_dir
    from carendmr.audio.pcm_output import BufferedPcmOutput, PcmOutputError

    try:
        config = load_fm_config(project_root)
        if talkgroup is not None:
            config = replace(config, talkgroup=talkgroup)
            config.validate()
    except FmConfigError as error:
        print(str(error))
        return 2
    try:
        decoder = OpusDecoder(p.AUDIO_SAMPLE_RATE, native_dir=native_dir(project_root))
    except (OpusUnavailableError, OpusError) as error:
        print(str(error))
        return 2

    output = BufferedPcmOutput(sample_rate=p.AUDIO_SAMPLE_RATE)
    receiver = FmReceiver(config, decoder=decoder, output=output)
    print(f"Verbinde mit {config.host}:{config.port} als {config.callsign} …")
    print("Nur Empfang – es wird nichts gesendet. Ende mit Strg+C.")
    try:
        receiver.start()
    except FmConnectionError as error:
        print(f"Anmeldung fehlgeschlagen: {error}")
        receiver.close()
        return 2
    except PcmOutputError as error:
        print(f"Audioausgabe nicht möglich: {error}")
        receiver.close()
        return 2

    deadline = time.monotonic() + seconds if seconds else None
    try:
        while not receiver.disconnected.is_set():
            if deadline is not None and time.monotonic() >= deadline:
                break
            receiver.process(0.2)
    except KeyboardInterrupt:
        print("Abbruch mit Strg+C.")
    finally:
        receiver.close()

    stats = receiver.stats
    print("-" * 40)
    print(f"Sprechende Stationen : {stats.talker_starts}")
    print(f"Audiopakete          : {stats.audio_packets}")
    print(f"Verschleierte Pakete : {stats.concealed_frames}")
    print(f"Dekodierfehler       : {stats.decode_errors}")
    return 0 if not stats.disconnect_reason else 1
