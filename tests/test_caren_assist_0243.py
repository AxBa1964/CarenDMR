import tempfile
import time
import unittest
from pathlib import Path

from carendmr.accessibility.caren_assist import AsyncCarenAssist
from carendmr.application.operating_preferences import OperatingPreferences, OperatingPreferencesStore
from carendmr.domain import InformationCategory, InformationMessage, InformationPriority, OperatingContext
from carendmr.domain import EventLevel
from datetime import datetime


class _Output:
    def __init__(self):
        self.items = []
    def speak(self, text):
        self.items.append(text)


class CarenAssist0243Tests(unittest.TestCase):
    def test_operating_preferences_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            store = OperatingPreferencesStore(Path(temp) / "operating.local.json")
            expected = OperatingPreferences(9990, 2, "private", True)
            store.save(expected)
            self.assertEqual(expected, store.load())

    def test_invalid_preferences_fall_back_safely(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "operating.local.json"
            path.write_text('{"talkgroup": -1, "timeslot": 8, "call_type": "x"}', encoding="utf-8")
            self.assertEqual(OperatingPreferences(), OperatingPreferencesStore(path).load())

    def test_async_assist_filters_and_does_not_block(self):
        output = _Output()
        assist = AsyncCarenAssist(enabled=lambda: True, output=output)
        message = InformationMessage(
            timestamp=datetime.now(), code="connection.connected",
            short_text="Verbunden", long_text="Mit BrandMeister verbunden.",
            category=InformationCategory.CONNECTION,
            priority=InformationPriority.HIGH, level=EventLevel.INFO,
            context=OperatingContext.OPERATION,
        )
        assist(message)
        deadline = time.time() + 1.0
        while not output.items and time.time() < deadline:
            time.sleep(0.01)
        assist.close()
        self.assertEqual(["Mit BrandMeister verbunden."], output.items)


if __name__ == "__main__":
    unittest.main()
