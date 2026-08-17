from pathlib import Path
import importlib.util


def _load_module():
    path = Path("tools/ambe_level_sweep.py")
    spec = importlib.util.spec_from_file_location("ambe_level_sweep_02114", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_levels_are_fixed_and_monotonic():
    module = _load_module()
    assert module.LEVELS_DB == (1.0, 2.0, 3.0, 4.0, 5.0)


def test_scaling_skips_clipping_instead_of_hard_limiting():
    module = _load_module()
    samples = [32000, -32000] * 80
    scaled, info = module.scale_without_clipping(samples, 3.0)
    assert scaled == []
    assert info["status"] == "SKIPPED_CLIPPING_RISK"


def test_scaling_applies_requested_gain_when_safe():
    module = _load_module()
    samples = [1000, -1000] * 80
    scaled, info = module.scale_without_clipping(samples, 6.0)
    assert info["status"] == "OK"
    assert max(abs(v) for v in scaled) > 1900
    assert max(abs(v) for v in scaled) < 2100


def test_tool_is_offline():
    source = Path("tools/ambe_level_sweep.py").read_text(encoding="utf-8")
    assert "DroidStarPluginEncoder" in source
    assert "NativeMbeReceiveVocoder" in source
    assert "from carendmr.brandmeister" not in source
    assert "import carendmr.brandmeister" not in source
    assert "execute_live_voice_once" not in source
