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


# ---------------------------------------------------------------------------
# Step 2.3: cleaning
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", TABLES)
def test_clean_rows_reconcile_to_raw(con, name):
    """raw rows = clean rows + removed rows, per table."""
    raw = scalar(con, f"SELECT count(*) FROM raw_{name}")
    clean = scalar(con, f"SELECT count(*) FROM clean_{name}")
    removed = scalar(con, "SELECT count(*) FROM clean_removed_invoices") if name == "invoices" else 0
    assert raw == clean + removed


def test_removed_rows_are_exactly_the_duplicate_copies(con):
    assert scalar(con, "SELECT count(*) FROM clean_removed_invoices") == 40
    assert scalar(con, """
        SELECT count(*) FROM clean_removed_invoices r
        WHERE NOT EXISTS (SELECT 1 FROM clean_invoices k
                          WHERE k.invoice_id = r.kept_invoice_id AND k.customer_id = r.customer_id
                            AND k.product_id = r.product_id AND k.invoice_date = r.invoice_date
                            AND k.amount = r.amount AND k.status = r.status)
    """) == 0
    # no exact duplicates remain
    assert scalar(con, """
        SELECT count(*) FROM (SELECT 1 FROM clean_invoices
                              GROUP BY customer_id, product_id, invoice_date, amount, revenue_type, status
                              HAVING count(*) > 1)
    """) == 0


def test_p04_amount_removed(con):
    assert scalar(con, "SELECT sum(amount) FROM clean_removed_invoices") == Decimal("96957.26")


def test_every_credit_note_linked_to_its_original(con):
    assert scalar(con, "SELECT count(*) FROM clean_invoices WHERE is_credit_note AND credit_note_original_id IS NULL") == 0
    bad = scalar(con, """
        SELECT count(*) FROM clean_invoices cn
        LEFT JOIN clean_invoices o ON o.invoice_id = cn.credit_note_original_id
        WHERE cn.is_credit_note
          AND (o.invoice_id IS NULL OR o.is_credit_note OR o.customer_id <> cn.customer_id
               OR o.product_id <> cn.product_id OR o.invoice_date <> cn.invoice_date OR o.amount <> -cn.amount
               OR o.credited_by_id <> cn.invoice_id)
    """)
    assert bad == 0
    # one-to-one: no original is linked by two credit notes
    assert scalar(con, """SELECT count(*) FROM (SELECT credit_note_original_id FROM clean_invoices
                          WHERE is_credit_note GROUP BY 1 HAVING count(*) > 1)""") == 0


def test_cleaning_actions_explain_the_revenue_change(con):
    """raw invoice total + revenue impact of all cleaning actions = cube net (current setting)."""
    raw = scalar(con, "SELECT sum(amount) FROM raw_invoices")
    impact = scalar(con, "SELECT sum(revenue_impact) FROM cleaning_actions")
    cube = scalar(con, "SELECT sum(net_revenue) FROM fact_revenue_monthly")
    assert raw + impact == cube


def test_customers_never_dropped_and_industry_filled(con):
    assert scalar(con, "SELECT count(*) FROM clean_customers WHERE industry IS NULL") == 0
    assert scalar(con, "SELECT count(*) FROM clean_customers WHERE industry = 'Unknown'") == \
        scalar(con, "SELECT count(*) FROM raw_customers WHERE industry IS NULL")


# ---------------------------------------------------------------------------
# Step 2.4: revenue cube
# ---------------------------------------------------------------------------

def test_cube_net_equals_clean_invoice_net_total_and_by_year(con):
    rows = con.execute("""
        WITH inv AS (
            SELECT year(month_start) AS y,
                   sum(invoice_amount((SELECT anomaly_treatment FROM cfg_settings),
                                      amount_as_reported, amount_flipped, amount_excluded)) AS net
            FROM clean_invoices GROUP BY 1),
        cube AS (SELECT year(month_start) AS y, sum(net_revenue) AS net FROM fact_revenue_monthly GROUP BY 1)
        SELECT inv.y, inv.net, cube.net FROM inv FULL JOIN cube USING (y) ORDER BY 1
    """).fetchall()
    assert [r[0] for r in rows] == [2022, 2023, 2024, 2025]
    for y, inv_net, cube_net in rows:
        assert inv_net == cube_net, y
    assert sum(r[1] for r in rows) == scalar(con, "SELECT sum(net_revenue) FROM fact_revenue_monthly")


def test_cube_row_identities(con):
    assert scalar(con, """
        SELECT count(*) FROM fact_revenue_monthly
        WHERE recurring_net + oneoff_net <> net_revenue
           OR gross_billings + credit_notes <> net_revenue
           OR oneoff_signup_net + oneoff_other_net <> oneoff_net
    """) == 0


@pytest.mark.parametrize("table,grain", [
    ("fact_revenue_monthly", "customer_id, product_id, month_start"),
    ("fact_mrr_monthly", "customer_id, product_id, month_start"),
    ("dim_customer", "customer_id"),
    ("dim_product", "product_id"),
    ("dim_date", "month_start"),
])
def test_no_duplicate_grain_rows(con, table, grain):
    assert scalar(con, f"SELECT count(*) FROM (SELECT {grain} FROM {table} GROUP BY {grain} HAVING count(*) > 1)") == 0


@pytest.mark.parametrize("fact", ["fact_revenue_monthly", "fact_mrr_monthly"])
def test_cube_keys_exist_in_dimensions(con, fact):
    assert scalar(con, f"SELECT count(*) FROM {fact} f WHERE NOT EXISTS (SELECT 1 FROM dim_customer d WHERE d.customer_id = f.customer_id)") == 0
    assert scalar(con, f"SELECT count(*) FROM {fact} f WHERE NOT EXISTS (SELECT 1 FROM dim_product d WHERE d.product_id = f.product_id)") == 0
    assert scalar(con, f"SELECT count(*) FROM {fact} f WHERE NOT EXISTS (SELECT 1 FROM dim_date d WHERE d.month_start = f.month_start)") == 0


def test_mrr_is_recurring_billings_before_credit_notes(con):
    mrr = scalar(con, "SELECT sum(mrr) FROM fact_mrr_monthly")
    billings = scalar(con, "SELECT sum(gross_billings) FROM fact_revenue_monthly WHERE revenue_type = 'recurring'")
    assert mrr == billings


def test_anomaly_switch_moves_revenue_by_exactly_the_anomaly_amounts(con):
    rows = con.execute("""
        WITH a AS (SELECT year(month_start) AS y, sum(net_revenue) AS net FROM revenue_cube('as_reported') GROUP BY 1),
             f AS (SELECT year(month_start) AS y, sum(net_revenue) AS net FROM revenue_cube('flipped') GROUP BY 1),
             e AS (SELECT year(month_start) AS y, sum(net_revenue) AS net FROM revenue_cube('excluded') GROUP BY 1),
             n AS (SELECT year(month_start) AS y, sum(amount) AS anomaly FROM clean_invoices WHERE anomaly_flag GROUP BY 1)
        SELECT a.y, a.net, f.net, e.net, coalesce(n.anomaly, 0)
        FROM a JOIN f USING (y) JOIN e USING (y) LEFT JOIN n USING (y) ORDER BY 1
    """).fetchall()
    assert len(rows) == 4
    for y, as_rep, flipped, excluded, anomaly in rows:
        assert flipped - as_rep == -2 * anomaly, y     # anomaly amounts are negative
        assert excluded - as_rep == -anomaly, y
    assert scalar(con, "SELECT count(*) FROM clean_invoices WHERE anomaly_flag AND amount >= 0") == 0


def test_exports_match_tables(con):
    clean_dir = ROOT / "data" / "clean"
    for t in ["fact_revenue_monthly", "fact_mrr_monthly", "dim_customer", "dim_product", "dim_date"]:
        with open(clean_dir / f"{t}.csv", newline="", encoding="utf-8") as f:
            n = sum(1 for _ in f) - 1
        assert n == scalar(con, f"SELECT count(*) FROM {t}"), t


def test_source_to_cube_walk_adds_up():
    path = ROOT / "outputs" / "tables" / "step2_source_to_cube_walk.csv"
    if not path.exists():
        pytest.skip("walk not built; run the notebooks")
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            total = sum(Decimal(r[c]) for c in ["raw_gross_billings", "less_duplicates", "anomaly_treatment", "credit_notes"])
            assert abs(total - Decimal(r["cube_net"])) < Decimal("0.005"), r["year"]


def test_qa_log_ids_sequential(con):
    ids = [r[0] for r in con.execute("SELECT qa_id FROM qa_log ORDER BY qa_id").fetchall()]
    assert ids == [f"Q{i:02d}" for i in range(1, len(ids) + 1)]


# ---------------------------------------------------------------------------
# Step 3: reconciliation (checks that hold whatever anomaly treatment is chosen)
# ---------------------------------------------------------------------------

def test_recon_walk_adds_up(con):
    bad = scalar(con, """
        SELECT count(*) FROM recon_walk
        WHERE raw_gross_billings + less_duplicates + anomaly_treatment + credit_notes <> cube_net
           OR cube_net + unreconciled_difference <> mgmt_total
    """)
    assert bad == 0
    assert scalar(con, "SELECT count(*) FROM recon_walk") == 4


def test_recon_walk_matches_management_accounts(con):
    assert scalar(con, "SELECT sum(mgmt_total) FROM recon_walk") == \
        scalar(con, "SELECT sum(total_revenue) FROM clean_management_accounts")


def test_costs_tie_to_cost_of_sales_every_month(con):
    assert scalar(con, "SELECT count(*) FROM recon_costs_monthly WHERE difference <> 0") == 0
    assert scalar(con, "SELECT count(*) FROM recon_costs_monthly") == 48


def test_options_grid_complete(con):
    assert scalar(con, "SELECT count(*) FROM recon_options_monthly") == 3 * 48


def test_product_lines_sum_to_cube_total(con):
    bad = scalar(con, """
        SELECT count(*) FROM (
            SELECT p.month, sum(p.cube_net) AS lines, any_value(r.cube_net) AS total
            FROM recon_product_line_monthly p JOIN recon_monthly r USING (month) GROUP BY p.month)
        WHERE lines <> total
    """)
    assert bad == 0


def test_anomaly_setting_is_excluded_and_ties_to_lines(con):
    """Step 3 decision D01: excluded is the only treatment that ties to the product lines every month."""
    assert scalar(con, "SELECT anomaly_treatment FROM cfg_settings") == "excluded"
    tied = dict(con.execute("SELECT treatment, months_tied_to_lines FROM recon_options_summary").fetchall())
    assert tied["excluded"] == 48
    assert tied["as_reported"] < 48 and tied["flipped"] < 48


def test_no_negative_mrr_rows(con):
    assert scalar(con, "SELECT count(*) FROM fact_mrr_monthly WHERE mrr <= 0") == 0


def test_every_month_labelled(con):
    assert scalar(con, "SELECT count(*) FROM recon_monthly") == 48
    assert scalar(con, "SELECT count(*) FROM recon_monthly WHERE status NOT IN ('tied', 'explained', 'unexplained') OR status IS NULL") == 0
    # tied and explained months have no difference; unexplained months carry an explanation
    assert scalar(con, "SELECT count(*) FROM recon_monthly WHERE status <> 'unexplained' AND difference <> 0") == 0
    assert scalar(con, "SELECT count(*) FROM recon_monthly WHERE status <> 'tied' AND explanation IS NULL") == 0
    assert scalar(con, "SELECT count(*) FROM recon_product_line_monthly WHERE status IS NULL") == 0


def test_annual_difference_equals_documented_unexplained_items(con):
    rows = con.execute("""
        SELECT a.year, a.difference, coalesce(u.amount, 0)
        FROM recon_annual a
        LEFT JOIN (SELECT year, sum(amount) AS amount FROM recon_unexplained_items GROUP BY 1) u USING (year)
    """).fetchall()
    assert len(rows) == 4
    for year, diff, items in rows:
        assert diff == items, year


def test_unexplained_items_are_the_management_line_gaps(con):
    """Every unexplained month is one where the cube ties to the product lines but not the reported total."""
    assert scalar(con, """
        SELECT count(*) FROM recon_unexplained_items u
        JOIN clean_management_accounts m USING (month)
        WHERE u.amount <> m.lines_less_total OR NOT m.lines_total_mismatch_flag
    """) == 0
    assert scalar(con, "SELECT count(*) FROM recon_unexplained_items") == \
        scalar(con, "SELECT count(*) FROM clean_management_accounts WHERE lines_total_mismatch_flag")


def test_product_lines_tie_every_month_under_chosen_setting(con):
    assert scalar(con, "SELECT count(*) FROM recon_product_line_monthly WHERE difference <> 0") == 0
    assert scalar(con, "SELECT count(*) FROM recon_product_line_monthly") == 4 * 48


def test_annual_reconciliation_within_tolerance_apart_from_documented_items(con):
    """After removing the documented unexplained items, every year ties to the penny."""
    assert scalar(con, """
        SELECT count(*) FROM recon_annual a
        WHERE abs(a.difference - coalesce((SELECT sum(amount) FROM recon_unexplained_items u WHERE u.year = a.year), 0)) >= 0.01
    """) == 0
