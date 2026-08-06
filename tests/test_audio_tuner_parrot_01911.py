from pathlib import Path


def test_audio_tuner_parrot_uses_ts2_private_9990():
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert 'DmrChannel(target=9990, timeslot=2, call_type="private", name="Parrot")' in source
    assert 'DmrChannel(target=9990, timeslot=1, call_type="private", name="Parrot")' not in source
    assert 'self._prepare_audio_tuner_parrot()' in source
