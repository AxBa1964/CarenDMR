"""Regression: Favoriten-Refresh darf den Benchmark-Service nicht ersetzen."""
from __future__ import annotations

import ast
from pathlib import Path


def _method_node(name: str) -> ast.FunctionDef:
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Methode {name!r} nicht gefunden")


def test_refresh_favorites_does_not_replace_audio_benchmark_service() -> None:
    method = _method_node("_refresh_favorites")
    assignments = [
        node
        for node in ast.walk(method)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
    ]
    targets = []
    for assignment in assignments:
        raw_targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
        for target in raw_targets:
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                targets.append(f"{target.value.id}.{target.attr}")
    assert "self.audio_benchmark_service" not in targets


def test_audio_benchmark_service_is_created_once_in_main_window_init() -> None:
    source = Path("carendmr/ui_qt/main_window.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    calls = []
    for node in ast.walk(module):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "AudioBenchmarkService":
                calls.append(node)
    assert len(calls) == 1
