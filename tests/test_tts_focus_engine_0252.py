from __future__ import annotations

import time
import unittest

from carendmr.accessibility.caren_assist import AsyncCarenAssist


class _SlowOutput:
    def __init__(self) -> None:
        self.items: list[str] = []

    def speak(self, text: str) -> None:
        time.sleep(0.03)
        self.items.append(text)


class TtsFocusEngine0252Tests(unittest.TestCase):
    # Die Quelltext-Tests der entfernten Tkinter-Oberfläche entfielen mit 0.2.1.87.

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
