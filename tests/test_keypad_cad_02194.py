"""0.2.1.94: CAD-Modell des Tastenfelds (CadQuery) – Gehäuse Entwurf 2."""
from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CAD = ROOT / "hardware" / "keypad" / "cad"


def test_model_source_parses_and_has_parameters():
    source = (CAD / "tastenfeld.py").read_text(encoding="utf-8")
    ast.parse(source)
    for needle in ("cut: float = 14.0", "plate_t: float = 1.5", "angle: float = 7.0",
                   "h_front: float = 20.0", "h_pod: float = 52.0", "unit: float = 19.05"):
        assert needle in source


def test_exported_files_present_for_every_part():
    expected = {"unterteil", "tastenplatte", "podestdeckel", "kappe", "kappe_ptt",
                "probestreifen_ausschnitt", "fuss_tpu"}
    for name in expected:
        assert (CAD / "out" / "step" / f"{name}.step").is_file(), name
        assert (CAD / "out" / "stl" / f"{name}.stl").is_file(), name
    assert (CAD / "out" / "step" / "baugruppe.step").is_file()


def test_cadquery_not_required_by_carendmr():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "cadquery" not in requirements


@pytest.fixture(scope="module")
def model():
    pytest.importorskip("cadquery")
    spec = importlib.util.spec_from_file_location("tastenfeld", CAD / "tastenfeld.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["tastenfeld"] = module
    spec.loader.exec_module(module)
    return module


def test_all_parts_are_single_valid_solids(model):
    built = model.parts(model.Params())
    assert len(built) == 7
    for name, part in built.items():
        assert part.val().isValid(), name
        assert len(part.solids().vals()) == 1, name


def test_housing_dimensions(model):
    p = model.Params()
    box = model.housing(p).val().BoundingBox()
    assert box.xlen == pytest.approx(145.0, abs=0.01)
    assert box.ylen == pytest.approx(p.depth, abs=0.01)
    assert box.zlen == pytest.approx(52.0, abs=0.01)
    assert p.h_back == pytest.approx(20.0 + p.plate_y1 * p.tan)


def test_key_plate_has_13_switch_cutouts(model):
    p = model.Params()
    assert len(p.keys()) + len(p.ptt_switches()) == 13
    # Ausschnitte liegen vollständig auf der Platte und überlappen nicht.
    holes = [(u, v) for _, u, v, _ in p.keys()] + p.ptt_switches()
    for u, v in holes:
        assert p.cut / 2 < u < p.plate_w - p.cut / 2
        assert p.cut / 2 < v < p.plate_len - p.cut / 2
    for i, (u1, v1) in enumerate(holes):
        for u2, v2 in holes[i + 1:]:
            assert abs(u1 - u2) >= p.cut or abs(v1 - v2) >= p.cut


def test_test_strip_offers_five_sizes(model):
    assert model.TEST_CUTS == (13.8, 13.9, 14.0, 14.1, 14.2)
