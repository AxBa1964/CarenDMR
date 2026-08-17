from pathlib import Path
import unittest


class RxDiagnostics02145Tests(unittest.TestCase):
    def test_qt_startup_disables_rx_agc_for_diagnostic_comparison(self):
        source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
        self.assertIn("self.audio_send_service.set_agc_enabled(False)", source)
        self.assertIn("self.receive_service.set_agc_enabled(False)", source)
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
