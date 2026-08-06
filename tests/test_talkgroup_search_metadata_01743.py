import json
from pathlib import Path

from carendmr.application import TalkgroupSearchService


def test_search_finds_derived_language(tmp_path: Path):
    path = tmp_path / "talkgroups.json"
    path.write_text(json.dumps([{"target": 235, "name": "United Kingdom", "timeslot": 2, "call_type": "group"}]), encoding="utf-8")
    service = TalkgroupSearchService(path)
    result = service.search("englisch")
    assert len(result) == 1
    assert result[0].country == "Vereinigtes Königreich"
    assert result[0].language == "Englisch"
