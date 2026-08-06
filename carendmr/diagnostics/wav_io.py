from __future__ import annotations

import wave
from pathlib import Path
from typing import BinaryIO


def open_wav_writer(path: Path) -> tuple[BinaryIO, wave.Wave_write]:
    """Open a WAV writer without leaving a half-initialized Wave_write on failure.

    Opening the raw file first avoids CPython's Wave_write.__del__ warning when
    creating the destination itself fails (for example due to OneDrive, access,
    or path errors).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = path.open("wb")
    try:
        writer = wave.open(raw, "wb")
    except Exception:
        raw.close()
        raise
    return raw, writer


def write_pcm16_mono(path: Path, sample_rate: int, pcm_bytes: bytes) -> None:
    raw, writer = open_wav_writer(path)
    try:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(int(sample_rate))
        writer.writeframes(pcm_bytes)
    finally:
        try:
            writer.close()
        finally:
            if not raw.closed:
                raw.close()
