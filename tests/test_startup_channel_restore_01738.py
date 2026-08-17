from pathlib import Path


def test_saved_channel_is_restored_with_known_name_on_startup() -> None:
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert "self._restore_saved_dmr_channel()" in source
    assert "def _restore_saved_dmr_channel" in source
    method = source.split("def _restore_saved_dmr_channel", 1)[1].split("def _known_channel_for_target", 1)[0]
    assert "self._known_channel_for_target(self.preferences.talkgroup)" in method
    assert "name=known.name if known else """ in method
    assert "self._set_current_dmr_channel(channel, clear_input=False)" in method
