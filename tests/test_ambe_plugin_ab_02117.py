from pathlib import Path
import importlib.util


def _load_module():
    path = Path("tools/ambe_plugin_ab.py")
    spec = importlib.util.spec_from_file_location("ambe_plugin_ab_02117", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_ab_uses_fixed_best_gain():
    module = _load_module()
    assert module.FIXED_GAIN_DB == 1.0


def test_ab_tool_requires_second_plugin_and_is_offline():
    source = Path("tools/ambe_plugin_ab.py").read_text(encoding="utf-8")
    assert "--plugin-b" in source
    assert "DroidStarPluginEncoder" in source
    assert "NativeMbeReceiveVocoder" in source
    assert "execute_live_voice_once" not in source
    assert "brandmeister" not in source.lower()


def test_ab_report_compares_binary_and_ambe_hashes():
    source = Path("tools/ambe_plugin_ab.py").read_text(encoding="utf-8")
    assert "same_plugin_binary" in source
    assert "same_ambe_output" in source
    assert "ambe_sha256" in source
