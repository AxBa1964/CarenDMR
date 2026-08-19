from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
CONNECTION_MANAGER = ROOT / "carendmr" / "application" / "connection_manager.py"


def test_connection_manager_has_no_platform_branch_for_tx_session():
    text = CONNECTION_MANAGER.read_text(encoding="utf-8")
    assert "platform.system()" not in text
    assert "fresh_session_test" not in text
    assert "RX_STOP_FUER_TX_FRISCHE_SESSION_REFERENZ" in text
    assert "RX_THREAD_FRISCHE_SESSION_REFERENZ_GESTARTET" in text


def test_connection_manager_syntax():
    ast.parse(CONNECTION_MANAGER.read_text(encoding="utf-8"))
