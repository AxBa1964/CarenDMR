from pathlib import Path
from unittest.mock import Mock

from carendmr.audio.pcm_output import BufferedPcmOutput
from carendmr.application.audio_send_service import AudioSendService


def test_buffered_output_uses_selected_device_and_native_rate():
    stream = Mock()
    sd = Mock()
    sd.query_devices.return_value = {"max_output_channels": 2}
    sd.RawOutputStream.return_value = stream
    output = BufferedPcmOutput(
        sample_rate=8000,
        sounddevice_module=sd,
        output_device_index=7,
        output_sample_rate=16000,
    )
    output.start()
    kwargs = sd.RawOutputStream.call_args.kwargs
    assert kwargs["device"] == 7
    assert kwargs["samplerate"] == 16000
    assert kwargs["blocksize"] == 320


def test_audio_send_service_factory_uses_saved_output(tmp_path: Path):
    service = object.__new__(AudioSendService)
    device = Mock(index=9, default_sample_rate=48000.0)
    manager = Mock()
    manager.devices = (device,)
    manager.resolve.return_value.device = device
    service.manager = manager
    output = service.create_pcm_output(sample_rate=8000)
    assert output._output_device_index == 9
    assert output._output_sample_rate == 48000
