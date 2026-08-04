"""Leichtgewichtige, nicht blockierende Sprachführung für Caren Assist V1."""
from __future__ import annotations

import base64
import platform
import queue
import subprocess
from dataclasses import dataclass
from threading import Event, Lock, Thread
from typing import Callable

from carendmr.domain.information import InformationMessage


class SystemSpeechOutput:
    """Lokale System-TTS mit dauerhaftem Windows-SAPI-Prozess.

    Der Synthesizer bleibt geöffnet. Dadurch wird nicht bei jeder Meldung das
    Audiogerät neu initialisiert und der Satzanfang kann nicht mehr abgeschnitten
    werden.
    """

    _WINDOWS_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
while (($line = [Console]::In.ReadLine()) -ne $null) {
    if ($line -eq '__CAREN_CLOSE__') { break }
    try {
        $bytes = [Convert]::FromBase64String($line)
        $text = [System.Text.Encoding]::UTF8.GetString($bytes)
        if (-not [string]::IsNullOrWhiteSpace($text)) { $s.Speak($text) }
    } catch { }
}
$s.Dispose()
"""

    def __init__(self) -> None:
        self._lock = Lock()
        self._windows_process: subprocess.Popen[str] | None = None

    def _ensure_windows_process(self) -> subprocess.Popen[str]:
        process = self._windows_process
        if process is not None and process.poll() is None and process.stdin is not None:
            return process
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", self._WINDOWS_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._windows_process = process
        return process

    def speak(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        system = platform.system()
        if system == "Windows":
            encoded = base64.b64encode(cleaned.encode("utf-8")).decode("ascii")
            with self._lock:
                process = self._ensure_windows_process()
                assert process.stdin is not None
                try:
                    process.stdin.write(encoded + "\n")
                    process.stdin.flush()
                except (BrokenPipeError, OSError):
                    self._windows_process = None
                    process = self._ensure_windows_process()
                    assert process.stdin is not None
                    process.stdin.write(encoded + "\n")
                    process.stdin.flush()
        elif system == "Darwin":
            subprocess.run(["say", cleaned], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def close(self) -> None:
        with self._lock:
            process = self._windows_process
            self._windows_process = None
            if process is None or process.poll() is not None or process.stdin is None:
                return
            try:
                process.stdin.write("__CAREN_CLOSE__\n")
                process.stdin.flush()
                process.stdin.close()
            except OSError:
                pass


@dataclass(frozen=True)
class _SpeechRequest:
    text: str
    done: Event | None = None
    kind: str = "general"


class AsyncCarenAssist:
    """Priorisierte TTS-Queue für den Funkbetrieb.

    Kurze TX/RX-Ansagen können mit einem Abschlussereignis synchronisiert werden.
    Interne Verbindungs-Zwischenzustände werden bewusst nicht automatisch
    gesprochen, damit laufender Funkverkehr nicht überlagert wird.
    """

    DEFAULT_CODES = {
        "system.ready",
        "connection.connected",
        "connection.error",
        "operation.talkgroup.changed",
        "operation.timeslot.changed",
        "operation.call_type.changed",
    }

    def __init__(self, *, enabled: Callable[[], bool], output: SystemSpeechOutput | None = None,
                 allowed_codes: set[str] | None = None) -> None:
        self._enabled = enabled
        self._output = output or SystemSpeechOutput()
        self._allowed_codes = allowed_codes or set(self.DEFAULT_CODES)
        self._queue: queue.Queue[_SpeechRequest | None] = queue.Queue(maxsize=32)
        self._stop = Event()
        self._thread = Thread(target=self._worker, name="CarenAssist-TTS", daemon=True)
        self._thread.start()

    def __call__(self, message: InformationMessage) -> None:
        if not self._enabled() or message.code not in self._allowed_codes:
            return
        self.say(message.speech_text)

    def clear_pending(self, *, kind: str | None = None) -> int:
        removed = 0
        retained: list[_SpeechRequest | None] = []
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            if item is None:
                retained.append(item)
                continue
            if kind is not None and item.kind != kind:
                retained.append(item)
                continue
            if item.done is not None:
                item.done.set()
            removed += 1
        for item in retained:
            try:
                self._queue.put_nowait(item)
            except queue.Full:
                if isinstance(item, _SpeechRequest) and item.done is not None:
                    item.done.set()
        return removed

    def say(self, text: str, *, replace_pending: bool = False) -> None:
        if not self._enabled() or not text.strip():
            return
        if replace_pending:
            self.clear_pending()
        self._enqueue(text.strip(), None, kind="general")

    def say_and_wait(self, text: str, *, replace_pending: bool = True) -> Event:
        done = Event()
        if not self._enabled() or not text.strip():
            done.set()
            return done
        if replace_pending:
            self.clear_pending()
        self._enqueue(text.strip(), done, kind="general")
        return done

    def say_focus(self, text: str) -> None:
        """Koalesziert schnelle Fokuswechsel auf die zuletzt erreichte Position."""
        if not self._enabled() or not text.strip():
            return
        self.clear_pending(kind="focus")
        self._enqueue(text.strip(), None, kind="focus")

    def _enqueue(self, text: str, done: Event | None, *, kind: str) -> None:
        try:
            self._queue.put_nowait(_SpeechRequest(text=text, done=done, kind=kind))
        except queue.Full:
            try:
                old = self._queue.get_nowait()
                if isinstance(old, _SpeechRequest) and old.done is not None:
                    old.done.set()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(_SpeechRequest(text=text, done=done, kind=kind))
            except queue.Full:
                if done is not None:
                    done.set()

    def close(self) -> None:
        self._stop.set()
        self.clear_pending()
        close_output = getattr(self._output, "close", None)
        if callable(close_output):
            close_output()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass

    def _worker(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue
            if item is None:
                return
            text, done = item.text, item.done
            try:
                self._output.speak(text)
            except Exception:
                pass
            finally:
                if done is not None:
                    done.set()
