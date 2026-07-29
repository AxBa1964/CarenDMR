import unittest

from tools.brandmeister_one_shot import OneShotSafetyError, execute_one_shot


class DisabledPublicGroupOneShotTests(unittest.TestCase):
    def test_legacy_tg91_sender_always_fails_before_using_arguments(self):
        transport = object()
        with self.assertRaisesRegex(OneShotSafetyError, "nichts gesendet"):
            execute_one_shot(
                object(),
                client_factory=lambda _: transport,
                monitor_seconds=0.1,
            )

    def test_disabled_entrypoint_has_no_send_or_retry_helper(self):
        import tools.brandmeister_one_shot as legacy

        self.assertFalse(hasattr(legacy, "_monitor"))
        self.assertFalse(hasattr(legacy, "_validate_fixture"))
        self.assertFalse(hasattr(legacy, "PACKET_INTERVAL_SECONDS"))


if __name__ == "__main__":
    unittest.main()
