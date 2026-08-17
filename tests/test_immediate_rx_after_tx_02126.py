from pathlib import Path


def test_live_transmit_never_waits_for_parrot_echo():
    source = Path('carendmr/application/parrot_test_service.py').read_text(encoding='utf-8')
    live_call = source.split('def transmit_live_capture', 1)[1].split('def capture_hold_to_talk', 1)[0]
    assert 'wait_for_parrot_echo=False' in live_call
    assert 'wait_for_parrot_echo=is_parrot' not in live_call


def test_live_transmitter_keeps_parrot_wait_optional_not_default():
    source = Path('carendmr/brandmeister/live_voice_transmit.py').read_text(encoding='utf-8')
    assert 'wait_for_parrot_echo: bool = False' in source
    assert 'TX_TERMINATOR_GESENDET' in source
