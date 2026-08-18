from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_md380_cmake_wrapper_is_packaged():
    wrapper = ROOT / "native" / "md380_dynarmic_build" / "CMakeLists.txt"
    text = wrapper.read_text(encoding="utf-8")
    assert "add_library(carendmr_md380_bridge SHARED" in text
    assert "add_subdirectory(\"${MD380_SOURCE_DIR}\" md380_upstream)" in text
    assert "target_link_libraries(carendmr_md380_bridge PRIVATE" in text


def test_gitignore_keeps_wrapper_but_ignores_build_outputs():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "native/md380_dynarmic_build/\n" not in text
    assert "native/md380_dynarmic_build/out*/" in text


def test_macos_builder_preflights_wrapper():
    text = (ROOT / "native" / "build_md380_dynarmic_macos.sh").read_text(encoding="utf-8")
    assert 'CMAKE_PROJECT="$SCRIPT_DIR/md380_dynarmic_build"' in text
    assert 'if [ ! -f "$CMAKE_PROJECT/CMakeLists.txt" ]; then' in text
    assert 'cmake -S "$CMAKE_PROJECT" -B "$BUILD_DIR"' in text
