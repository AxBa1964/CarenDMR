from pathlib import Path

import carendmr.encoder.md380_dynarmic as md380


def test_windows_bridge_name(monkeypatch):
    monkeypatch.setattr(md380.os, "name", "nt")
    monkeypatch.setattr(md380.sys, "platform", "win32")
    assert md380.default_md380_bridge_path(Path("/project")).name == "carendmr_md380_bridge.dll"


def test_macos_bridge_name(monkeypatch):
    monkeypatch.setattr(md380.os, "name", "posix")
    monkeypatch.setattr(md380.sys, "platform", "darwin")
    assert md380.default_md380_bridge_path(Path("/project")).name == "libcarendmr_md380_bridge.dylib"


def test_linux_bridge_name(monkeypatch):
    monkeypatch.setattr(md380.os, "name", "posix")
    monkeypatch.setattr(md380.sys, "platform", "linux")
    assert md380.default_md380_bridge_path(Path("/project")).name == "libcarendmr_md380_bridge.so"
