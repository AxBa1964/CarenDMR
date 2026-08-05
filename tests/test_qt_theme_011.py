from pathlib import Path

from carendmr.version import __version__


def test_theme_version() -> None:
    assert __version__ == "0.1.7.3.5"


def test_theme_is_centralized_and_contrast_aware() -> None:
    root = Path(__file__).parents[1]
    theme = (root / "carendmr" / "ui_qt" / "theme.py").read_text(encoding="utf-8")
    assert "class ThemeTokens" in theme
    assert "focus: str" in theme
    assert "QTableWidget" in theme
    assert "QDialog" in theme
    assert "QGroupBox" in theme
    assert "apply_theme" in theme


def test_ui_modules_have_no_direct_hex_colors() -> None:
    ui_dir = Path(__file__).parents[1] / "carendmr" / "ui_qt"
    for path in ui_dir.glob("*.py"):
        if path.name == "theme.py":
            continue
        content = path.read_text(encoding="utf-8")
        assert "#10151d" not in content
        assert "#ffffff" not in content.lower()
