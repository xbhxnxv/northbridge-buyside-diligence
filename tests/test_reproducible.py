"""A rerun of the pipeline must not change any tracked file.

Slow (it runs the whole pipeline, about 75 seconds), so it is deselected by default
(see pytest.ini). Run it with:  python -m pytest tests -m slow
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def tracked_hashes() -> dict[str, str]:
    files = [f for f in git("ls-files", "-z").split("\0") if f and (ROOT / f).is_file()]
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in files}


@pytest.mark.slow
def test_second_run_leaves_git_status_unchanged():
    if not (ROOT / "data" / "northbridge.duckdb").exists():
        pytest.skip("run `python run_all.py` once first; this test checks the second run")
    status_before, hashes_before = git("status", "--porcelain"), tracked_hashes()
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    result = subprocess.run([sys.executable, "run_all.py", "--skip", "tests"], cwd=ROOT, env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    status_after, hashes_after = git("status", "--porcelain"), tracked_hashes()
    changed = sorted(f for f in hashes_before if hashes_before[f] != hashes_after.get(f))
    assert not changed, f"the rerun changed tracked files: {changed}"
    assert status_after == status_before
    if not status_before:
        assert status_after == ""
