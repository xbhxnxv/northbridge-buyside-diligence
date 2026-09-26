"""Rebuild the whole Northbridge diligence pipeline from a clean clone.

Stages, in order:
  1. generate   regenerate the data room in data/raw/ (seeded, identical every run)
  2. sql        run sql/NN_*.sql in numeric order against a fresh data/northbridge.duckdb
  3. notebooks  execute notebooks/*.ipynb in place, in filename order
  4. databook   build databook/Northbridge_Databook.xlsx
  5. dashboard  export the Power BI star-schema CSVs to dashboard/model_data/
  6. tests      run the pytest tie-outs in tests/

A stage whose inputs do not exist yet (for example no notebooks before Step 3) is
skipped with a message rather than failing. Any stage that does run and fails stops
the pipeline with a non-zero exit code.

Usage:
  python run_all.py                 run every stage
  python run_all.py --only sql tests
  python run_all.py --skip generate
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "northbridge.duckdb"
PY = sys.executable


class Skip(Exception):
    """Raised by a stage that has nothing to run yet."""


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(cmd)}")


def stage_generate() -> None:
    run([PY, "data/generator/generate_data.py"])


def stage_sql() -> None:
    scripts = sorted((ROOT / "sql").glob("[0-9][0-9]_*.sql"))
    if not scripts:
        raise Skip("no sql/NN_*.sql scripts yet")
    import duckdb

    for suffix in ("", ".wal"):
        stale = DB_PATH.with_name(DB_PATH.name + suffix)
        if stale.exists():
            stale.unlink()
    con = duckdb.connect(str(DB_PATH))
    try:
        for script in scripts:
            t0 = time.perf_counter()
            try:
                con.execute(script.read_text(encoding="utf-8"))
            except duckdb.Error as exc:
                raise RuntimeError(f"{script.relative_to(ROOT)}: {exc}") from exc
            print(f"    {script.relative_to(ROOT)}  ({time.perf_counter() - t0:.1f}s)")
    finally:
        con.close()


def stage_notebooks() -> None:
    notebooks = sorted((ROOT / "notebooks").glob("*.ipynb"))
    if not notebooks:
        raise Skip("no notebooks yet")
    for nb in notebooks:
        print(f"    {nb.relative_to(ROOT)}")
        run([
            PY, "-m", "jupyter", "nbconvert",
            "--to", "notebook", "--execute", "--inplace",
            "--ExecutePreprocessor.timeout=1200",
            "--ExecutePreprocessor.kernel_name=python3",
            str(nb.relative_to(ROOT)),
        ])


def stage_databook() -> None:
    script = ROOT / "databook" / "build_databook.py"
    if not script.exists():
        raise Skip("databook/build_databook.py not built yet")
    run([PY, str(script.relative_to(ROOT))])


def stage_dashboard() -> None:
    script = ROOT / "dashboard" / "export_model_data.py"
    if not script.exists():
        raise Skip("dashboard/export_model_data.py not built yet")
    run([PY, str(script.relative_to(ROOT))])


def stage_tests() -> None:
    if not list((ROOT / "tests").glob("test_*.py")):
        raise Skip("no tests yet")
    run([PY, "-m", "pytest", "tests", "-q"])


STAGES = {
    "generate": stage_generate,
    "sql": stage_sql,
    "notebooks": stage_notebooks,
    "databook": stage_databook,
    "dashboard": stage_dashboard,
    "tests": stage_tests,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", choices=STAGES, help="run only these stages")
    parser.add_argument("--skip", nargs="+", choices=STAGES, default=[], help="skip these stages")
    args = parser.parse_args()

    selected = [s for s in STAGES if (not args.only or s in args.only) and s not in args.skip]
    summary: list[tuple[str, str, float]] = []
    start = time.perf_counter()

    for name in selected:
        print(f"\n=== {name} ===")
        t0 = time.perf_counter()
        try:
            STAGES[name]()
            status = "ok"
        except Skip as reason:
            status = f"skipped ({reason})"
            print(f"    {status}")
        except Exception as exc:  # report which stage broke, then stop
            print(f"    FAILED: {exc}")
            summary.append((name, "FAILED", time.perf_counter() - t0))
            break
        summary.append((name, status, time.perf_counter() - t0))

    print("\n=== summary ===")
    for name, status, secs in summary:
        print(f"  {name:<10} {secs:6.1f}s  {status}")
    print(f"  {'total':<10} {time.perf_counter() - start:6.1f}s")
    return 1 if any(status == "FAILED" for _, status, _ in summary) else 0


if __name__ == "__main__":
    sys.exit(main())
