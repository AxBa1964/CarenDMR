import json
from pathlib import Path

from carendmr.application import FavoriteService
from carendmr.domain import DmrChannel, FavoriteChannel


def test_favorite_uses_custom_name_and_keeps_standard_name() -> None:
    favorite = FavoriteChannel(262, 2, "group", "Deutschland", "OV-Abend", "Rundspruch Dienstag 08:00").normalized()
    assert favorite.display_name == "OV-Abend"
    assert favorite.default_name == "Deutschland"
    assert favorite.to_dmr_channel() == DmrChannel(262, 2, "group", "OV-Abend")
    assert favorite.call_type_short == "G"


def test_favorite_service_persists_order_and_notes(tmp_path: Path) -> None:
    service = FavoriteService(tmp_path / "favorites.local.json")
    first = service.add(FavoriteChannel(262, 2, "group", "Deutschland", "OV-Abend", "Dienstag 08:00"))
    second = service.add(FavoriteChannel(91, 2, "group", "Worldwide", "DX"))
    service.move(1, 0)
    reloaded = FavoriteService(service.path)
    assert [fav.target for fav in reloaded.favorites] == [91, 262]
    assert reloaded.favorites[1].note == "Dienstag 08:00"
    assert reloaded.find(262, 2, "group") is not None


def test_json_export_and_import_avoids_duplicates(tmp_path: Path) -> None:
    source = FavoriteService(tmp_path / "source.json")
    source.add(FavoriteChannel(2623, 2, "group", "Niedersachsen Bremen", "Nordrunde"))
    exported = tmp_path / "export.json"
    source.export_json(exported)
    target = FavoriteService(tmp_path / "target.json")
    assert target.import_json(exported) == 1
    assert target.import_json(exported) == 0


def test_main_window_integrates_favorites() -> None:
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    assert 'FavoriteService(self.project_root / "config" / "favorites.local.json")' in source
    assert 'self.tabs.addTab(self.favorites_widget, "Talkgroups")' in source
    assert 'self.favorite_button = QPushButton("☆")' in source
    assert "self.favorite_combo" not in source
    assert "talkgroup_row.addWidget(self.favorite_button)" in source
    assert "self._apply_favorite_channel" in source


def test_talkgroups_table_is_compact_and_uses_common_source() -> None:
    source = Path("carendmr/ui_qt/favorites_widget.py").read_text(encoding="utf-8")
    assert '["★", "Eigener Name", "Standardname", "TG", "TS", "R", "Land", "Sprache", "Notiz"]' in source
    assert "TalkgroupSearchService" in source
    assert "BrandMeister aktualisieren" in source
    assert "itemClicked" in source
    assert "_note_preview" in source
    assert "export_json" in source and "export_csv" in source
