from pathlib import Path
from _ui_sources import main_window_source


def test_design_system_tokens_and_metrics_are_centralized():
    text = Path("carendmr/ui_qt/theme.py").read_text(encoding="utf-8")
    assert "class DesignMetrics" in text
    assert "connection_control_width" in text
    assert "QRadioButton::indicator:checked" in text
    assert "QTableWidget::item:selected" in text
    assert "QTabBar {{ margin-left:" in text


def test_status_controls_use_shared_metrics():
    text = main_window_source()
    assert "self.connection_indicator = StatusIndicator(operation_page)" in text
    indicator = Path("carendmr/ui_qt/operating_indicators.py").read_text(encoding="utf-8")
    assert "self.setFixedSize(150, 40)" in indicator
    assert "self.connect_button.setFixedSize(METRICS.connection_control_width, 66)" in text
