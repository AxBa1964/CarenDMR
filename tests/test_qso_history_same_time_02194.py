"""0.2.1.94: Gleiche Endzeit (grobe Windows-Uhr) – zuletzt gespeichert gilt als neuester Eintrag."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from carendmr.application import qso_history_service as module
from carendmr.application import QsoHistoryService
from carendmr.domain import CurrentCall, RadioContact

FIXED = datetime(2026, 11, 27, 18, 0, 0, tzinfo=timezone.utc)


class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):  # noqa: D401 - Testersatz
        return FIXED


def _service_with_two_calls(tmp_path: Path, monkeypatch) -> QsoHistoryService:
    monkeypatch.setattr(module, "datetime", FrozenDateTime)
    service = QsoHistoryService(tmp_path)
    contact = RadioContact(1234567, "DL1ABC", "Max", "Muster", country="Germany")
    service.add_completed_call(CurrentCall(1234567, 91, 2, 1, 4.0, contact))
    service.add_completed_call(CurrentCall(1234567, 262, 1, 2, 6.0, contact))
    return service


def test_recent_list_orders_equal_times_by_insertion(tmp_path, monkeypatch):
    service = _service_with_two_calls(tmp_path, monkeypatch)
    rows = service.list_recent()
    assert rows[0].ended_at == rows[1].ended_at
    assert [row.talkgroup for row in rows] == [262, 91]


def test_station_summary_uses_last_saved_call_on_equal_times(tmp_path, monkeypatch):
    service = _service_with_two_calls(tmp_path, monkeypatch)
    summary = service.list_station_summaries("DL1ABC")[0]
    assert summary.last_talkgroup == 262
    assert summary.last_timeslot == 1


def test_export_query_is_stable_for_equal_times():
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "ORDER BY ended_at DESC, id DESC" in source
    assert "FROM qso_history ORDER BY ended_at, id" in source
