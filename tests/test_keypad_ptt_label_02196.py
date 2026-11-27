"""0.2.1.96: PTT-Plättchen mit Längsrippe und 3MF-Dateien (Platte + Zeichen als ein Objekt)."""
from __future__ import annotations

import importlib.util
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "hardware" / "keypad" / "cad"
NS = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}


def _model(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        assert "[Content_Types].xml" in archive.namelist()
        assert "_rels/.rels" in archive.namelist()
        return ET.fromstring(archive.read("3D/3dmodel.model"))


def test_ptt_label_files_exist():
    assert (CAD / "out" / "stl" / "plaettchen" / "plaettchen_ptt_basis.stl").is_file()
    assert (CAD / "out" / "stl" / "plaettchen" / "plaettchen_ptt_zeichen.stl").is_file()
    assert (CAD / "out" / "3mf" / "plaettchen_ptt.3mf").is_file()


@pytest.mark.parametrize("name", ["plaettchen_alle", "plaettchen_ptt", "plaettchen_favorit_1"])
def test_3mf_is_one_object_with_two_parts(name):
    root = _model(CAD / "out" / "3mf" / f"{name}.3mf")
    assert root.get("unit") == "millimeter"
    objects = root.findall("m:resources/m:object", NS)
    meshes = [o for o in objects if o.find("m:mesh", NS) is not None]
    groups = [o for o in objects if o.find("m:components", NS) is not None]
    assert sorted(o.get("name") for o in meshes) == ["basis", "zeichen"]
    assert len(groups) == 1
    assert len(groups[0].findall("m:components/m:component", NS)) == 2
    items = root.findall("m:build/m:item", NS)
    assert [item.get("objectid") for item in items] == [groups[0].get("id")]
    for mesh in meshes:
        assert len(mesh.findall("m:mesh/m:triangles/m:triangle", NS)) > 0


@pytest.fixture(scope="module")
def model():
    pytest.importorskip("cadquery")
    spec = importlib.util.spec_from_file_location("tastenfeld_ptt", CAD / "tastenfeld.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["tastenfeld_ptt"] = module
    spec.loader.exec_module(module)
    return module


def test_ptt_label_fits_cap_and_has_centered_rib(model):
    p = model.Params()
    base, rib = model.ptt_label(p)
    bb, rb = base.val().BoundingBox(), rib.val().BoundingBox()
    assert bb.xlen <= p.ptt_width - 3.5
    assert bb.ylen <= model.CAP_TOP
    assert rb.xlen == pytest.approx(model.PTT_RIB_LEN, abs=0.01)
    assert rb.center.x == pytest.approx(0.0, abs=0.01)
    assert rb.center.y == pytest.approx(0.0, abs=0.01)
    assert rb.zmin == pytest.approx(model.LABEL_T, abs=0.01)
    assert rb.zlen == pytest.approx(model.RELIEF, abs=0.01)
