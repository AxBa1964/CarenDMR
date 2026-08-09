from pathlib import Path

def test_windows_build_patches_upstream_link_scope():
    source = Path("native/build_md380_dynarmic_windows.ps1").read_text(encoding="utf-8")
    assert "target_link_libraries(md380_vocoder STATIC dynarmic)" in source
    assert "target_link_libraries(md380_vocoder PRIVATE dynarmic)" in source
    assert 'CMAKE_POLICY_VERSION_MINIMUM = "3.5"' in source
    assert "core_perl" in source
