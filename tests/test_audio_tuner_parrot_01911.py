from pathlib import Path
from _ui_sources import main_window_source


def test_audio_tuner_parrot_uses_ts2_private_9990():
    source = main_window_source()
    assert 'DmrChannel(target=9990, timeslot=2, call_type="private", name="Parrot")' in source
    assert 'DmrChannel(target=9990, timeslot=1, call_type="private", name="Parrot")' not in source
    assert 'self._prepare_audio_tuner_parrot()' in source
