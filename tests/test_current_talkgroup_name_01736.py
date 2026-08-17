from pathlib import Path


def test_current_talkgroup_name_is_rendered_below_current_tg():
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert 'self.current_tg_name_label = QLabel("")' in source
    assert 'current_column.addWidget(self.current_tg_name_label)' in source
    assert 'def _set_current_dmr_channel' in source
    assert 'self.current_tg_name_label.setText(normalized.name or "")' in source
    assert 'self.tg_name_label = QLabel("")' not in source
