import unittest

from carendmr.brandmeister.config import BrandMeisterConfig
from carendmr.brandmeister.listen import listen_receive_only
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

    def login(self):
        self.state = LoginState.CONNECTED

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

    def close(self):
        self.is_open = False


class FakeDecoder:
    def decode(self, _word):
        return PcmFrame((7,) * 160, corrected_errors=0)

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
        self.assertFalse(hasattr(FakeTransport, "send"))


if __name__ == "__main__":
    unittest.main()
