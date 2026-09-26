"""Tie-outs and integrity checks for the Northbridge pipeline.

Run after `python run_all.py` (or `python run_all.py --only sql`), which builds
data/northbridge.duckdb. Every test reads the database read-only.
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "northbridge.duckdb"

TABLES = ["customers", "products", "subscriptions", "invoices", "costs", "management_accounts"]


@pytest.fixture(scope="session")
def con():
    if not DB_PATH.exists():
        pytest.skip("data/northbridge.duckdb not built; run `python run_all.py` first")
    c = duckdb.connect(str(DB_PATH), read_only=True)
    yield c
    c.close()


def scalar(con, sql: str):
    return con.execute(sql).fetchone()[0]


def csv_rows(name: str) -> list[dict]:
    with open(RAW / f"{name}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Step 0: the data room is the one the brief specifies
# ---------------------------------------------------------------------------

EXPECTED_ROWS = {
    "customers": 2_192,
    "products": 6,
    "subscriptions": 3_502,
    "invoices": 92_732,
    "costs": 192,
    "management_accounts": 48,
}

# Published in the project brief, rounded to the nearest pound.
EXPECTED_MGMT_REVENUE = {2022: 28_232_152, 2023: 32_174_370, 2024: 37_261_399, 2025: 45_771_419}


@pytest.mark.parametrize("name", TABLES)
def test_data_room_row_counts(name):
    assert len(csv_rows(name)) == EXPECTED_ROWS[name]


def test_data_room_management_revenue():
    totals: dict[int, Decimal] = {}
    for r in csv_rows("management_accounts"):
        y = int(r["month"][:4])
        totals[y] = totals.get(y, Decimal(0)) + Decimal(r["total_revenue"])
    assert {y: round(v) for y, v in totals.items()} == EXPECTED_MGMT_REVENUE


# ---------------------------------------------------------------------------
# Step 2.1: the typed load drops nothing and rounds nothing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", TABLES)
def test_load_row_counts_match_csv(con, name):
    assert scalar(con, f"SELECT count(*) FROM raw_{name}") == len(csv_rows(name))


MONEY_COLUMNS = {
    "invoices": ["amount"],
    "subscriptions": ["monthly_price"],
    "costs": ["hosting_cost", "support_staff_cost", "third_party_licence_cost", "total_cost_of_delivery"],
    "management_accounts": ["revenue_core_platform", "revenue_analytics_add-on", "revenue_payments_module",
                            "revenue_implementation_services", "total_revenue", "cost_of_sales", "gross_profit"],
}


@pytest.mark.parametrize("name,column", [(t, c) for t, cols in MONEY_COLUMNS.items() for c in cols])
def test_load_money_totals_match_csv_text(con, name, column):
    """Sum of the CSV text parsed as exact decimals equals the sum of the loaded DECIMAL column."""
    expected = sum(Decimal(r[column]) for r in csv_rows(name))
    loaded_column = "revenue_analytics_addon" if column == "revenue_analytics_add-on" else column
    assert scalar(con, f"SELECT sum({loaded_column}) FROM raw_{name}") == expected


def test_load_no_null_dates_introduced(con):
    """Blank end_date is the only permitted null date: every other date parsed."""
    assert scalar(con, "SELECT count(*) FROM raw_invoices WHERE invoice_date IS NULL") == 0
    assert scalar(con, "SELECT count(*) FROM raw_customers WHERE signup_date IS NULL") == 0
    assert scalar(con, "SELECT count(*) FROM raw_subscriptions WHERE start_date IS NULL") == 0
    blank_end = sum(1 for r in csv_rows("subscriptions") if r["end_date"] == "")
    assert scalar(con, "SELECT count(*) FROM raw_subscriptions WHERE end_date IS NULL") == blank_end


# ---------------------------------------------------------------------------
# Step 2.2: profile integrity
# ---------------------------------------------------------------------------

def test_profile_primary_keys_unique(con):
    assert scalar(con, "SELECT count(*) FROM prof_primary_keys WHERE row_count <> distinct_keys OR null_keys > 0") == 0


def test_profile_issue_register_complete(con):
    ids = [r[0] for r in con.execute("SELECT issue_id FROM prof_issues ORDER BY issue_id").fetchall()]
    assert ids == [f"P{i:02d}" for i in range(1, 12)]


def test_profile_issue_register_years_add_up(con):
    bad = scalar(con, """
        SELECT count(*) FROM prof_issues
        WHERE abs(amount_net - (net_2022 + net_2023 + net_2024 + net_2025)) > 0.005
    """)
    assert bad == 0
