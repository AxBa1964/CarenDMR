from pathlib import Path
from _ui_sources import main_window_source


def test_disconnected_default_does_not_override_persisted_talkgroup():
    source = main_window_source()
    assert "state.brandmeister_connected" in source
    assert "ConnectionState.CONNECTING" in source
    assert "self.current_tg_label.setText(str(state.talkgroup))" in source
    block = source[source.index("# Im getrennten Initialzustand"):source.index("if state.brandmeister_connected and state.receive_active", source.index("# Im getrennten Initialzustand"))]
    assert "if state.talkgroup and (" in block
    assert "ConnectionState.DISCONNECTED" not in block
