"""0.2.1.95: flache Tastenkappen + zweifarbige Kennzeichnungs-Plättchen."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "hardware" / "keypad" / "cad"
NAMES = ("favorit_1", "favorit_2", "favorit_3", "favorit_4", "beenden",
         "tg_zurueck", "tg_vor", "leiser", "lauter", "verbinden", "trennen")


def test_two_colour_label_files_exist():
    for name in NAMES:
        for part in ("basis", "zeichen"):
            assert (CAD / "out" / "stl" / "plaettchen" / f"plaettchen_{name}_{part}.stl").is_file()
        assert (CAD / "out" / "step" / "plaettchen" / f"plaettchen_{name}.step").is_file()
    assert (CAD / "out" / "stl" / "plaettchen_alle_basis.stl").is_file()
    assert (CAD / "out" / "stl" / "plaettchen_alle_zeichen.stl").is_file()


def test_old_caps_with_symbols_are_gone():
    leftovers = sorted(path.name for path in (CAD / "out").rglob("kappe_*")
                       if path.stem != "kappe_ptt")
    assert leftovers == []


@pytest.fixture(scope="module")
def model():
    pytest.importorskip("cadquery")
    spec = importlib.util.spec_from_file_location("tastenfeld_labels", CAD / "tastenfeld.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["tastenfeld_labels"] = module
    spec.loader.exec_module(module)
    return module


def test_caps_have_flat_top_for_upside_down_printing(model):
    cap = model.keycap()
    box = cap.val().BoundingBox()
    assert box.zmax == pytest.approx(model.CAP_H, abs=0.01)
    # Oberseite: genau eine ebene Fläche ganz oben, ohne aufgesetzte Zeichen
    top_faces = cap.faces(">Z").vals()
    assert len(top_faces) == 1
    assert top_faces[0].BoundingBox().xlen == pytest.approx(model.CAP_TOP, abs=0.01)


def test_labels_two_parts_touch_without_overlap(model):
    p = model.Params()
    plates = model.labels(p)
    assert sorted(plates) == sorted(NAMES)
    for name, (base, sign) in plates.items():
        assert base.val().isValid() and sign.val().isValid(), name
        common = base.intersect(sign)
        volume = sum(solid.Volume() for solid in common.solids().vals())
        assert volume == pytest.approx(0.0, abs=1e-3), name
        bb = base.val().BoundingBox()
        assert bb.xlen <= model.CAP_TOP and bb.ylen <= model.CAP_TOP, name


def test_braille_digits_follow_standard(model):
    assert model.BRAILLE["#"] == (3, 4, 5, 6)
    assert model.BRAILLE["1"] == (1,)
    assert model.BRAILLE["2"] == (1, 2)
    assert model.BRAILLE["3"] == (1, 4)
    assert model.BRAILLE["4"] == (1, 4, 5)
    _, sign = model.label_plate("braille2")
    # Zahlzeichen (4 Punkte) + „2“ (2 Punkte)
    assert len(sign.solids().vals()) == 6
    assert sign.val().BoundingBox().zlen == pytest.approx(0.5, abs=0.01)
