"""0.2.1.92: Update-Prüfung auf Anfrage über dk7ee.de/download/versionen.json."""
from __future__ import annotations

import json
from pathlib import Path

from carendmr.application.update_check_service import (
    TOOL_KEY,
    VERSIONS_URL,
    UpdateCheckService,
    UpdateState,
    evaluate,
    parse_version,
)

ROOT = Path(__file__).resolve().parents[1]


def _json(version="0.2.2.0", **extra) -> bytes:
    entry = {"name": "CarenDMR", "version": version,
             "download": "https://example.org/CarenDMR-Setup.exe",
             "seite": "https://dk7ee.de/carendmr.html"}
    entry.update(extra)
    return json.dumps({"schema": 1, "stand": "2026-11-14", "tools": {TOOL_KEY: entry}}).encode("utf-8")


def test_fixed_source_and_key():
    assert VERSIONS_URL == "https://dk7ee.de/download/versionen.json"
    assert TOOL_KEY == "carendmr"


def test_numeric_comparison():
    assert parse_version("0.2.1.100") > parse_version("0.2.1.91")
    assert parse_version("1.10.0") > parse_version("1.9.0")
    assert parse_version("1.5") == parse_version("1.5.0.0")


def test_newer_version_is_reported_with_links():
    result = evaluate(_json(datum="2026-11-20", neu="Update-Prüfung"), current="0.2.1.91")
    assert result.state is UpdateState.AVAILABLE
    assert "0.2.2.0" in result.message and "2026-11-20" in result.message and "Update-Prüfung" in result.message
    assert result.download.startswith("https://") and result.page.startswith("https://")


def test_same_or_older_version_is_current():
    assert evaluate(_json("0.2.1.91"), current="0.2.1.91").state is UpdateState.CURRENT
    assert evaluate(_json("0.2.1.83"), current="0.2.1.91").state is UpdateState.CURRENT


def test_errors_are_reported_not_raised():
    assert evaluate(b"kein json", current="0.2.1.91").state is UpdateState.ERROR
    assert evaluate(json.dumps({"schema": 2, "tools": {}}).encode(), current="1.0").state is UpdateState.ERROR
    assert evaluate(json.dumps({"schema": 1, "tools": {}}).encode(), current="1.0").state is UpdateState.ERROR
    assert evaluate(_json("x.y"), current="1.0").state is UpdateState.ERROR

    def offline(_url):
        raise OSError("keine Verbindung")

    result = UpdateCheckService(fetch=offline, current="0.2.1.91").check()
    assert result.state is UpdateState.ERROR and "läuft normal weiter" in result.message


def test_only_https_links_are_used():
    result = evaluate(_json(download="http://unsicher.example/setup.exe"), current="0.0.1")
    assert result.download == ""


def test_service_reads_fixed_url():
    seen = []
    service = UpdateCheckService(fetch=lambda url: seen.append(url) or _json("0.0.1"), current="0.2.1.92")
    assert service.check().state is UpdateState.CURRENT
    assert seen == [VERSIONS_URL]


def test_ui_wiring():
    windows = (ROOT / "carendmr" / "ui_qt" / "main_window_windows.py").read_text(encoding="utf-8")
    assert 'QAction("Nach Updates suchen …", self)' in windows
    easy = (ROOT / "carendmr" / "ui_qt" / "easy_window.py").read_text(encoding="utf-8")
    assert '("Ctrl+Shift+U", self._open_update_check)' in easy
    dialog = (ROOT / "carendmr" / "ui_qt" / "update_dialog.py").read_text(encoding="utf-8")
    assert "QDesktopServices.openUrl" in dialog and 'startswith("https://")' in dialog
