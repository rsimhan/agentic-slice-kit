"""
Documentation that cannot go stale silently.

docs/ARCHITECTURE.md points at exact lines of code. Code moves; documents do not
follow. So this test parses every `file:line - symbol` reference out of the
document and checks the symbol is still defined there - and when it is not, it
tells you the line it moved to, so fixing the doc is a copy-paste rather than an
archaeology exercise.

This is principle 8 applied to the document that describes principle 8.
"""
import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "ARCHITECTURE.md"

# `slice/store.py:133` - `Store.append`   (also tolerates a bare symbol)
REF = re.compile(
    r"`(?P<file>[\w/]+\.py):(?P<line>\d+)`\s*[^`]*`(?P<symbol>[\w.]+)`")

TOLERANCE = 3          # a decorator or a comment above the def is not a failure


def definitions(path: Path) -> dict[str, int]:
    """Every class, function and module-level constant, with its line."""
    tree = ast.parse(path.read_text())
    out: dict[str, int] = {}

    def walk(node, prefix=""):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{prefix}{child.name}"
                out.setdefault(name, child.lineno)
                out.setdefault(child.name, child.lineno)
                if isinstance(child, ast.ClassDef):
                    walk(child, prefix=f"{child.name}.")
            elif isinstance(child, ast.Assign):
                for t in child.targets:
                    if isinstance(t, ast.Name):
                        out.setdefault(t.id, child.lineno)
    walk(tree)
    return out


def references():
    assert DOC.exists(), "docs/ARCHITECTURE.md is missing"
    return [(m["file"], int(m["line"]), m["symbol"]) for m in REF.finditer(DOC.read_text())]


def test_the_document_actually_has_references():
    refs = references()
    assert len(refs) >= 20, f"only found {len(refs)} code references - has the format changed?"


@pytest.mark.parametrize("ref", references(), ids=lambda r: f"{r[0]}:{r[1]}:{r[2]}")
def test_reference_still_points_at_its_symbol(ref):
    filename, line, symbol = ref
    path = ROOT / filename
    assert path.exists(), f"ARCHITECTURE.md points at {filename}, which does not exist"

    defs = definitions(path)
    bare = symbol.split(".")[-1]
    actual = defs.get(symbol) or defs.get(bare)

    assert actual is not None, (
        f"ARCHITECTURE.md references `{symbol}` in {filename}, but nothing by that "
        f"name is defined there any more. Update the document or restore the symbol.")
    assert abs(actual - line) <= TOLERANCE, (
        f"ARCHITECTURE.md says {filename}:{line} for `{symbol}`, "
        f"but it is now at line {actual}. Update the document.")
