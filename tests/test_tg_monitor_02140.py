import json
import unittest

from carendmr.domain import DmrChannel
from carendmr.ipc.protocol import decode_request
from carendmr.tg_monitor.activity_service import TalkgroupActivityService


class TGMonitor02140Tests(unittest.TestCase):
    def test_lastheard_start_event_is_parsed_active(self):
        data = {
            "payload": json.dumps({
                "DestinationID": 262,
                "DestinationName": "Germany",
                "SourceID": 2621234,
                "SourceCall": "DL1ABC",
                "SourceName": "Test",
                "Start": 100,
                "Stop": 0,
                "SessionID": "abc",
                "Event": "Session-Start",
            })
        }
        item = TalkgroupActivityService._parse_activity(data)
        self.assertIsNotNone(item)
        self.assertEqual(262, item.target)
        self.assertEqual("DL1ABC", item.callsign)
        self.assertTrue(item.active)

    def test_lastheard_stop_event_is_parsed_inactive(self):
        data = {
            "payload": json.dumps({
                "DestinationID": 91,
                "SourceID": 123,
                "Start": 100,
                "Stop": 112,
                "SessionID": "def",
                "Event": "Session-Stop",
            })
        }
        item = TalkgroupActivityService._parse_activity(data)
        self.assertIsNotNone(item)
        self.assertFalse(item.active)
        self.assertEqual(12, item.duration_seconds)

    def test_invalid_lastheard_payload_is_ignored(self):
        self.assertIsNone(TalkgroupActivityService._parse_activity({"payload": "not-json"}))

    def test_ipc_accepts_only_valid_set_channel(self):
        raw = json.dumps({
            "command": "set_channel",
            "target": 262,
            "timeslot": 2,
            "call_type": "group",
            "name": "Germany",
        }).encode()
        channel = decode_request(raw)
        self.assertEqual(DmrChannel(262, 2, "group", name="Germany").normalized(), channel)

    def test_ipc_rejects_unknown_command(self):
        with self.assertRaises(ValueError):
            decode_request(json.dumps({"command": "shutdown"}).encode())


if __name__ == "__main__":
    unittest.main()
