from pathlib import Path


def test_codec_lab_is_offline_and_compares_two_decoders():
    source = Path("tools/ambe_codec_lab.py").read_text(encoding="utf-8")
    assert "DroidStarPluginEncoder" in source
    assert "NativeMbeReceiveVocoder" in source
    assert "decode_2450x1150" in source
    assert "execute_live_voice_once" not in source
    assert "BrandMeister" in source


def test_bridge_exposes_plugin_decoder():
    source = Path("native/vocoder_plugin_bridge.cpp").read_text(encoding="utf-8")
    assert "carendmr_vocoder_decode_2450x1150" in source
    assert "decode_2450x1150(pcm, frame)" in source
