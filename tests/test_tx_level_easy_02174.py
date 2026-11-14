from pathlib import Path
import ast
from _ui_sources import main_window_source

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def test_productive_tx_level_is_real_attenuation():
    text = read("carendmr/application/audio_send_service.py")
    assert "tx_factor = max(0.0, min(1.0, service.gain_percent / 100.0))" in text
    assert "tx_mono = mono * tx_factor" in text
    assert "self._resampler.process(tx_mono)" in text

def test_100_percent_preserves_reference_path():
    text = read("carendmr/application/audio_send_service.py")
    assert "100 % = Faktor 1.0" in text
    assert "min(1.0" in text

def test_desktop_labels_are_tx_level():
    text = main_window_source()
    assert 'setAccessibleName("TX-Pegel")' in text
    assert 'gain_caption = QLabel("TX-Pegel")' in text
    settings = read("carendmr/ui_qt/settings_dialog.py")
    assert 'audio_form.addRow("TX-Pegel:", gain_row)' in settings

def test_easy_has_rx_tx_hotkeys_and_status():
    text = read("carendmr/ui_qt/easy_window.py")
    assert '("Ctrl++", self._rx_volume_up)' in text
    assert '("Ctrl+-", self._rx_volume_down)' in text
    assert '("Alt++", self._tx_level_up)' in text
    assert '("Alt+-", self._tx_level_down)' in text
    assert "RX-Lautstärke" in text
    assert "TX-Pegel" in text
    assert "min(200" in text
    assert "min(100" in text

def test_modified_python_syntax():
    for rel in (
        "carendmr/application/audio_send_service.py",
        "carendmr/ui_qt/main_window.py",
        "carendmr/ui_qt/settings_dialog.py",
        "carendmr/ui_qt/easy_window.py",
    ):
        ast.parse(read(rel))
