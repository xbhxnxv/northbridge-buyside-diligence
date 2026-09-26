"""Checks on the SaaS retention benchmarks used in 4d (decisions D12 and D28).

Sourced benchmarks live in outputs/tables/benchmarks.csv. Until that file
exists, the 4d ranges are labelled "indicative, not sourced" and no written
deliverable may quote a benchmark.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "outputs" / "tables"
SOURCED = TABLES / "benchmarks.csv"
INDICATIVE = TABLES / "4d_benchmarks_indicative.csv"
DATABOOK = ROOT / "databook" / "Northbridge_Databook.xlsx"

FALLBACK = ("D28: no primary benchmark source could be opened from this session, "
            "so outputs/tables/benchmarks.csv does not exist yet")

COLUMNS = ["source_id", "publisher", "title", "year", "url", "accessed_date", "segment", "metric",
           "statistic", "value", "definition_notes", "comparability"]
STATISTICS = {"median", "lower_quartile", "upper_quartile", "range_low", "range_high"}
COMPARABILITY = {"high", "medium", "low"}
PROSE = ["memo/findings_memo.md", "outputs/key_findings.md", "README.md", "docs/interview_prep.md"]


def rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_benchmarks_csv_rows_are_sourced():
    if not SOURCED.exists():
        pytest.skip(FALLBACK)
    data = rows(SOURCED)
    assert data, "benchmarks.csv is empty"
    assert list(data[0].keys()) == COLUMNS
    for r in data:
        assert r["url"].startswith("http"), r
        assert re.fullmatch(r"20\d\d", r["year"]), r
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["accessed_date"]), r
        assert r["statistic"] in STATISTICS, r
        assert r["comparability"] in COMPARABILITY, r
        float(r["value"])


def test_databook_benchmark_rows_match_their_table():
    if SOURCED.exists():
        pytest.skip("sourced benchmarks exist; the figure-by-figure check against benchmarks.csv applies instead")
    if not DATABOOK.exists():
        pytest.skip("databook not built")
    from openpyxl import load_workbook
    ws = load_workbook(DATABOOK, data_only=True)["4d NRR GRR"]
    start = next(c.row for c in ws["A"] if isinstance(c.value, str) and c.value.startswith("What good looks like"))
    assert "indicative, not sourced" in ws.cell(start, 1).value
    expected = rows(INDICATIVE)
    for i, r in enumerate(expected, start=start + 2):
        shown = [ws.cell(i, j).value for j in range(1, 6)]
        assert shown == [r["measure"], r["weaker"], r["typical"], r["strong"], r["basis"]], (i, shown)
    assert ws.cell(start + 2 + len(expected), 1).value is None


@pytest.mark.parametrize("doc", PROSE)
def test_no_benchmark_claims_while_unsourced(doc):
    if SOURCED.exists():
        pytest.skip("sourced benchmarks exist; the figure-by-figure check against benchmarks.csv applies instead")
    path = ROOT / doc
    if not path.exists():
        pytest.skip(f"{doc} not built")
    text = path.read_text(encoding="utf-8").lower()
    assert "benchmark" not in text, f"{doc} mentions benchmarks, but none are sourced (D12, D28)"


def test_no_text_says_indicative_not_sourced():
    if not SOURCED.exists():
        pytest.skip(FALLBACK + "; the indicative label is still the honest one")
    hits = []
    for path in ROOT.rglob("*"):
        if any(p in path.parts for p in (".git", ".venv", "data", "__pycache__")) or not path.is_file():
            continue
        if path.suffix not in {".md", ".py", ".csv", ".json", ".ipynb", ".sql"} or path.name == "test_benchmarks.py":
            continue
        if "indicative, not sourced" in path.read_text(encoding="utf-8", errors="ignore"):
            hits.append(str(path.relative_to(ROOT)))
    assert not hits, hits
