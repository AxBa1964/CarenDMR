from pathlib import Path
import unittest


class RadioUi021Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).parents[1] / "carendmr" / "ui" / "main_window.py").read_text(encoding="utf-8")

    def test_three_user_oriented_tabs(self):
        self.assertIn('◉  BETRIEB', self.source)
        self.assertIn('QSO-HISTORIE', self.source)
        self.assertIn('EINSTELLUNGEN', self.source)
        self.assertNotIn('self.notebook.add(transmit, text="Senden")', self.source)

    def test_toggle_ptt_and_sixty_second_limit(self):
        self.assertIn('text="TX AUS\\nZum Senden drücken"', self.source)
        self.assertIn('command=self._toggle_transmit', self.source)
        self.assertIn('set_tx_safety_limit_seconds(300)', self.source)

    def test_encoder_is_verified_automatically(self):
        self.assertIn('self.root.after(0, self._initialize_once)', self.source)
        self.assertIn('self._verify_encoder_path(plugin_path, save=False)', self.source)

    def test_connection_toggle_and_call_type(self):
        self.assertIn('text="CONNECT"', self.source)
        self.assertIn('text="DISCONNECT"', self.source)
        self.assertIn('for row, value in enumerate(("Gruppe", "Privat"))', self.source)
        self.assertIn('text="Stumm (Strg+M)"', self.source)

    def test_operation_hides_developer_status_texts(self):
        self.assertNotIn('Sicherheitsabschaltung: nach 60 Sekunden. Der aktuelle Sendetest', self.source)
        self.assertNotIn('textvariable=self.parrot_status_var, wraplength=650', self.source)


if __name__ == "__main__":
    unittest.main()
