from pathlib import Path

def test_windows_build_patches_upstream_link_scope():
    source = Path("native/build_md380_dynarmic_windows.ps1").read_text(encoding="utf-8")
    # 0.2.1.89: Der Upstream-CMake-Build (mit dem Linkfehler) wird nicht mehr
    # verwendet; die Bridge übersetzt md380_vocoder.cpp selbst.
    assert "md380_vocoder.cpp" in source
    assert 'CMAKE_POLICY_VERSION_MINIMUM = "3.5"' in source
    assert "core_perl" in source
