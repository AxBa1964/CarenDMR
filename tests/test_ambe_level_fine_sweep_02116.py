from pathlib import Path
import importlib.util


def _load():
    path = Path("tools/ambe_level_fine_sweep.py")
    spec = importlib.util.spec_from_file_location("ambe_level_fine_sweep_02116", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_tool_exists_and_levels_are_exact():
    assert Path("tools/ambe_level_fine_sweep.py").is_file()
    module = _load()
    assert module.LEVELS_DB == (1.0, 2.0, 3.0, 4.0, 5.0)


def test_safe_scaling_and_clipping_guard():
    module = _load()
    scaled, info = module.scale_without_clipping([1000, -1000] * 80, 3.0)
    assert scaled and info["status"] == "OK"
    scaled, info = module.scale_without_clipping([32000, -32000] * 80, 1.0)
    assert scaled == [] and info["status"] == "SKIPPED_CLIPPING_RISK"


def test_fine_sweep_tool_remains_available_after_later_sprints():
    assert Path("tools/ambe_level_fine_sweep.py").is_file()
