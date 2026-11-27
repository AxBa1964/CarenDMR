"""0.2.1.96: Software-Kennung im FM-Funknetz einstellbar, Vorgabe „CarenFM“."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from carendmr.svxreflector.client import node_info
from carendmr.svxreflector.config import FmConfigError, load_fm_config
from carendmr.version import __version__

ROOT = Path(__file__).resolve().parents[1]


def _write(root: Path, **values) -> None:
    data = {"callsign": "DK7EE-APP", "auth_key": "test-key"}
    data.update(values)
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "fm_funknetz.local.json").write_text(json.dumps(data), encoding="utf-8")


def test_default_software_name_is_carenfm(tmp_path):
    _write(tmp_path)  # alte Datei ohne software_name
    assert load_fm_config(tmp_path).software_name == "CarenFM"


def test_software_name_can_be_set(tmp_path):
    _write(tmp_path, software_name="CarenDMR")
    assert load_fm_config(tmp_path).software_name == "CarenDMR"


@pytest.mark.parametrize("name", ["SvxLink", "svxlink", "Latry", "HamLink", "QSO Link"])
def test_foreign_software_names_are_refused(tmp_path, name):
    _write(tmp_path, software_name=name)
    with pytest.raises(FmConfigError, match="anderes Programm"):
        load_fm_config(tmp_path)


@pytest.mark.parametrize("name", ["", " ", "X" * 33])
def test_invalid_software_names(tmp_path, name):
    _write(tmp_path, software_name=name)
    with pytest.raises(FmConfigError, match="Software-Name"):
        load_fm_config(tmp_path)


def test_node_info_uses_name_and_own_version():
    info = node_info("DK7EE-APP", "CarenFM")
    assert info["sw"] == "CarenFM" and info["swVer"] == __version__


def test_example_config_names_carenfm():
    example = json.loads((ROOT / "config" / "fm_funknetz.example.json").read_text(encoding="utf-8"))
    assert example["software_name"] == "CarenFM"
