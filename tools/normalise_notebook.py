"""Remove run-dependent metadata from executed notebooks, keeping every output.

nbconvert is run with record_timing off, so it no longer writes per-cell execution
timestamps; this script removes any that are already in a notebook, drops widget
state, and writes the notebook back in nbformat's standard layout (nbformat 4, one-space
indent, sorted keys). It fails if an output contains something that changes from run to
run or machine to machine: a memory address or this checkout's absolute path.

Usage: python tools/normalise_notebook.py NOTEBOOK [NOTEBOOK ...]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parent.parent
CELL_KEYS = ("execution",)
NOTEBOOK_KEYS = ("widgets",)
VOLATILE = [re.compile(r" at 0x[0-9a-fA-F]{6,}"), re.compile(re.escape(str(ROOT)))]


def normalise(path: Path) -> bool:
    """Rewrite `path` in place. Returns True if the bytes changed."""
    path = Path(path)
    original = path.read_bytes()
    nb = nbformat.read(path, as_version=4)
    for cell in nb.cells:
        for key in CELL_KEYS:
            cell.metadata.pop(key, None)
        outputs = json.dumps(cell.get("outputs", []))
        for pattern in VOLATILE:
            if pattern.search(outputs):
                raise RuntimeError(f"{path.name}: an output contains run-dependent text matching {pattern.pattern!r}")
    for key in NOTEBOOK_KEYS:
        nb.metadata.pop(key, None)
    nbformat.validate(nb)
    nbformat.write(nb, path)
    return path.read_bytes() != original


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    for f in argv:
        changed = normalise(Path(f))
        print(f"{f}: {'normalised' if changed else 'already normalised'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
