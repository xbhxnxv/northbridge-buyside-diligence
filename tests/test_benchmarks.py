"""Checks on the SaaS retention benchmarks used in 4d (decisions D12, D28 and D35 to D39).

Sourced benchmarks are transcribed from the publishers' reports into
data/reference/benchmarks_source.csv and copied by notebooks/04d_nrr_grr.ipynb to
outputs/tables/benchmarks.csv. Every benchmark figure in the memo, the key findings, the
interview prep, docs/benchmarks.md and the databook must come from that table. While the
file does not exist, the 4d ranges are labelled as unsourced and no written deliverable
may quote a benchmark (the tests for that state skip once the file exists).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "outputs" / "tables"
SOURCED = TABLES / "benchmarks.csv"
REFERENCE = ROOT / "data" / "reference" / "benchmarks_source.csv"
COMPARISON = TABLES / "4d_benchmark_comparison.csv"
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


# ---------------------------------------------------------------------------
# Once sourced: every benchmark figure shown anywhere comes from benchmarks.csv
# ---------------------------------------------------------------------------

KEYWORDS = ("benchmark", "saas capital", "high alpha", "benchmarkit", "chartmogul", "smb median")
SOURCED_PROSE = ["memo/findings_memo.md", "outputs/key_findings.md", "docs/interview_prep.md", "docs/benchmarks.md"]


def sourced_or_skip() -> list[dict]:
    if not SOURCED.exists():
        pytest.skip(FALLBACK)
    return rows(SOURCED)


def northbridge_values() -> list[float]:
    vals = []
    for name in ("key_figures", "4d_nrr_grr", "4d_benchmark_comparison"):
        for r in rows(TABLES / f"{name}.csv"):
            for cell in r.values():
                try:
                    vals.append(float(cell))
                except (TypeError, ValueError):
                    pass
    return vals


def benchmark_passages(doc: str, text: str) -> list[str]:
    """Sentences (or table rows) that quote a benchmark. For docs/benchmarks.md, the two sections
    that compare Northbridge with the benchmarks; its source and figure tables are checked cell by cell."""
    if doc == "docs/benchmarks.md":
        parts = re.split(r"^## ", text, flags=re.M)
        text = "\n".join(p for p in parts if p.startswith(("The SMB range adopted", "Where Northbridge sits")))
    pieces = re.split(r"(?<=[.;:])\s+|\n", text)
    return [x for x in pieces if any(k in x.lower() for k in KEYWORDS)]


def test_benchmarks_csv_is_the_checked_in_source():
    data = sourced_or_skip()
    ref = rows(REFERENCE)
    assert len(data) == len(ref)
    for a, b in zip(data, ref):
        assert {k: v for k, v in a.items() if k != "value"} == {k: v for k, v in b.items() if k != "value"}
        assert float(a["value"]) == float(b["value"]), (a, b)


def test_benchmark_comparison_recomputed_from_benchmarks_csv():
    data = sourced_or_skip()
    latest = {}
    for r in data:
        latest[r["publisher"]] = max(latest.get(r["publisher"], 0), int(r["year"]))
    smb_median = [r for r in data if r["segment"].startswith("SMB:") and r["statistic"] == "median"]
    rules = {
        "smb": lambda r: int(r["year"]) == latest[r["publisher"]] and r["comparability"] in ("high", "medium"),
        "sc_smb": lambda r: r["source_id"] == "SC25",
        "band": lambda r: int(r["year"]) == latest[r["publisher"]] and r["comparability"] in ("high", "medium")
        and r["segment"] == "SMB: ACV $25k to $50k",
    }
    comp = rows(COMPARISON)
    checked = 0
    for c in comp:
        if c["key"] not in rules:
            continue
        metric = "GRR" if c["measure"] == "GRR" else "NRR"
        vals = [float(r["value"]) for r in smb_median if r["metric"] == metric and rules[c["key"]](r)]
        assert vals and float(c["benchmark_low"]) == min(vals) and float(c["benchmark_high"]) == max(vals), c
        nb = float(c["northbridge_2025"])
        assert c["position"] == ("below" if nb < min(vals) else "above" if nb > max(vals) else "within"), c
        checked += 1
    assert checked >= 8


@pytest.mark.parametrize("doc", SOURCED_PROSE)
def test_every_benchmark_figure_in_prose_is_in_benchmarks_csv(doc):
    data = sourced_or_skip()
    path = ROOT / doc
    if not path.exists():
        pytest.skip(f"{doc} not built")
    bench = {float(r["value"]) for r in data}
    ours = northbridge_values()
    passages = benchmark_passages(doc, path.read_text(encoding="utf-8"))
    assert passages, f"{doc} quotes no benchmark"
    quoted = 0
    for passage in passages:
        for mo in re.finditer(r"(?<![\w.$£])(\d+(?:\.\d+)?)%", passage):
            s = mo.group(1)
            v = float(s)
            if "." not in s:  # benchmark figures are quoted as published; Northbridge's to one decimal place
                assert v in bench, f"{doc}: {mo.group(0)} is not in benchmarks.csv: {passage}"
                quoted += 1
            else:
                assert any(abs(v - x) <= 0.05 + 1e-9 for x in ours) or v in bench, f"{doc}: {mo.group(0)} not in the pipeline: {passage}"
    assert quoted >= 2, f"{doc}: no benchmark figures found in {passages}"


def test_databook_benchmark_rows_match_benchmarks_csv():
    data = sourced_or_skip()
    if not DATABOOK.exists():
        pytest.skip("databook not built")
    from openpyxl import load_workbook
    ws = load_workbook(DATABOOK, data_only=True)["4d NRR GRR"]
    start = next(c.row for c in ws["A"] if isinstance(c.value, str) and c.value.startswith("What good looks like"))
    assert "sourced" in ws.cell(start, 1).value
    medians = {(r["source_id"], r["segment"], r["metric"]): float(r["value"]) for r in data if r["statistic"] == "median"}
    n = 0
    i = start + 2
    while ws.cell(i, 1).value not in (None, "Measure"):
        key = (ws.cell(i, 1).value, ws.cell(i, 4).value, ws.cell(i, 5).value)
        assert key in medians, key
        assert abs(100 * ws.cell(i, 6).value - medians[key]) < 1e-9, (key, ws.cell(i, 6).value)
        n += 1
        i += 1
    assert n >= 20
    # the summary rows: SMB range and SaaS Capital range per measure, and Northbridge's 2025 figure
    comp = {(c["key"], c["measure"]): c for c in rows(COMPARISON)}
    while ws.cell(i, 1).value != "Measure":
        i += 1
    for j in range(i + 1, i + 4):
        measure = ws.cell(j, 1).value
        for col_, key, field in ((2, "smb", "benchmark_low"), (3, "smb", "benchmark_high"), (4, "sc_smb", "benchmark_low"),
                                 (5, "sc_smb", "benchmark_high"), (6, "smb", "northbridge_2025")):
            assert abs(100 * ws.cell(j, col_).value - float(comp[(key, measure)][field])) < 1e-4, (measure, field)
    assert "saas capital" in str(ws.cell(i + 5, 1).value).lower() and "http" in str(ws.cell(i + 5, 1).value)
