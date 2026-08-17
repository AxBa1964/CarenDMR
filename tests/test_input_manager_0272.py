from pathlib import Path

from carendmr.accessibility.hotkeys import HotkeyManager


def test_hotkey_manager_persists_unassigned(tmp_path: Path):
    path = tmp_path / 'hotkeys.json'
    manager = HotkeyManager(path)
    manager.set('HELP', '')
    reloaded = HotkeyManager(path)
    assert reloaded.mapping['HELP'] == ''


def test_empty_hotkey_does_not_conflict(tmp_path: Path):
    manager = HotkeyManager(tmp_path / 'hotkeys.json')
    manager.set('HELP', '')
    manager.set('STATUS', '')
    assert manager.conflicts() == []
