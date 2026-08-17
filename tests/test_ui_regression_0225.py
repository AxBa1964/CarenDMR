from pathlib import Path


def test_main_window_contains_all_three_modern_ui_sections() -> None:
    text = (Path(__file__).resolve().parents[1] / "carendmr" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert 'BETRIEB' in text
    assert 'history_search_var' in text
    assert 'QSO bestätigen' in text
    assert '_show_settings_section("audio")' in text
    assert 'Einstellungen durchsuchen' in text


def test_qso_history_service_supports_worked_status() -> None:
    text = (Path(__file__).resolve().parents[1] / "carendmr" / "application" / "qso_history_service.py").read_text(encoding="utf-8")
    assert 'worked INTEGER' in text
    assert 'list_station_summaries' in text
    assert 'set_worked' in text
