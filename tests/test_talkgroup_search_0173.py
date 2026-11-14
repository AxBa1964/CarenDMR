import json
from pathlib import Path

from carendmr.application import TalkgroupSearchService
from _ui_sources import main_window_source


def _service(tmp_path: Path) -> TalkgroupSearchService:
    path = tmp_path / "talkgroups.json"
    path.write_text(json.dumps([
        {"name": "Deutschland", "target": 262, "timeslot": 2, "call_type": "group", "country": "Deutschland"},
        {"name": "Niedersachsen Bremen", "target": 2623, "timeslot": 2, "call_type": "group", "country": "Deutschland"},
        {"name": "Worldwide", "target": 91, "timeslot": 2, "call_type": "group"},
        {"name": "Parrot", "target": 9990, "timeslot": 2, "call_type": "private"},
    ]), encoding="utf-8")
    return TalkgroupSearchService(path)


def test_search_finds_number_prefix_and_exact_number_first(tmp_path: Path) -> None:
    service = _service(tmp_path)
    assert [channel.target for channel in service.search("26")] == [262, 2623]
    assert [channel.target for channel in service.search("262")] == [262, 2623]


def test_search_finds_name_case_insensitively(tmp_path: Path) -> None:
    service = _service(tmp_path)
    assert service.search("par")[0].target == 9990
    assert service.search("deut")[0].target == 262


def test_result_target_is_compact_for_table_column(tmp_path: Path) -> None:
    service = _service(tmp_path)
    channel = service.search("par")[0]
    assert service.format_target(channel) == "DMR-ID 9990"
    assert service.format_target(service.search("262")[0]) == "TG 262"


def test_invalid_catalog_entries_are_skipped(tmp_path: Path) -> None:
    path = tmp_path / "talkgroups.json"
    path.write_text(json.dumps([{"name": "Kaputt"}, {"name": "OK", "target": 91}]), encoding="utf-8")
    service = TalkgroupSearchService(path)
    assert [channel.target for channel in service.channels] == [91]


def test_main_window_uses_live_talkgroup_search() -> None:
    source = main_window_source()
    assert "TalkgroupSearchWidget" in source
    assert 'setPlaceholderText("Talkgroup nach Nummer oder Name suchen")' in source
    assert "channel_selected.connect(self._apply_selected_channel)" in source
    assert "QRegularExpressionValidator" not in source


def test_search_popup_keeps_input_focus_and_uses_two_columns() -> None:
    source = Path("carendmr/ui_qt/talkgroup_search_widget.py").read_text(encoding="utf-8")
    assert "QTableWidget(0, 2" in source
    assert "WindowDoesNotAcceptFocus" in source
    assert "WA_ShowWithoutActivating" in source
    assert "self.setFocus(Qt.FocusReason.OtherFocusReason)" in source
    assert "self._accept_current_result()" in source
    assert "self.popup.hide()" in source
    assert "self._results: list[DmrChannel]" in source
    assert "_show_results_for_current_text" in source
    assert "key == Qt.Key.Key_Down and not self.popup.isVisible()" in source
    assert "def event(self, event) -> bool:" in source
    assert "QEvent.Type.KeyPress" in source
    assert "self._highlighted_row" in source
