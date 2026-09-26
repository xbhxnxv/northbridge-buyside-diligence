"""Run the pipeline twice and check that every output is byte-for-byte the same.

After each run this reads every file git tracks, plus the generated CSVs that git
ignores (data/clean/ and dashboard/model_data/), and compares the two runs. Each file
that differs is printed with the reason: which zip entries, notebook cells, PDF keys or
text lines changed. The exit code is 0 only if nothing differs.

The DuckDB database file is not compared: it is a working store, not an output.
The pytest stage is skipped inside the two runs; it writes nothing tracked.

Usage: python tools/check_reproducible.py [--runs N]
       python run_all.py --check-determinism      (same thing)
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
UNTRACKED_OUTPUTS = ["data/clean/*.csv", "dashboard/model_data/*.csv"]


def output_files() -> list[str]:
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    files = {f for f in tracked.decode().split("\0") if f}
    for pattern in UNTRACKED_OUTPUTS:
        files.update(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern))
    return sorted(f for f in files if (ROOT / f).is_file())


def snapshot() -> dict[str, bytes]:
    return {f: (ROOT / f).read_bytes() for f in output_files()}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_pipeline(n: int, log_dir: Path) -> None:
    log = log_dir / f"run{n}.log"
    t0 = time.perf_counter()
    env = {**os.environ, "PYTHONHASHSEED": "0"}
    with open(log, "w", encoding="utf-8") as fh:
        result = subprocess.run([PY, "run_all.py", "--skip", "tests"], cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT)
    print(f"run {n}: exit {result.returncode} in {time.perf_counter() - t0:.1f}s")
    if result.returncode != 0:
        print(log.read_text(encoding="utf-8")[-3000:])
        raise SystemExit(f"run {n} of the pipeline failed")


def first_text_difference(a: bytes, b: bytes) -> str:
    la = a.decode("utf-8", errors="replace").splitlines()
    lb = b.decode("utf-8", errors="replace").splitlines()
    for i, (x, y) in enumerate(zip(la, lb), start=1):
        if x != y:
            return f"line {i}: {x.strip()[:90]!r} -> {y.strip()[:90]!r}"
    return f"length {len(la)} -> {len(lb)} lines"


def explain_zip(a: bytes, b: bytes) -> str:
    za, zb = zipfile.ZipFile(io.BytesIO(a)), zipfile.ZipFile(io.BytesIO(b))
    na, nb = [i.filename for i in za.infolist()], [i.filename for i in zb.infolist()]
    if sorted(na) != sorted(nb):
        return f"different entries: {sorted(set(na) ^ set(nb))}"
    content = [n for n in na if za.read(n) != zb.read(n)]
    if content:
        parts = []
        for n in content[:5]:
            parts.append(f"{n} ({first_text_difference(za.read(n), zb.read(n))})")
        return "entry content differs: " + "; ".join(parts) + (" ..." if len(content) > 5 else "")
    if na != nb:
        return "same entries in a different order"
    times = [n for n in na if za.getinfo(n).date_time != zb.getinfo(n).date_time]
    if times:
        return f"zip entry timestamps differ ({len(times)} entries)"
    return "zip headers or compression differ"


def explain_notebook(a: bytes, b: bytes) -> str:
    ja, jb = json.loads(a), json.loads(b)
    if ja.get("metadata") != jb.get("metadata"):
        return "notebook metadata differs"
    parts = []
    for i, (ca, cb) in enumerate(zip(ja["cells"], jb["cells"])):
        for key in ("metadata", "outputs", "source", "execution_count"):
            if ca.get(key) != cb.get(key):
                detail = ""
                if key in ("metadata", "outputs"):
                    detail = first_text_difference(json.dumps(ca.get(key), indent=1).encode(), json.dumps(cb.get(key), indent=1).encode())
                parts.append(f"cell {i} {key} {detail}".strip())
    return "; ".join(parts[:4]) + (" ..." if len(parts) > 4 else "") if parts else "JSON layout differs"


def explain_pdf(a: bytes, b: bytes) -> str:
    from pypdf import PdfReader
    ra, rb = PdfReader(io.BytesIO(a)), PdfReader(io.BytesIO(b))
    parts = []
    ma, mb = dict(ra.metadata or {}), dict(rb.metadata or {})
    parts += [f"{k}: {ma.get(k)} -> {mb.get(k)}" for k in sorted(set(ma) | set(mb)) if ma.get(k) != mb.get(k)]
    for key in ("/ID", "/DocChecksum"):
        if ra.trailer.get(key) != rb.trailer.get(key):
            parts.append(f"trailer {key} differs")
    if [p.extract_text() for p in ra.pages] != [p.extract_text() for p in rb.pages]:
        parts.append("page text differs")
    return "; ".join(parts) if parts else "PDF bytes differ (objects or streams)"


def explain(path: str, a: bytes, b: bytes) -> str:
    suffix = Path(path).suffix.lower()
    try:
        if suffix in (".xlsx", ".docx"):
            return explain_zip(a, b)
        if suffix == ".ipynb":
            return explain_notebook(a, b)
        if suffix == ".pdf":
            return explain_pdf(a, b)
        if suffix in (".png", ".jpg", ".jpeg", ".duckdb"):
            return "binary content differs"
        return first_text_difference(a, b)
    except Exception as exc:  # the explanation is a courtesy; the byte comparison decides
        return f"differs ({type(exc).__name__} while explaining: {exc})"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=2, help="number of runs to compare (default 2)")
    args = parser.parse_args()
    import tempfile

    before = snapshot()
    snaps = []
    with tempfile.TemporaryDirectory(prefix="repro-") as tmp:
        for n in range(1, args.runs + 1):
            run_pipeline(n, Path(tmp))
            snaps.append(snapshot())

    changed_by_first = [f for f in snaps[0] if before.get(f) != snaps[0][f]]
    untracked = sum(f.startswith(("data/clean/", "dashboard/model_data/")) for f in snaps[-1])
    print(f"\nfiles compared: {len(snaps[-1])} ({len(snaps[-1]) - untracked} tracked, {untracked} generated CSVs that git ignores)")
    if changed_by_first:
        print(f"changed by run 1 against the state before it (for information): {len(changed_by_first)}")
        for f in changed_by_first:
            print(f"  {f}")

    failures = 0
    for n in range(1, len(snaps)):
        a, b = snaps[n - 1], snaps[n]
        diff = sorted(f for f in set(a) | set(b) if a.get(f) != b.get(f))
        print(f"\nrun {n} against run {n + 1}: {len(diff)} file(s) differ")
        for f in diff:
            if f not in a or f not in b:
                print(f"  {f}: only in run {n if f in a else n + 1}")
            else:
                print(f"  {f}: {explain(f, a[f], b[f])}")
        failures += len(diff)
    if failures == 0:
        print("\nREPRODUCIBLE: every compared file is byte-for-byte identical across runs")
        return 0
    print(f"\nNOT REPRODUCIBLE: {failures} difference(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
