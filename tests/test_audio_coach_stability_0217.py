from pathlib import Path
from _ui_sources import main_window_source


def test_audio_coach_has_cancel_toggle_and_common_finish():
    source = Path("carendmr/ui_qt/audio_coach_widget.py").read_text(encoding="utf-8")
    assert 'setText("Abbrechen")' in source
    assert "def _cancel_own_modulation_test" in source
    assert "def _finish_test" in source
    assert "invoke_cancel=True" in source


def test_main_window_cleans_up_guided_audio_test():
    source = main_window_source()
    assert "cancel_modulation_test=self._cancel_audio_tuner_assistant" in source
    assert "def _cancel_audio_tuner_assistant" in source
    assert "self.audio_send_service.cancel_audio_test()" in source
    assert "self._stop_tx()" in source
