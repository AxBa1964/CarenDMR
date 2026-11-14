from pathlib import Path
from _ui_sources import main_window_source


def test_saved_channel_is_restored_with_known_name_on_startup() -> None:
    source = main_window_source()
    assert "self._restore_saved_dmr_channel()" in source
    assert "def _restore_saved_dmr_channel" in source
    method = source.split("def _restore_saved_dmr_channel", 1)[1].split("def _known_channel_for_target", 1)[0]
    assert "self._known_channel_for_target(self.preferences.talkgroup)" in method
    assert "name=known.name if known else """ in method
    assert "self._set_current_dmr_channel(channel, clear_input=False)" in method
