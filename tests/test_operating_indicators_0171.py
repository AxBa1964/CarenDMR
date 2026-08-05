from pathlib import Path

from carendmr.version import __version__


def test_release_version_is_0171() -> None:
    assert __version__ == "0.1.7.3.8"


def test_visual_indicators_are_integrated_without_ambe_text() -> None:
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert "StatusIndicator" in source
    assert "LevelMeter" in source
    assert "MIC-PEGEL" in source
    assert "RX-PEGEL" in source
    assert "AMBE-Encoder bereit" not in source
    assert 'level_callback=lambda level: self._updates.put(("mic_level", level))' in source
    assert "set_output_level_callback" in source


def test_indicators_are_purely_visual() -> None:
    source = Path("carendmr/ui_qt/operating_indicators.py").read_text(encoding="utf-8")
    assert "Qt.FocusPolicy.NoFocus" in source
    assert "WA_TransparentForMouseEvents" in source
    assert 'setAccessibleName("")' in source
    assert '"GETRENNT"' in source
    assert '"EMPFANG"' in source
    assert '"SENDEN"' in source
    assert '"FEHLER"' in source
