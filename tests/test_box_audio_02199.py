"""0.2.1.99: Box-Web Audio – Lautstärke/Mikrofonpegel und Geräteauswahl."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from carendmr.box.audio_settings import BoxAudioSettings, BoxAudioSettingsError
from carendmr.box.web.app import SESSION_COOKIE, BoxWebApp, Request
from carendmr.box.web.auth import AdminAuth, SessionStore


# ---------------------------------------------------------- Lautstärke

def test_defaults_without_file(tmp_path):
    settings = BoxAudioSettings(tmp_path)
    assert settings.output_volume_percent() == 100
    assert settings.microphone_gain_percent() == 100


def test_save_and_reload(tmp_path):
    settings = BoxAudioSettings(tmp_path)
    settings.save(output_volume_percent=150, microphone_gain_percent=80)
    again = BoxAudioSettings(tmp_path)
    assert again.output_volume_percent() == 150 and again.microphone_gain_percent() == 80


def test_save_merges_other_keys(tmp_path):
    path = tmp_path / "config" / "audio_send.local.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"tx_safety_limit_seconds": 300, "output_volume_percent": 100}))
    BoxAudioSettings(tmp_path).save(output_volume_percent=120, microphone_gain_percent=90)
    data = json.loads(path.read_text())
    assert data["tx_safety_limit_seconds"] == 300 and data["output_volume_percent"] == 120


def test_out_of_range_refused(tmp_path):
    with pytest.raises(BoxAudioSettingsError, match="Lautstärke"):
        BoxAudioSettings(tmp_path).save(output_volume_percent=500, microphone_gain_percent=100)
    with pytest.raises(BoxAudioSettingsError, match="Zahl"):
        BoxAudioSettings(tmp_path).save(output_volume_percent="laut", microphone_gain_percent=100)


# --------------------------------------------------------------- Web

class FakeAudio:
    def __init__(self, project_root):
        from carendmr.application.audio_setup_service import AudioChoice

        self._in = [AudioChoice("mic1", "USB-Mikrofon")]
        self._out = [AudioChoice("spk1", "USB-Lautsprecher")]
        self.saved = None
        self.tested = None

    def scan(self):
        return list(self._in), list(self._out)

    def current_keys(self):
        return "mic1", "spk1"

    def save(self, input_key, output_key):
        if input_key not in ("mic1",) or output_key not in ("spk1",):
            raise ValueError("Gerät nicht vorhanden.")
        self.saved = (input_key, output_key)

    def play_test_tone(self, output_key):
        self.tested = output_key


def _app(tmp_path, *, audio_factory):
    app = BoxWebApp(tmp_path, auth=AdminAuth(tmp_path), sessions=SessionStore(),
                    audio_factory=audio_factory)
    token = app.handle(Request("POST", "/anmelden", {
        "first_time": "1", "password": "geheim1", "password2": "geheim1"})).set_cookie
    return app, token


def _csrf(app, token):
    import re

    html = app.handle(Request("GET", "/audio", {}, {SESSION_COOKIE: token})).body
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def test_audio_page_shows_devices_and_levels(tmp_path):
    app, token = _app(tmp_path, audio_factory=lambda r: FakeAudio(r))
    page = app.handle(Request("GET", "/audio", {}, {SESSION_COOKIE: token})).body
    assert "USB-Mikrofon" in page and "USB-Lautsprecher" in page
    assert "Empfangslautstärke" in page


def test_audio_save_levels(tmp_path):
    app, token = _app(tmp_path, audio_factory=lambda r: FakeAudio(r))
    csrf = _csrf(app, token)
    page = app.handle(Request("POST", "/audio", {
        "csrf": csrf, "aktion": "save_levels", "volume": "150", "gain": "80"},
        {SESSION_COOKIE: token})).body
    assert "Lautstärke gespeichert" in page
    assert BoxAudioSettings(tmp_path).output_volume_percent() == 150


def test_audio_save_devices_and_test(tmp_path):
    fake = FakeAudio(tmp_path)
    app, token = _app(tmp_path, audio_factory=lambda r: fake)
    csrf = _csrf(app, token)
    app.handle(Request("POST", "/audio", {
        "csrf": csrf, "aktion": "save_devices", "input": "mic1", "output": "spk1"},
        {SESSION_COOKIE: token}))
    assert fake.saved == ("mic1", "spk1")
    app.handle(Request("POST", "/audio", {
        "csrf": csrf, "aktion": "test", "output": "spk1"}, {SESSION_COOKIE: token}))
    assert fake.tested == "spk1"


def test_audio_without_hardware_still_allows_levels(tmp_path):
    def failing(project_root):
        raise RuntimeError("keine Audio-Bibliothek")

    app, token = _app(tmp_path, audio_factory=failing)
    page = app.handle(Request("GET", "/audio", {}, {SESSION_COOKIE: token})).body
    assert "Keine Audiogeräte gefunden" in page
    csrf = _csrf(app, token)
    page = app.handle(Request("POST", "/audio", {
        "csrf": csrf, "aktion": "save_levels", "volume": "120", "gain": "100"},
        {SESSION_COOKIE: token})).body
    assert "Lautstärke gespeichert" in page


def test_audio_device_save_blocked_without_hardware(tmp_path):
    def failing(project_root):
        raise RuntimeError("keine Audio-Bibliothek")

    app, token = _app(tmp_path, audio_factory=failing)
    csrf = _csrf(app, token)
    page = app.handle(Request("POST", "/audio", {
        "csrf": csrf, "aktion": "save_devices", "input": "x", "output": "y"},
        {SESSION_COOKIE: token})).body
    assert "nicht verfügbar" in page
