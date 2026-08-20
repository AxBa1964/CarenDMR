from pathlib import Path

from carendmr.application.qso_history_service import QsoHistoryService
from carendmr.qso_sync import QsoSyncConfig


def _service(root: Path, shared: Path) -> QsoHistoryService:
    (root / "config").mkdir(parents=True, exist_ok=True)
    QsoSyncConfig(enabled=True, folder=str(shared)).save(root / "config" / "qso_sync.local.json")
    return QsoHistoryService(root)


def test_qso_history_and_worked_state_sync_bidirectionally(tmp_path):
    shared = tmp_path / "cloud"
    a = _service(tmp_path / "pc_a", shared)
    worked_at = a.mark_worked(
        1234567,
        callsign="DL1ABC",
        name="Test",
        country="Germany",
        talkgroup=262,
        timeslot=2,
    )

    b = _service(tmp_path / "pc_b", shared)
    summaries = b.list_station_summaries()
    assert len(summaries) == 1
    assert summaries[0].callsign == "DL1ABC"
    assert summaries[0].worked is True
    assert summaries[0].worked_at == worked_at

    b.set_worked(1234567, False)
    a.sync_now()
    assert a.is_worked(1234567) is False


def test_qrz_logid_is_synchronized(tmp_path):
    shared = tmp_path / "cloud"
    a = _service(tmp_path / "pc_a", shared)
    qso_at = a.mark_worked(2345678, callsign="OE1XYZ", talkgroup=91, timeslot=2)
    a.record_qrz_log(2345678, "OE1XYZ", qso_at, "987654321")

    b = _service(tmp_path / "pc_b", shared)
    assert b.qrz_logid("OE1XYZ", qso_at) == "987654321"


def test_each_machine_writes_its_own_atomic_snapshot(tmp_path):
    shared = tmp_path / "cloud"
    a = _service(tmp_path / "pc_a", shared)
    b = _service(tmp_path / "pc_b", shared)
    a.mark_worked(1111111, callsign="A1AAA")
    b.mark_worked(2222222, callsign="B2BBB")
    files = list(shared.glob("CarenDMR_QSO_*.json"))
    assert len(files) == 2
    assert not list(shared.glob("*.tmp"))
