from pathlib import Path

def test_coach_waits_for_real_parrot_rx():
    service = Path("carendmr/application/audio_send_service.py").read_text(encoding="utf-8")
    parrot = Path("carendmr/application/parrot_test_service.py").read_text(encoding="utf-8")
    assert "mark_audio_test_waiting_for_rx" in parrot
    assert "observe_audio_test_pcm" in service
    assert "observe_audio_test_call_activity" in service
    assert "AUDIO_TEST_PARROT_GESPEICHERT" in service
    assert 'f"rx_{stamp}_parrot_nach_ambe_8k.wav"' in service

def test_coach_defers_false_tx_only_report():
    live = Path("carendmr/brandmeister/live_voice_transmit.py").read_text(encoding="utf-8")
    parrot = Path("carendmr/application/parrot_test_service.py").read_text(encoding="utf-8")
    assert "defer_debug_report: bool = False" in live
    assert "if rx_debug_dir is not None and not defer_debug_report" in live
    assert 'defer_debug_report=bool(getattr(capture, "_one_shot_audio_test", False))' in parrot

def test_saved_rx_audio_state_is_applied_at_startup():
    main = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert "self.receive_service.set_output_volume_percent(self.audio_send_service.output_volume_percent)" in main
    assert "self.receive_service.set_user_muted(self.audio_send_service.user_muted)" in main
    assert "self.receive_service.set_agc_enabled(self.audio_send_service.agc_enabled)" in main
