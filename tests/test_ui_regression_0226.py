from pathlib import Path


def _source() -> str:
    return (Path(__file__).resolve().parents[1] / "carendmr" / "ui" / "main_window.py").read_text(encoding="utf-8")


def test_history_table_is_responsive_and_detail_width_is_fixed() -> None:
    text = _source()
    assert 'def _resize_history_columns' in text
    assert 'self.history_tree.bind("<Configure>", self._resize_history_columns)' in text
    assert 'table_area.columnconfigure(0, weight=1)' in text
    assert 'ttk.Treeview(table_area' in text
    assert 'grid(in_=table_area' not in text
    assert 'columnspan=2, sticky="nsew"' in text
    assert 'width=280' in text
    assert 'content.columnconfigure(0, weight=1, minsize=720)' in text


def test_settings_header_has_enough_height_for_subtitle() -> None:
    text = _source()
    assert 'heading = tk.Frame(frame, bg=bg, height=76)' in text
    assert 'heading.rowconfigure(1, minsize=24)' in text


def test_worked_status_is_restored_on_operation_page() -> None:
    text = _source()
    assert 'self.receive_service.history.is_worked(call.source_id)' in text
    assert '"✓ Bereits gesprochen" if self._worked_status_value' in text
    assert 'if self._worked_status_source_id == summary.source_id:' in text
