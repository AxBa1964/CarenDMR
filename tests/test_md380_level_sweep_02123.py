from pathlib import Path
import importlib.util


def load_tool():
    path = Path("tools/ambe_md380_level_sweep.py")
    spec = importlib.util.spec_from_file_location("ambe_md380_level_sweep", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_levels_are_fine_and_centered_around_zero():
    module = load_tool()
    assert module.LEVELS_DB == (-2.0, -1.0, 0.0, 1.0, 2.0, 3.0)


def test_zero_db_keeps_samples_unchanged():
    module = load_tool()
    samples = [-12000, -1, 0, 1, 12000]
    out, clipped = module.apply_gain(samples, 0.0)
    assert out == samples
    assert clipped == 0


def test_positive_gain_clips_safely():
    module = load_tool()
    out, clipped = module.apply_gain([32767, -32768], 3.0)
    assert out == [32767, -32768]
    assert clipped == 2
