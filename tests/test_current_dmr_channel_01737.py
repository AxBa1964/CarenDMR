from pathlib import Path
from _ui_sources import main_window_source


def _source() -> str:
    return main_window_source()


def test_search_text_change_does_not_clear_current_talkgroup_name() -> None:
    source = _source()
    assert "self.tg_edit.textChanged.connect(self._update_known_talkgroup_name)" not in source


def test_selected_and_manual_channels_use_central_channel_update() -> None:
    source = _source()
    assert "def _set_current_dmr_channel" in source
    selected = source.split("def _apply_selected_channel", 1)[1].split("def _apply_pending_talkgroup", 1)[0]
    manual = source.split("def _apply_talkgroup_entry", 1)[1].split("def _save_preferences", 1)[0]
    assert "self._set_current_dmr_channel(normalized)" in selected
    assert "self._set_current_dmr_channel(known)" in manual


def test_runtime_talkgroup_update_refreshes_known_name() -> None:
    source = _source()
    assert "self._update_known_talkgroup_name(str(state.talkgroup))" in source
