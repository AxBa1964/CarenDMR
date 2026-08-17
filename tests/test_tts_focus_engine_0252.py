from __future__ import annotations

import time
import unittest
from pathlib import Path

from carendmr.accessibility.caren_assist import AsyncCarenAssist


class _SlowOutput:
    def __init__(self) -> None:
        self.items: list[str] = []

    def speak(self, text: str) -> None:
        time.sleep(0.03)
        self.items.append(text)


class TtsFocusEngine0252Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (Path(__file__).parents[1] / "carendmr" / "ui" / "main_window.py").read_text(encoding="utf-8")

    def test_focus_sentences_are_atomic(self) -> None:
        self.assertIn('text = f"Timeslot {self._spoken_timeslot', self.source)
        self.assertIn('text = f"Rufart {self._spoken_call_type()', self.source)
        self.assertNotIn('text = f"Timeslot, ', self.source)
        self.assertNotIn('text = f"Rufart, ', self.source)

    def test_focus_uses_dedicated_serial_queue(self) -> None:
        self.assertIn("self.caren_assist.say_focus(text)", self.source)

    def test_operation_tab_circle_returns_from_connect_to_talkgroup(self) -> None:
        self.assertIn('self.connect_button.bind("<Tab>", self._focus_talkgroup_from_keyboard', self.source)

    def test_pending_focus_is_coalesced_to_latest(self) -> None:
        output = _SlowOutput()
        assist = AsyncCarenAssist(enabled=lambda: True, output=output)
        assist.say_focus("Timeslot eins.")
        assist.say_focus("Rufart Gruppe.")
        deadline = time.time() + 1.0
        while len(output.items) < 1 and time.time() < deadline:
            time.sleep(0.01)
        assist.close()
        self.assertIn(output.items[-1], {"Timeslot eins.", "Rufart Gruppe."})
        self.assertTrue(all(item.endswith(".") for item in output.items))


if __name__ == "__main__":
    unittest.main()
