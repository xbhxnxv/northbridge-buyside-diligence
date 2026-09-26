"""Small helpers shared by the notebooks: paths, database access and table formatting.

Notebooks run with notebooks/ as the working directory (nbconvert's default), so paths
are resolved from this file's location rather than the current directory.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "northbridge.duckdb"
DOCS = ROOT / "docs"
TABLES = ROOT / "outputs" / "tables"
CHARTS = ROOT / "outputs" / "charts"
CLEAN = ROOT / "data" / "clean"


def connect(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def q(con: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    """Run a query and return a DataFrame with DECIMAL columns as floats."""
    df = con.execute(sql).df()
    for col in df.columns:
        if df[col].map(lambda v: isinstance(v, Decimal)).any():
            df[col] = df[col].astype(float)
    return df


# ---------------------------------------------------------------------------
# Number formatting (British conventions, negatives in brackets for money)
# ---------------------------------------------------------------------------

def gbp(x, dp: int = 0) -> str:
    if x is None or pd.isna(x):
        return ""
    x = float(x)
    s = f"£{abs(x):,.{dp}f}"
    return f"({s})" if x < 0 else s


def num(x, dp: int = 0) -> str:
    if x is None or pd.isna(x):
        return ""
    return f"{float(x):,.{dp}f}"


def pct(x, dp: int = 1) -> str:
    """Format a value already expressed in percent (e.g. 12.3 -> '12.3%')."""
    if x is None or pd.isna(x):
        return ""
    return f"{float(x):.{dp}f}%"


def md_table(df: pd.DataFrame, formats: dict | None = None, index: bool = False) -> str:
    """Render a DataFrame as a GitHub-flavoured markdown table.

    formats maps column name -> callable returning a string. Numeric columns without a
    formatter get thousands separators; everything else is str().
    """
    formats = formats or {}
    frame = df.reset_index() if index else df
    cols = list(frame.columns)
    numeric = {c for c in cols if pd.api.types.is_numeric_dtype(frame[c]) and not pd.api.types.is_bool_dtype(frame[c])}

    def cell(col, v):
        if col in formats:
            return formats[col](v)
        if isinstance(v, (list, tuple, np.ndarray)):
            return ", ".join(map(str, v))
        if v is None or pd.isna(v):
            return ""
        if col in numeric and (col == "year" or col.endswith("_year")):
            return str(int(v))
        if col in numeric:
            fv = float(v)
            return f"{fv:,.0f}" if fv.is_integer() else f"{fv:,.2f}"
        if hasattr(v, "strftime"):
            return v.strftime("%Y-%m-%d")
        return str(v)

    aligns = ["---:" if (c in numeric or c in formats) else "---" for c in cols]
    lines = ["| " + " | ".join(map(str, cols)) + " |", "| " + " | ".join(aligns) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(cell(c, row[c]).replace("|", "\\|") for c in cols) + " |")
    return "\n".join(lines)


def replace_block(path: Path, name: str, content: str) -> None:
    """Replace the text between <!-- BEGIN GENERATED: name --> and <!-- END GENERATED: name -->.

    Lets a hand-written document carry numbers that are regenerated on every run.
    """
    begin, end = f"<!-- BEGIN GENERATED: {name} -->", f"<!-- END GENERATED: {name} -->"
    text = path.read_text(encoding="utf-8")
    if begin not in text or end not in text:
        raise ValueError(f"{path.name}: markers for block '{name}' not found")
    head, rest = text.split(begin, 1)
    _, tail = rest.split(end, 1)
    path.write_text(f"{head}{begin}\n{content.strip()}\n{end}{tail}", encoding="utf-8")
