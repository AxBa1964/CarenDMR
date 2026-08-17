from pathlib import Path

from carendmr.application.favorite_service import FavoriteService
from carendmr.application.talkgroup_search_service import TalkgroupSearchService
from carendmr.domain import FavoriteChannel


def test_favorites_are_metadata_of_search_catalog(tmp_path: Path) -> None:
    catalog = tmp_path / "talkgroups.json"
    catalog.write_text('[{"target":262,"timeslot":2,"call_type":"group","name":"Deutschland"}]', encoding="utf-8")
    favorite_path = tmp_path / "favorites.local.json"
    service = FavoriteService(favorite_path)
    service.add(FavoriteChannel(262, 2, "group", "Deutschland", "OV-Abend", "Dienstag", 0))
    search = TalkgroupSearchService(catalog)
    search.set_favorites(service.favorites)

    result = search.search("26")[0]
    assert result.target == 262
    assert result.name == "OV-Abend"
    assert search.display_name(result) == "★ OV-Abend"


def test_private_favorite_is_searchable_without_base_catalog_entry(tmp_path: Path) -> None:
    catalog = tmp_path / "talkgroups.json"
    catalog.write_text('[]', encoding="utf-8")
    favorite_path = tmp_path / "favorites.local.json"
    service = FavoriteService(favorite_path)
    service.add(FavoriteChannel(2632198, 2, "private", "", "Heidi", "", 0))
    search = TalkgroupSearchService(catalog)
    search.set_favorites(service.favorites)

    result = search.search("hei")[0]
    assert result.target == 2632198
    assert result.call_type == "private"
