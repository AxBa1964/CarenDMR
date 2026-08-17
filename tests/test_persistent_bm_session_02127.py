from pathlib import Path


def test_connection_manager_pauses_rx_instead_of_disconnect_for_tx():
    source = Path("carendmr/application/connection_manager.py").read_text(encoding="utf-8")
    live = source[source.index("def run_parrot_hold_to_talk"):]
    assert "pause_for_tx()" in live
    assert "resume_after_tx()" in live
    assert "existing_client=session_client" in live


def test_receive_service_exposes_same_logged_in_session():
    source = Path("carendmr/application/receive_service.py").read_text(encoding="utf-8")
    assert "def session_client" in source
    assert "def pause_for_tx" in source
    assert "def resume_after_tx" in source
    assert "preserve_client_on_exit=self._tx_pause_requested.is_set" in source


def test_live_tx_can_preserve_existing_client():
    source = Path("carendmr/brandmeister/live_voice_transmit.py").read_text(encoding="utf-8")
    assert "existing_client: BrandMeisterClient | None = None" in source
    assert "preserve_client: bool = False" in source
    assert "TX_SESSION_WIEDERVERWENDET" in source
    assert "TX_SESSION_OFFEN_GEHALTEN" in source


def test_receive_loop_can_reuse_session_without_reactivation():
    source = Path("carendmr/brandmeister/listen.py").read_text(encoding="utf-8")
    assert "existing_client: BrandMeisterClient | None = None" in source
    assert "skip_target_activation: bool = False" in source
    assert "RX_SESSION_WIEDERVERWENDET" in source
    assert "RX_ZIELAKTIVIERUNG_UEBERSPRUNGEN" in source
