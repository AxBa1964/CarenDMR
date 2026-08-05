from pathlib import Path


def test_disconnected_default_does_not_override_persisted_talkgroup():
    source = (Path(__file__).parents[1] / "carendmr" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
    assert "state.brandmeister_connected" in source
    assert "ConnectionState.CONNECTING" in source
    assert "self.current_tg_label.setText(str(state.talkgroup))" in source
    block = source[source.index("# Im getrennten Initialzustand"):source.index("if state.brandmeister_connected and state.receive_active", source.index("# Im getrennten Initialzustand"))]
    assert "if state.talkgroup and (" in block
    assert "ConnectionState.DISCONNECTED" not in block
