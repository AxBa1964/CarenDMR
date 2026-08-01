import unittest

from carendmr.brandmeister.config import BrandMeisterConfig
from carendmr.brandmeister.listen import LiveCallActivity, LiveListenProgress, listen_receive_only
from carendmr.brandmeister.protocol import LoginState
from carendmr.brandmeister.silent_call import (
    build_tg91_ts2_silent_call_fixture,
)
from carendmr.network import NetworkReceiveTimeout
from carendmr.vocoder import PcmFrame


class FakeTransport:
    def __init__(self, packets):
        self.packets = list(packets)

    def receive(self):
        if self.packets:
            return self.packets.pop(0)
        raise NetworkReceiveTimeout("done")


class FakeClient:
    def __init__(self, config, packets):
        self.config = config
        self.transport = FakeTransport(packets)
        self.state = LoginState.DISCONNECTED
        self.pings = 0

    def login(self):
        self.state = LoginState.CONNECTED

    def send_ping(self):
        self.pings += 1

    def close(self):
        self.transport = None
        self.state = LoginState.DISCONNECTED


class FakeOutput:
    def __init__(self, **_):
        self.is_open = False
        self.samples = []

    def start(self):
        self.is_open = True

    def write(self, samples):
        self.samples.extend(samples)

    def send_ping(self):
        self.pings += 1

    def close(self):
        self.is_open = False


class FakeDecoder:
    def decode(self, _word):
        return PcmFrame((7,) * 160, corrected_errors=0)

    def send_ping(self):
        self.pings += 1

    def close(self):
        pass


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        self.value += 0.01
        return self.value


class LiveListenTests(unittest.TestCase):
    def test_receive_only_fixture_decodes_and_closes_without_send_surface(self):
        fixture = build_tg91_ts2_silent_call_fixture(
            source_id=1_234_567,
            repeater_id=1_234_567,
            stream_id=0x12345678,
        )
        packets = list(fixture.to_bytes())
        config = BrandMeisterConfig(
            host="example.invalid",
            port=62031,
            dmr_id=1_234_567,
            password="not-a-secret-fixture",
            callsign="N0TEST",
        )
        client = FakeClient(config, packets)
        output = FakeOutput()
        result = listen_receive_only(
            config,
            seconds=0.2,
            client_factory=lambda _: client,
            output_factory=lambda **_: output,
            decoder_factory=FakeDecoder,
            monotonic=Clock(),
            sleep=lambda _: None,
        )

        self.assertTrue(result.authenticated)
        self.assertTrue(result.audio_started)
        self.assertEqual(result.target_voice_bursts, 6)
        self.assertEqual(result.decoded_codewords, 18)
        self.assertEqual(result.decoded_samples, 6 * 480)
        self.assertEqual(result.decode_errors, 0)
        self.assertTrue(result.closed)
        self.assertFalse(result.interrupted)
        self.assertFalse(hasattr(FakeTransport, "send"))


    def test_call_activity_reports_start_and_end(self):
        fixture = build_tg91_ts2_silent_call_fixture(
            source_id=1_234_567, repeater_id=1_234_567, stream_id=0x12345678,
        )
        config = BrandMeisterConfig(
            host="example.invalid", port=62031, dmr_id=1_234_567,
            password="not-a-secret-fixture", callsign="N0TEST",
        )
        client = FakeClient(config, list(fixture.to_bytes()))
        activity: list[LiveCallActivity] = []
        listen_receive_only(
            config, seconds=0.2, call_activity_callback=activity.append,
            client_factory=lambda _: client, output_factory=FakeOutput,
            decoder_factory=FakeDecoder, monotonic=Clock(), sleep=lambda _: None,
        )
        self.assertTrue(activity[0].active)
        self.assertEqual(1_234_567, activity[0].source_id)
        self.assertEqual(91, activity[0].talkgroup)
        self.assertEqual(2, activity[0].timeslot)
        self.assertFalse(activity[-1].active)

    def test_unlimited_receive_stops_cleanly_on_keyboard_interrupt(self):
        config = BrandMeisterConfig(
            host="example.invalid", port=62031, dmr_id=1_234_567,
            password="not-a-secret-fixture", callsign="N0TEST",
        )
        client = FakeClient(config, [])
        output = FakeOutput()

        class InterruptingTransport:
            def receive(self):
                raise KeyboardInterrupt

        client.transport = InterruptingTransport()
        result = listen_receive_only(
            config, seconds=None, client_factory=lambda _: client,
            output_factory=lambda **_: output, decoder_factory=FakeDecoder,
            monotonic=Clock(), sleep=lambda _: None,
        )

        self.assertTrue(result.interrupted)
        self.assertTrue(result.closed)
        self.assertTrue(result.authenticated)

    def test_unlimited_receive_sends_periodic_heartbeat(self):
        config = BrandMeisterConfig(
            host="example.invalid", port=62031, dmr_id=1_234_567,
            password="not-a-secret-fixture", callsign="N0TEST",
        )
        client = FakeClient(config, [])
        result = listen_receive_only(
            config, seconds=0.12, heartbeat_interval=0.02,
            client_factory=lambda _: client, output_factory=FakeOutput,
            decoder_factory=FakeDecoder, monotonic=Clock(), sleep=lambda _: None,
        )
        self.assertTrue(result.closed)
        self.assertGreaterEqual(client.pings, 1)

    def test_progress_callback_receives_diagnostic_counts(self):
        config = BrandMeisterConfig(
            host="example.invalid", port=62031, dmr_id=1_234_567,
            password="not-a-secret-fixture", callsign="N0TEST",
        )
        client = FakeClient(config, [])
        progress: list[LiveListenProgress] = []
        result = listen_receive_only(
            config, seconds=0.2, progress_callback=progress.append,
            progress_interval=0.01, client_factory=lambda _: client,
            output_factory=FakeOutput, decoder_factory=FakeDecoder,
            monotonic=Clock(), sleep=lambda _: None,
        )
        self.assertTrue(result.closed)
        self.assertGreaterEqual(len(progress), 1)
        self.assertEqual(0, progress[0].decode_errors)


if __name__ == "__main__":
    unittest.main()
