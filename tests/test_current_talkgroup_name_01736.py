from pathlib import Path
from _ui_sources import main_window_source


def test_current_talkgroup_name_is_rendered_below_current_tg():
    source = main_window_source()
    assert 'self.current_tg_name_label = QLabel("")' in source
    assert 'current_column.addWidget(self.current_tg_name_label)' in source
    assert 'def _set_current_dmr_channel' in source
    assert 'self.current_tg_name_label.setText(normalized.name or "")' in source
    assert 'self.tg_name_label = QLabel("")' not in source
