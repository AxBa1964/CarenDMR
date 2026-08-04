from pathlib import Path


def test_settings_content_is_scrollable_and_assist_option_visible():
    source = (Path(__file__).parents[1] / "carendmr" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "settings_canvas = tk.Canvas" in source
    assert "settings_scrollbar = ttk.Scrollbar" in source
    assert "scrollregion=settings_canvas.bbox" in source
    assert 'height=390' in source
    assert "Caren Assist Sprachausgabe aktiv" in source
