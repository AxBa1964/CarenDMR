import ast
import re
from pathlib import Path

from carendmr.version import __version__


def test_release_version():
    assert __version__ == "0.1.9.1.3"


def test_theme_stylesheet_uses_only_defined_tokens():
    path = Path(__file__).parents[1] / "carendmr" / "ui_qt" / "theme.py"
    source = path.read_text(encoding="utf-8")
    module = ast.parse(source)
    fields = set()
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == "ThemeTokens":
            for statement in node.body:
                if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                    fields.add(statement.target.id)
    uses = set(re.findall(r"\bt\.([A-Za-z_][A-Za-z0-9_]*)", source))
    assert uses <= fields, f"Ungueltige Theme-Tokens: {sorted(uses - fields)}"
