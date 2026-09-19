#!/usr/bin/env python3
"""
Re-point docs/ARCHITECTURE.md at the current line numbers.

`tests/test_architecture.py` DETECTS drift; this FIXES it. Detection without a
cheap fix is how documentation quietly stops being maintained - the test goes
red, someone marks it skip, and six weeks later the doc is fiction.

    python scripts/sync_architecture.py           # show what moved
    python scripts/sync_architecture.py --write   # update the document
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "ARCHITECTURE.md"
REF = re.compile(r"`(?P<file>[\w/]+\.py):(?P<line>\d+)`(?P<mid>[^`]*)`(?P<symbol>[\w.]+)`")


def definitions(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}

    def walk(node, prefix=""):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                out.setdefault(f"{prefix}{child.name}", child.lineno)
                out.setdefault(child.name, child.lineno)
                if isinstance(child, ast.ClassDef):
                    walk(child, prefix=f"{child.name}.")
            elif isinstance(child, ast.Assign):
                for t in child.targets:
                    if isinstance(t, ast.Name):
                        out.setdefault(t.id, child.lineno)

    walk(ast.parse(path.read_text()))
    return out


def main(write: bool) -> int:
    text = DOC.read_text()
    cache: dict[str, dict[str, int]] = {}
    moved, missing = [], []

    def fix(m: re.Match) -> str:
        f, old, symbol = m["file"], int(m["line"]), m["symbol"]
        path = ROOT / f
        if not path.exists():
            missing.append((f, symbol, "file does not exist"))
            return m.group(0)
        defs = cache.setdefault(f, definitions(path))
        new = defs.get(symbol) or defs.get(symbol.split(".")[-1])
        if new is None:
            missing.append((f, symbol, "symbol not found"))
            return m.group(0)
        if new != old:
            moved.append((f, symbol, old, new))
            return f"`{f}:{new}`{m['mid']}`{symbol}`"
        return m.group(0)

    updated = REF.sub(fix, text)

    for f, sym, old, new in moved:
        print(f"  moved    {f}:{old} -> {new}   {sym}")
    for f, sym, why in missing:
        print(f"  MISSING  {f}  {sym}  ({why})")
    if not moved and not missing:
        print("  all references current")

    if write and moved:
        DOC.write_text(updated)
        print(f"\nupdated {len(moved)} reference(s) in {DOC.relative_to(ROOT)}")
    elif moved:
        print("\nrun with --write to apply")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main("--write" in sys.argv))
