import json
from pathlib import Path

from carendmr.application.talkgroup_catalog_service import TalkgroupCatalogService


def test_brandmeister_payload_is_normalized_and_sorted(tmp_path: Path) -> None:
    service = TalkgroupCatalogService(tmp_path / "talkgroups.json")
    rows = service._normalize_api_payload({"2623": "Niedersachsen/Bremen", "91": "World-wide", "x": "ignored"})
    assert [row["target"] for row in rows] == [91, 2623]
    assert rows[1]["name"] == "Niedersachsen/Bremen"
    assert rows[1]["timeslot"] == 2
    assert rows[1]["call_type"] == "group"


def test_catalog_save_produces_search_compatible_list(tmp_path: Path) -> None:
    path = tmp_path / "talkgroups.json"
    service = TalkgroupCatalogService(path)
    rows = service._normalize_api_payload({"26538": "Nordharz"})
    service.save(rows)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == [{
        "target": 26538, "timeslot": 2, "call_type": "group", "name": "Nordharz",
        "country": "Deutschland", "country_code": "DE", "description": "",
        "language": "Deutsch", "language_source": "mcc", "language_confidence": 0.82,
    }]
