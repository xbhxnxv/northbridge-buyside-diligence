"""Export the Power BI model data and the expected value of every measure.

Writes to dashboard/model_data/ a star schema (plus one snowflake level for product line):

    DimDate ─┬─< FactRevenue >─┬─ DimCustomer
             ├─< FactMRR     >─┤
             └─< FactCost        DimProduct >── DimProductLine ──< FactCost
                                     (FactRevenue and FactMRR join DimProduct)

and dashboard/expected_values.csv: each measure in dashboard/measures.dax computed in Python
for a set of filter contexts (each year; each year by product line; 2025 by region group,
region and size band), so the Power BI build can be checked number by number.

The Python here follows the DAX definitions in measures.dax, including which slicers each
measure ignores. It reads the DuckDB cube built by the SQL stage.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "northbridge.duckdb"
MODEL = ROOT / "dashboard" / "model_data"
EXPECTED = ROOT / "dashboard" / "expected_values.csv"

SIZE_ORDER = {"Micro (1-9)": 1, "Small (10-49)": 2, "Medium (50-249)": 3, "Large (250+)": 4}
LINE_ORDER = {"Core Platform": 1, "Analytics Add-on": 2, "Payments Module": 3, "Implementation Services": 4}


def export(con) -> dict[str, pd.DataFrame]:
    q = lambda s: con.execute(s).df()
    tables = {
        "FactRevenue": q("""
            SELECT customer_id, product_id, month_start, gross_billings, credit_notes, net_revenue, recurring_net, oneoff_net,
                   oneoff_signup_net, oneoff_other_net, overdue_amount, invoice_count, credit_note_count
            FROM fact_revenue_monthly ORDER BY month_start, customer_id, product_id"""),
        "FactMRR": q("SELECT customer_id, product_id, month_start, mrr FROM fact_mrr_monthly ORDER BY month_start, customer_id, product_id"),
        "FactCost": q("""
            SELECT product_line, month AS month_start, hosting_cost, support_staff_cost, third_party_licence_cost,
                   total_cost_of_delivery AS total_cost
            FROM clean_costs ORDER BY month, product_line"""),
        "DimCustomer": q("""
            SELECT customer_id, customer_name_std AS customer_name, signup_date, signup_year, signup_quarter AS cohort,
                   industry, region, region_group, company_size AS size_band, acquisition_channel AS channel, account_manager,
                   is_large_account, name_collision_flag, industry_missing_flag
            FROM dim_customer ORDER BY customer_id"""),
        "DimProduct": q("SELECT product_id, product_name, product_line, revenue_type, list_price FROM dim_product ORDER BY product_id"),
        "DimDate": q("""
            SELECT month_start, year, quarter, year_quarter, month_number, month_name, year_month, is_year_end, is_quarter_end
            FROM dim_date ORDER BY month_start"""),
    }
    tables["DimCustomer"]["size_band_order"] = tables["DimCustomer"].size_band.map(SIZE_ORDER)
    lines = tables["DimProduct"][["product_line", "revenue_type"]].drop_duplicates()
    lines["line_order"] = lines.product_line.map(LINE_ORDER)
    tables["DimProductLine"] = lines.rename(columns={"revenue_type": "line_type"}).sort_values("line_order")
    MODEL.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(MODEL / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    return tables


class Measures:
    """Python versions of the DAX measures, evaluated for a filter context."""

    def __init__(self, t: dict[str, pd.DataFrame]):
        prod = t["DimProduct"][["product_id", "product_line"]]
        cust = t["DimCustomer"][["customer_id", "region_group", "region", "size_band"]]
        self.rev = t["FactRevenue"].merge(prod, on="product_id").merge(cust, on="customer_id")
        self.mrr = t["FactMRR"].merge(prod, on="product_id").merge(cust, on="customer_id")
        self.cost = t["FactCost"]
        for df in (self.rev, self.mrr, self.cost):
            df["month_start"] = pd.to_datetime(df["month_start"])
            df["year"] = df.month_start.dt.year

    @staticmethod
    def _apply(df, flt, customer_filters=True):
        for k, v in flt.items():
            if k in ("region_group", "region", "size_band") and not customer_filters:
                continue
            if k in df.columns:
                df = df[df[k] == v]
        return df

    def _dec_mrr_by_customer(self, year, flt):
        m = self._apply(self.mrr, flt)
        m = m[m.month_start == pd.Timestamp(year, 12, 1)]
        return m.groupby("customer_id").mrr.sum()

    def evaluate(self, year: int, flt: dict) -> dict:
        r = self._apply(self.rev[self.rev.year == year], flt)
        r_py = self._apply(self.rev[self.rev.year == year - 1], flt)
        out = {}
        net = r.net_revenue.sum()
        out["Net Revenue"] = net
        out["Recurring Revenue"] = r.recurring_net.sum()
        out["One-off Revenue"] = r.oneoff_net.sum()
        out["Other Implementation Revenue"] = r.oneoff_other_net.sum()
        out["Recurring %"] = out["Recurring Revenue"] / net if net else np.nan
        out["Net Revenue YoY %"] = net / r_py.net_revenue.sum() - 1 if len(r_py) else np.nan
        close = self._dec_mrr_by_customer(year, flt)
        out["MRR"] = close.sum()                                   # December is the last month of a year context
        out["ARR"] = 12 * close.sum()
        out["Active Customers"] = int((close > 0).sum())
        opening = self._dec_mrr_by_customer(year - 1, flt)
        out["ARR YoY %"] = close.sum() / opening.sum() - 1 if opening.sum() else np.nan
        if year >= 2023 and opening.sum():
            c = close.reindex(opening.index, fill_value=0.0)
            out["NRR"] = c.sum() / opening.sum()
            out["GRR"] = np.minimum(c, opening).sum() / opening.sum()
            out["Logo Churn Rate"] = float((c <= 0).mean())
        else:
            out["NRR"] = out["GRR"] = out["Logo Churn Rate"] = np.nan
        # Top 10 concentration ignores customer slicers (whole-company measure; see measures.dax)
        rc = self._apply(self.rev[self.rev.year == year], flt, customer_filters=False)
        by_c = rc.groupby("customer_id").net_revenue.sum().sort_values(ascending=False)
        out["Top 10 Concentration %"] = by_c.head(10).sum() / by_c.sum() if by_c.sum() else np.nan
        # Gross profit: cost exists only at product line x month, so it is blank under a customer filter
        if any(k in flt for k in ("region_group", "region", "size_band")):
            out["Gross Profit"] = out["Gross Margin %"] = np.nan
        else:
            cst = self._apply(self.cost[self.cost.year == year], flt).total_cost.sum()
            out["Gross Profit"] = net - cst
            out["Gross Margin %"] = (net - cst) / net if net else np.nan
        return out


def expected_values(t) -> pd.DataFrame:
    m = Measures(t)
    contexts = []
    for y in (2022, 2023, 2024, 2025):
        contexts.append(("year", y, "", ""))
        for pl in LINE_ORDER:
            contexts.append(("year x product line", y, "product_line", pl))
    for col, values in (("region_group", ["UK", "EU"]), ("region", sorted(t["DimCustomer"].region.unique())),
                        ("size_band", list(SIZE_ORDER))):
        for v in values:
            contexts.append((f"2025 x {col}", 2025, col, v))
    rows = []
    for ctype, y, col, val in contexts:
        res = m.evaluate(y, {col: val} if col else {})
        for measure, value in res.items():
            rows.append({"context": ctype, "year": y, "filter_column": col, "filter_value": val, "measure": measure,
                         "value": None if pd.isna(value) else round(float(value), 6)})
    return pd.DataFrame(rows)


def main():
    con = duckdb.connect(str(DB), read_only=True)
    t = export(con)
    ev = expected_values(t)
    ev.to_csv(EXPECTED, index=False)
    print(f"model_data: {', '.join(f'{k} ({len(v):,})' for k, v in t.items())}")
    print(f"expected_values.csv: {len(ev):,} rows")


if __name__ == "__main__":
    main()
