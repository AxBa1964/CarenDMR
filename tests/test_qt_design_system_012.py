from pathlib import Path


def test_design_system_tokens_and_metrics_are_centralized():
    text = Path("carendmr/ui_qt/theme.py").read_text(encoding="utf-8")
    assert "class DesignMetrics" in text
    assert "connection_control_width" in text
    assert "QRadioButton::indicator:checked" in text
    assert "QTableWidget::item:selected" in text
    assert "QTabBar {{ margin-left:" in text


def test_status_controls_use_shared_metrics():
    text = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert "StatusIndicator(header)" in text
    indicator = Path("carendmr/ui_qt/operating_indicators.py").read_text(encoding="utf-8")
    assert "self.setFixedSize(150, 40)" in indicator
    assert "self.connect_button.setFixedSize(METRICS.connection_control_width, METRICS.action_control_height)" in text
