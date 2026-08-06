from pathlib import Path
import wave

import pytest

from carendmr.diagnostics.wav_io import write_pcm16_mono


def test_write_pcm16_mono_creates_valid_wav(tmp_path: Path) -> None:
    path = tmp_path / "audio.wav"
    write_pcm16_mono(path, 8000, b"\x00\x00" * 160)
    with wave.open(str(path), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 8000
        assert wav_file.getnframes() == 160


def test_write_pcm16_mono_does_not_construct_wave_writer_when_raw_open_fails(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "audio.wav"
    calls = []

    def fail_open(self, *args, **kwargs):
        raise PermissionError("blocked")

    monkeypatch.setattr(Path, "open", fail_open)
    monkeypatch.setattr(wave, "open", lambda *args, **kwargs: calls.append(args))

    with pytest.raises(PermissionError):
        write_pcm16_mono(target, 8000, b"\x00\x00")
    assert calls == []
