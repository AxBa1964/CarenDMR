from pathlib import Path
import unittest
from _ui_sources import main_window_source


class RxDiagnostics02145Tests(unittest.TestCase):
    def test_qt_startup_disables_rx_agc_for_diagnostic_comparison(self):
        core = Path("carendmr/bootstrap.py").read_text(encoding="utf-8")
        source = main_window_source()
        self.assertIn("audio_send_service.set_agc_enabled(False)", core)
        self.assertIn("receive_service.set_agc_enabled(False)", core)
        self.assertIn('timing_mark("RX_AGC_DIAGNOSE", "Beim Programmstart ausgeschaltet")', source)

    def test_receive_stop_requests_are_timing_logged(self):
        source = Path("carendmr/application/receive_service.py").read_text(encoding="utf-8")
        self.assertIn('"RX_STOP_ANGEFORDERT"', source)
        self.assertIn("Grund={message}", source)
        self.assertIn("TxPause=", source)

    def test_connection_manager_logs_disconnect_source(self):
        source = Path("carendmr/application/connection_manager.py").read_text(encoding="utf-8")
        self.assertIn('"RX_STOP_QUELLE", "ConnectionManager.disconnect"', source)
        self.assertIn("ConnectionManager.connect Zielwechsel", source)

    def test_status_indicator_uses_valid_point_size(self):
        source = Path("carendmr/ui_qt/operating_indicators.py").read_text(encoding="utf-8")
        self.assertIn("font.setPointSize(10)", source)
        self.assertNotIn("font.setPixelSize(13)", source)


if __name__ == "__main__":
    unittest.main()
