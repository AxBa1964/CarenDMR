from pathlib import Path


# Der Quelltext-Test der entfernten Tkinter-Oberfläche entfiel mit 0.2.1.87.

def test_qso_history_service_supports_worked_status() -> None:
    text = (Path(__file__).resolve().parents[1] / "carendmr" / "application" / "qso_history_service.py").read_text(encoding="utf-8")
    assert 'worked INTEGER' in text
    assert 'list_station_summaries' in text
    assert 'set_worked' in text
