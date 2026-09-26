"""Build databook/Northbridge_Databook.xlsx from outputs/tables/.

Conventions (the way advisers lay out a databook):
- Inputs loaded from the pipeline are values in blue font. Everything else (totals, shares,
  differences, growth rates, checks) is an Excel formula in black font.
- £ figures are stored in pounds and displayed in £'000 through the number format, so
  tie-outs work to the penny while the page reads in thousands.
- Every tab has a title, a units line, a source note, its tables, a native Excel chart and a
  DRAFT commentary box drafted from outputs/tables/key_findings.csv.
- Every check is a formula returning TRUE or FALSE, listed on the Checks tab with one
  overall check cell.

After building, the workbook is recalculated with LibreOffice (databook/recalc.py) and
every cell is scanned for errors. databook/cell_map.json records where the key figures sit
so the tests can compare them with outputs/tables/ to the penny.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.series import SeriesLabel
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as col

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "outputs" / "tables"
OUT = ROOT / "databook" / "Northbridge_Databook.xlsx"
CELL_MAP = ROOT / "databook" / "cell_map.json"
CONFIG = json.loads((ROOT / "report_config.json").read_text(encoding="utf-8"))

FONT = "Arial"
SIZE = 10
BLUE = "0000FF"
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
SECTION_FILL = PatternFill("solid", fgColor="D9E1F2")
DRAFT_FILL = PatternFill("solid", fgColor="FFF2CC")
THIN = Side(style="thin", color="A6A6A6")

GBP_K = '#,##0,;(#,##0,);"-"'
GBP = '#,##0;(#,##0);"-"'
GBP2 = '#,##0.00;(#,##0.00);"-"'
PCT = '0.0%;(0.0%);"-"'
PTS = '0.00;(0.00);"-"'
INT = '#,##0;(#,##0);"-"'
FACTOR = "0.0000"
DATE = "mmm yyyy"

YEARS = [2022, 2023, 2024, 2025]
SERIES_COLOURS = ["2A78D6", "EB6834", "1BAF7A", "EDA100"]


def t(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLES / f"{name}.csv")


def q(sheet: str) -> str:
    return f"'{sheet}'"


class Book:
    def __init__(self) -> None:
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.checks: list[tuple[str, str, str]] = []
        self.cells: dict[str, dict] = {}
        self.tabs: list[tuple[str, str]] = []
        self.pos: dict[str, object] = {}

    # --- sheet set-up -----------------------------------------------------------------
    def sheet(self, name: str, title: str, units: str, source: str, description: str, widths=None):
        ws = self.wb.create_sheet(name)
        ws.sheet_view.showGridLines = False
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.oddHeader.center.text = "&A"
        ws.oddFooter.center.text = "Page &P of &N"
        ws.oddFooter.left.text = f"{CONFIG['project']}: DRAFT"
        self.text(ws, "A1", title, bold=True)
        self.text(ws, "A2", units)
        self.text(ws, "A3", source)
        ws.column_dimensions["A"].width = 30
        for i, w in enumerate(widths or [], start=2):
            ws.column_dimensions[col(i)].width = w
        self.tabs.append((name, description))
        return ws

    # --- cell writers -----------------------------------------------------------------
    @staticmethod
    def text(ws, ref, value, bold=False, wrap=False, colour="000000", fill=None, italic=False):
        c = ws[ref]
        c.value = value
        c.font = Font(name=FONT, size=SIZE, bold=bold, color=colour, italic=italic)
        c.alignment = Alignment(wrap_text=wrap, vertical="top")
        if fill:
            c.fill = fill
        return c

    @staticmethod
    def inp(ws, ref, value, fmt=None):
        c = ws[ref]
        if isinstance(value, float) and pd.isna(value):
            value = None
        value = value.item() if hasattr(value, "item") else value
        if isinstance(value, float) and fmt in (GBP_K, GBP, GBP2):
            value = round(value, 2)  # money to the penny (avoids -0.00000001 showing as (0))
        c.value = value
        c.font = Font(name=FONT, size=SIZE, color=BLUE)
        if fmt:
            c.number_format = fmt
        return c

    @staticmethod
    def fml(ws, ref, formula, fmt=None, bold=False):
        c = ws[ref]
        c.value = formula
        c.font = Font(name=FONT, size=SIZE, bold=bold)
        if fmt:
            c.number_format = fmt
        return c

    def header(self, ws, row, first_col, labels):
        for i, label in enumerate(labels):
            c = ws.cell(row=row, column=first_col + i, value=label)
            c.font = Font(name=FONT, size=SIZE, bold=True, color="FFFFFF")
            c.fill = HEADER_FILL
            c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
        ws.row_dimensions[row].height = 30

    def section(self, ws, ref, label):
        self.text(ws, ref, label, bold=True, fill=SECTION_FILL)

    def check(self, ws, ref, formula, description):
        c = self.fml(ws, ref, formula, bold=True)
        c.alignment = Alignment(horizontal="center")
        self.checks.append((description, ws.title, ref))
        return c

    def mark(self, key, ws, ref, table, column, where=None, scale=1.0, tol=0.005):
        """Record where a key figure sits, for the penny-level test against outputs/tables."""
        self.cells[key] = {"sheet": ws.title, "cell": ref, "table": table, "column": column,
                           "where": where or {}, "scale": scale, "tol": tol}

    def commentary(self, ws, top, left, width, height, text):
        rng = f"{col(left)}{top}:{col(left + width - 1)}{top + height - 1}"
        ws.merge_cells(rng)
        c = ws.cell(row=top, column=left, value="DRAFT commentary for review (drafted from outputs/key_findings.md):\n\n" + text)
        c.font = Font(name=FONT, size=SIZE, italic=True)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        c.fill = DRAFT_FILL
        for r in ws[rng]:
            for cc in r:
                cc.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
                cc.fill = DRAFT_FILL

    @staticmethod
    def style_chart(chart, title, y_title, x_title, fmt=None, width=18, height=8.5):
        chart.title = title
        chart.y_axis.title = y_title
        chart.x_axis.title = x_title
        chart.width, chart.height = width, height
        chart.legend.position = "b"
        if fmt:
            chart.y_axis.numFmt = fmt
        chart.y_axis.majorGridlines = None
        chart.x_axis.delete = False
        chart.y_axis.delete = False
        for i, s in enumerate(chart.series):
            colour = SERIES_COLOURS[i % len(SERIES_COLOURS)]
            s.graphicalProperties.solidFill = colour
            s.graphicalProperties.line.solidFill = colour


def findings_for(tab: str) -> str:
    kf = t("key_findings")
    rows = kf[kf.databook_tab == tab]
    return "\n\n".join(f"{r.finding_id} ({r.materiality}): {r.finding}" for r in rows.itertuples())


# =======================================================================================
# Tabs
# =======================================================================================

def cover(b: Book):
    ws = b.wb.create_sheet("Cover")
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 110
    b.text(ws, "B3", CONFIG["project"], bold=True)
    b.text(ws, "B5", "Buy-side financial due diligence: Transaction Analytics databook", bold=True)
    b.text(ws, "B7", f"Target: {CONFIG['target']}")
    b.text(ws, "B8", "Status: DRAFT for discussion. Subject to management's answers to the Q&A log.")
    b.text(ws, "B9", f"Date: {CONFIG['report_date']}")
    b.text(ws, "B10", "Data: data-room extract, January 2022 to December 2025 (six tables).")
    b.text(ws, "B12", CONFIG["disclaimer"], wrap=True, italic=True)
    ws.row_dimensions[12].height = 30
    b.text(ws, "B14", "Colour convention: blue figures are inputs loaded from the pipeline (outputs/tables/); black figures are Excel formulas.")
    b.text(ws, "B15", "Units: £'000 unless a column says otherwise. Negative numbers are shown in brackets.")


def contents(b: Book):
    ws = b.wb.create_sheet("Contents", 1)
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 100
    b.text(ws, "A1", "Contents", bold=True)
    b.header(ws, 3, 1, ["Tab", "What it shows"])
    for i, (name, desc) in enumerate(b.tabs, start=4):
        c = b.text(ws, f"A{i}", name, colour="0563C1")
        c.hyperlink = f"#{q(name)}!A1"
        c.font = Font(name=FONT, size=SIZE, color="0563C1", underline="single")
        b.text(ws, f"B{i}", desc)


def basis(b: Book):
    ws = b.sheet("Basis", "Basis of preparation", "Units: £'000 unless stated", "Source: data room; docs/cleaning_log.md; docs/metric_definitions.md",
                 "Data sources, period, definitions, cleaning adjustments and limitations", widths=[14, 14, 14, 12, 12, 12, 12, 12, 12, 60])
    lines = [
        ("Data sources", "Six CSV tables from the seller's data room: customers, products, subscriptions, invoices, costs and monthly management accounts."),
        ("Period", "January 2022 to December 2025, monthly. Customer signups and contract start dates go back to 2017."),
        ("Revenue basis", "Cleaned invoice ledger (the revenue cube). It ties to the management accounts' product lines in all 48 months (Reconciliation tab)."),
        ("Definitions", "All metrics follow docs/metric_definitions.md (link below). Key terms: net revenue = billings plus credit notes; MRR = recurring billings before credit notes; ARR = December MRR × 12."),
        ("NRR and GRR", "Available for 2023, 2024 and 2025 only: the data has no December 2021 opening point."),
        ("Price increases", "Every recurring line was billed 5% above its contracted price from January 2024 and a further 7% from January 2025; treated as a price increase (Q15)."),
    ]
    r = 5
    for k_, v in lines:
        b.text(ws, f"A{r}", k_, bold=True)
        ws.merge_cells(f"B{r}:K{r}")
        b.text(ws, f"B{r}", v, wrap=True)
        ws.row_dimensions[r].height = 28
        r += 1
    c = b.text(ws, f"B{r}", CONFIG["repo_url"] + "/blob/main/docs/metric_definitions.md", colour="0563C1")
    c.hyperlink = CONFIG["repo_url"] + "/blob/main/docs/metric_definitions.md"
    b.text(ws, f"A{r}", "Metric definitions", bold=True)
    r += 2
    b.section(ws, f"A{r}", "Cleaning adjustments: change to net revenue (£'000)")
    r += 1
    cs = t("step2_cleaning_summary")
    b.header(ws, r, 1, ["Adjustment", "Issue", "Table", "Action", "Records", "2022", "2023", "2024", "2025", "Total", "Rule"])
    first = r + 1
    for i, row in enumerate(cs.itertuples(), start=first):
        b.inp(ws, f"A{i}", row.action_id); b.inp(ws, f"B{i}", row.issue_id); b.inp(ws, f"C{i}", row.table_name)
        b.inp(ws, f"D{i}", row.action_type); b.inp(ws, f"E{i}", int(row.records), INT)
        for j, y in enumerate(YEARS):
            b.inp(ws, f"{col(6 + j)}{i}", float(getattr(row, f"impact_{y}")), GBP_K)
        b.fml(ws, f"J{i}", f"=SUM(F{i}:I{i})", GBP_K)
        b.text(ws, f"K{i}", row.rule, wrap=True)
        ws.row_dimensions[i].height = 40
    last = first + len(cs) - 1
    tot = last + 1
    b.text(ws, f"A{tot}", "Total", bold=True)
    for j in range(5):
        cl = col(6 + j)
        b.fml(ws, f"{cl}{tot}", f"=SUM({cl}{first}:{cl}{last})", GBP_K, bold=True)
    ws.column_dimensions["K"].width = 80
    r = tot + 2
    b.text(ws, f"A{r}", "Check: raw invoice total + adjustments = cube net revenue (all years)")
    rec = q("Reconciliation")
    w = b.pos["walk"]
    b.check(ws, f"F{r}", f"=ABS(SUM({rec}!B{w['raw']}:E{w['raw']})+SUM({rec}!B{w['credit']}:E{w['credit']})+J{tot}-SUM({rec}!B{w['cube']}:E{w['cube']}))<0.01",
            "Basis: raw invoices plus cleaning adjustments equal the cube net revenue")
    r += 2
    b.section(ws, f"A{r}", "Limitations")
    lims = [
        "Synthetic data room; no access to management, contracts, the general ledger or the bank statements.",
        "Four monthly differences between reported total revenue and the product lines are unexplained (Q07, Q12 to Q14).",
        "Margin by customer size depends on the cost allocation basis; the data room has no cost-to-serve driver.",
        "SaaS benchmark ranges on the 4d tab are indicative and not sourced.",
        "Customer lifecycle before 2022 relies on subscription dates; invoices before 2022 are not in the data room.",
    ]
    for i, l in enumerate(lims, start=r + 1):
        ws.merge_cells(f"A{i}:K{i}")
        b.text(ws, f"A{i}", f"- {l}", wrap=True)


def reconciliation(b: Book):
    name = "Reconciliation"
    ws = b.sheet(name, "Reconciliation of the revenue cube to the management accounts",
                 "Units: £'000 unless stated; differences are cube less reported",
                 "Source: outputs/tables/step3_*.csv (sql/04_reconciliation.sql); anomaly treatment: excluded (decision D01)",
                 "Monthly, annual and product-line reconciliation and the source-to-reported walk",
                 widths=[14, 14, 14, 14, 14, 11, 14, 12, 90])
    m = t("step3_recon_monthly")
    b.section(ws, "A5", "Monthly revenue reconciliation")
    b.header(ws, 6, 1, ["Month", "Year", "Mgmt total revenue", "Mgmt sum of lines", "Cube net revenue", "Difference", "Difference %",
                        "Difference vs lines", "Status", "Explanation"])
    ws.column_dimensions["J"].width = 100
    for i, r in enumerate(m.itertuples(), start=7):
        b.inp(ws, f"A{i}", dt.datetime.strptime(str(r.month)[:10], "%Y-%m-%d"), DATE)
        b.fml(ws, f"B{i}", f"=YEAR(A{i})", "0")
        b.inp(ws, f"C{i}", float(r.mgmt_total_revenue), GBP_K)
        b.inp(ws, f"D{i}", float(r.mgmt_sum_of_lines), GBP_K)
        b.inp(ws, f"E{i}", float(r.cube_net), GBP_K)
        b.fml(ws, f"F{i}", f"=E{i}-C{i}", GBP)
        b.fml(ws, f"G{i}", f"=IF(C{i}=0,0,F{i}/C{i})", '0.000%;(0.000%);"-"')
        b.fml(ws, f"H{i}", f"=E{i}-D{i}", GBP)
        b.inp(ws, f"I{i}", r.status)
        b.inp(ws, f"J{i}", r.explanation if isinstance(r.explanation, str) else "")
    last = 6 + len(m)
    ws.freeze_panes = "C7"
    tot = last + 1
    b.text(ws, f"A{tot}", "Total", bold=True)
    for cl in "CDEFH":
        b.fml(ws, f"{cl}{tot}", f"=SUM({cl}7:{cl}{last})", GBP_K if cl in "CDE" else GBP, bold=True)
    b.check(ws, f"I{tot}", f"=ABS(H{tot})<0.01", "Reconciliation: cube ties to the management product lines in total")

    # Annual table
    a0 = tot + 3
    b.section(ws, f"A{a0 - 1}", "Annual reconciliation")
    b.header(ws, a0, 1, ["Year", "Mgmt total revenue", "Cube net revenue", "Difference", "Difference %", "Months unexplained",
                         "Unexplained items", "Cube net per pipeline", "Check"])
    ann = t("step3_recon_annual")
    for i, y in enumerate(YEARS, start=a0 + 1):
        b.inp(ws, f"A{i}", y, "0")
        b.fml(ws, f"B{i}", f"=SUMIFS($C$7:$C${last},$B$7:$B${last},A{i})", GBP_K)
        b.fml(ws, f"C{i}", f"=SUMIFS($E$7:$E${last},$B$7:$B${last},A{i})", GBP_K)
        b.fml(ws, f"D{i}", f"=C{i}-B{i}", GBP)
        b.fml(ws, f"E{i}", f"=IF(B{i}=0,0,D{i}/B{i})", '0.000%;(0.000%);"-"')
        b.fml(ws, f"F{i}", f'=COUNTIFS($B$7:$B${last},A{i},$I$7:$I${last},"unexplained")', INT)
        b.fml(ws, f"G{i}", f'=SUMIFS($F$7:$F${last},$B$7:$B${last},A{i},$I$7:$I${last},"unexplained")', GBP)
        b.inp(ws, f"H{i}", float(ann[ann.year == y].cube_net.iloc[0]), GBP_K)
        b.check(ws, f"I{i}", f"=AND(ABS(D{i}-G{i})<0.005,ABS(C{i}-H{i})<0.005)",
                f"Reconciliation {y}: difference equals the documented unexplained items and the cube total ties to the pipeline")
        b.mark(f"recon_cube_net_{y}", ws, f"C{i}", "step3_recon_annual", "cube_net", {"year": y})
        b.mark(f"recon_difference_{y}", ws, f"D{i}", "step3_recon_annual", "difference", {"year": y})
    a_last = a0 + len(YEARS)

    walk = t("step3_walk")
    w0 = a_last + 4
    b.section(ws, f"A{w0 - 1}", "Source-to-reported walk (anomaly treatment: excluded)")
    b.header(ws, w0, 1, ["£'000"] + [str(y) for y in YEARS])
    labels = ["Raw gross billings", "Less duplicates", "Anomaly treatment", "Credit notes", "Cube net revenue",
              "Unreconciled difference", "Management total revenue", "Check: cube net equals annual table"]
    for j, lab in enumerate(labels):
        b.text(ws, f"A{w0 + 1 + j}", lab, bold=lab in ("Cube net revenue", "Management total revenue"))
    for k_, y in enumerate(YEARS):
        cl = col(2 + k_)
        wr = walk[walk.year == y].iloc[0]
        b.inp(ws, f"{cl}{w0 + 1}", float(wr.raw_gross_billings), GBP_K)
        b.inp(ws, f"{cl}{w0 + 2}", float(wr.less_duplicates), GBP_K)
        b.inp(ws, f"{cl}{w0 + 3}", float(wr.anomaly_treatment), GBP_K)
        b.inp(ws, f"{cl}{w0 + 4}", float(wr.credit_notes), GBP_K)
        b.fml(ws, f"{cl}{w0 + 5}", f"=SUM({cl}{w0 + 1}:{cl}{w0 + 4})", GBP_K, bold=True)
        b.fml(ws, f"{cl}{w0 + 7}", f"=B{a0 + 1 + k_}", GBP_K, bold=True)
        b.fml(ws, f"{cl}{w0 + 6}", f"={cl}{w0 + 7}-{cl}{w0 + 5}", GBP)
        b.check(ws, f"{cl}{w0 + 8}", f"=ABS({cl}{w0 + 5}-C{a0 + 1 + k_})<0.005", f"Walk {y}: cube net from the walk equals the annual reconciliation")
        b.mark(f"walk_cube_net_{y}", ws, f"{cl}{w0 + 5}", "step3_walk", "cube_net", {"year": y})
    b.pos["walk"] = {"raw": w0 + 1, "credit": w0 + 4, "cube": w0 + 5}
    b.pos["recon_annual"] = (a0 + 1, a0 + len(YEARS))

    # Product-line annual reconciliation
    p0 = w0 + 12
    b.section(ws, f"A{p0 - 1}", "Product-line reconciliation (annual)")
    pl = t("step3_recon_product_line_annual")
    b.header(ws, p0, 1, ["Product line", "Year", "Mgmt revenue", "Cube net revenue", "Difference", "Months tied"])
    for i, r in enumerate(pl.itertuples(), start=p0 + 1):
        b.inp(ws, f"A{i}", r.product_line); b.inp(ws, f"B{i}", int(r.year), "0")
        b.inp(ws, f"C{i}", float(r.mgmt_revenue), GBP_K); b.inp(ws, f"D{i}", float(r.cube_net), GBP_K)
        b.fml(ws, f"E{i}", f"=D{i}-C{i}", GBP); b.inp(ws, f"F{i}", int(r.months_tied), INT)
    pl_last = p0 + len(pl)
    b.text(ws, f"A{pl_last + 1}", "Total", bold=True)
    b.fml(ws, f"E{pl_last + 1}", f"=SUM(E{p0 + 1}:E{pl_last})", GBP, bold=True)
    b.check(ws, f"F{pl_last + 1}", f"=ABS(E{pl_last + 1})<0.005", "Reconciliation: every product line ties in every year")

    ch = BarChart()
    ch.type = "col"
    ch.add_data(Reference(ws, min_col=6, min_row=6, max_row=last), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=7, max_row=last))
    b.style_chart(ch, "Monthly difference: cube less reported total revenue (£)", "£", "Month", GBP, width=24)
    ch.x_axis.tickLblPos = "low"
    ws.add_chart(ch, f"A{pl_last + 4}")
    b.commentary(ws, pl_last + 4, 10, 1, 18, findings_for("Reconciliation"))
    return {"walk_rows": (w0 + 1, w0 + 4, w0 + 5)}


def tab_4a(b: Book):
    name = "4a Revenue quality"
    ws = b.sheet(name, "4a. Revenue quality: recurring against one-off, ARR and growth", "Units: £'000 unless stated",
                 "Source: outputs/tables/4a_revenue_mix.csv, 4a_arr.csv, 4a_uplift_factors.csv (notebooks/04a_revenue_quality.ipynb)",
                 "Recurring and one-off revenue, ARR at each year end, headline against normalised growth",
                 widths=[13, 13, 13, 13, 13, 11, 11, 11, 11, 11, 11, 14, 9])
    mix = t("4a_revenue_mix")
    b.section(ws, "A5", "Revenue by type")
    b.header(ws, 6, 1, ["Year", "Recurring", "Implementation at signup", "Other implementation", "One-off", "Net revenue",
                        "Recurring %", "Other impl. %", "Headline growth", "Recurring growth", "Growth ex other impl.",
                        "Gap: headline less recurring (pts)", "Net revenue per Reconciliation", "Check"])
    for i, y in enumerate(YEARS, start=7):
        r = mix[mix.year == y].iloc[0]
        b.inp(ws, f"A{i}", y, "0")
        b.inp(ws, f"B{i}", float(r.recurring), GBP_K); b.inp(ws, f"C{i}", float(r.signup_implementation), GBP_K)
        b.inp(ws, f"D{i}", float(r.other_implementation), GBP_K)
        b.fml(ws, f"E{i}", f"=C{i}+D{i}", GBP_K); b.fml(ws, f"F{i}", f"=B{i}+E{i}", GBP_K, bold=True)
        b.fml(ws, f"G{i}", f"=B{i}/F{i}", PCT); b.fml(ws, f"H{i}", f"=D{i}/F{i}", PCT)
        if i > 7:
            b.fml(ws, f"I{i}", f"=F{i}/F{i - 1}-1", PCT); b.fml(ws, f"J{i}", f"=B{i}/B{i - 1}-1", PCT)
            b.fml(ws, f"K{i}", f"=(F{i}-D{i})/(F{i - 1}-D{i - 1})-1", PCT)
            b.fml(ws, f"L{i}", f"=(I{i}-J{i})*100", PTS)
            b.mark(f"headline_growth_{y}", ws, f"I{i}", "4a_growth", "headline_growth_pct", {"year": y}, 0.01, 1e-6)
            b.mark(f"recurring_growth_{y}", ws, f"J{i}", "4a_growth", "recurring_growth_pct", {"year": y}, 0.01, 1e-6)
            b.mark(f"growth_ex_other_{y}", ws, f"K{i}", "4a_growth", "growth_ex_other_implementation_pct", {"year": y}, 0.01, 1e-6)
        ra, rb_ = b.pos["recon_annual"]
        b.fml(ws, f"M{i}", f"=SUMIFS({q('Reconciliation')}!$C${ra}:$C${rb_},{q('Reconciliation')}!$A${ra}:$A${rb_},A{i})", GBP_K)
        b.check(ws, f"N{i}", f"=ABS(F{i}-M{i})<0.005", f"4a {y}: net revenue ties to the Reconciliation tab")
        b.mark(f"net_revenue_{y}", ws, f"F{i}", "4a_revenue_mix", "net_revenue", {"year": y})
        b.mark(f"recurring_pct_{y}", ws, f"G{i}", "4a_revenue_mix", "recurring_pct", {"year": y}, 0.01, 1e-6)
    ws.freeze_panes = "B7"
    arr = t("4a_arr")
    b.section(ws, "A13", "ARR at each year end (December MRR × 12)")
    b.header(ws, 14, 1, ["Year", "ARR", "Active customers", "ARR per customer (£)", "Uplift factor k", "ARR growth", "ARR growth before price increase"])
    for i, y in enumerate(YEARS, start=15):
        r = arr[arr.year == y].iloc[0]
        b.inp(ws, f"A{i}", y, "0"); b.inp(ws, f"B{i}", float(r.arr), GBP_K); b.inp(ws, f"C{i}", int(r.active_customers), INT)
        b.fml(ws, f"D{i}", f"=B{i}/C{i}", GBP)
        b.inp(ws, f"E{i}", 1.0 if pd.isna(r.k) else float(r.k), FACTOR)
        if i > 15:
            b.fml(ws, f"F{i}", f"=B{i}/B{i - 1}-1", PCT); b.fml(ws, f"G{i}", f"=(B{i}/E{i})/B{i - 1}-1", PCT)
            b.mark(f"arr_growth_ex_price_{y}", ws, f"G{i}", "4a_arr", "arr_growth_ex_price_pct", {"year": y}, 0.01, 1e-6)
        b.mark(f"arr_{y}", ws, f"B{i}", "4a_arr", "arr", {"year": y})
    ch = BarChart(); ch.type = "col"; ch.grouping = "stacked"; ch.overlap = 100
    ch.add_data(Reference(ws, min_col=2, max_col=4, min_row=6, max_row=10), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=7, max_row=10))
    b.style_chart(ch, "Net revenue by type (£'000)", "£'000", "Year", GBP_K)
    ws.add_chart(ch, "A21")
    b.commentary(ws, 21, 12, 8, 18, findings_for("4a"))


def tab_4b(b: Book):
    name = "4b Concentration"
    ws = b.sheet(name, "4b. Customer concentration", "Units: £'000 unless stated",
                 "Source: outputs/tables/4b_*.csv (notebooks/04b_concentration.ipynb)",
                 "Top 1/5/10/20 shares, large accounts, declining top customers",
                 widths=[9, 13, 13, 10, 13, 13, 10, 14, 10, 12, 10, 10])
    tn = t("4b_top_n_shares")
    b.section(ws, "A5", "Share of net revenue and of recurring revenue held by the largest customers")
    b.header(ws, 6, 1, ["Year", "Top N", "Top-N net revenue", "Total net revenue", "Share of net", "Top-N recurring",
                        "Total recurring", "Share of recurring", "Total per 4a", "Check"])
    r0 = 7
    for i, r in enumerate(tn.itertuples(), start=r0):
        b.inp(ws, f"A{i}", int(r.year), "0"); b.inp(ws, f"B{i}", int(r.top_n), "0")
        b.inp(ws, f"C{i}", float(r.net_revenue_top_n), GBP_K); b.inp(ws, f"D{i}", float(r.net_revenue_total), GBP_K)
        b.fml(ws, f"E{i}", f"=C{i}/D{i}", PCT)
        b.inp(ws, f"F{i}", float(r.recurring_top_n), GBP_K); b.inp(ws, f"G{i}", float(r.recurring_total), GBP_K)
        b.fml(ws, f"H{i}", f"=F{i}/G{i}", PCT)
        b.fml(ws, f"I{i}", f"=SUMIFS({q('4a Revenue quality')}!$F$7:$F$10,{q('4a Revenue quality')}!$A$7:$A$10,A{i})", GBP_K)
        b.check(ws, f"J{i}", f"=AND(ABS(D{i}-I{i})<0.005,E{i}>0,E{i}<=1)", f"4b {int(r.year)} top {int(r.top_n)}: total ties to 4a and share is between 0 and 100%")
        b.mark(f"top{int(r.top_n)}_share_{int(r.year)}", ws, f"E{i}", "4b_top_n_shares", "share_of_net_pct", {"year": int(r.year), "top_n": int(r.top_n)}, 0.01, 1e-6)
    last = r0 + len(tn) - 1
    ws.freeze_panes = "A7"
    # pivot grid for the chart
    g0 = last + 3
    b.section(ws, f"A{g0 - 1}", "Share of net revenue by year (for the chart)")
    b.header(ws, g0, 1, ["Year", "Top 1", "Top 5", "Top 10", "Top 20"])
    for i, y in enumerate(YEARS, start=g0 + 1):
        b.inp(ws, f"A{i}", str(y))
        for j, n in enumerate((1, 5, 10, 20)):
            b.fml(ws, f"{col(2 + j)}{i}", f"=SUMIFS($E${r0}:$E${last},$A${r0}:$A${last},{y},$B${r0}:$B${last},{n})", PCT)
    ch = LineChart()
    ch.add_data(Reference(ws, min_col=2, max_col=5, min_row=g0, max_row=g0 + 4), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=g0 + 1, max_row=g0 + 4))
    b.style_chart(ch, "Share of net revenue held by the largest customers", "Share of net revenue", "Year", "0%")
    ws.add_chart(ch, "M5")
    # large accounts
    la = t("4b_large_account_share")
    l0 = g0 + 7
    b.section(ws, f"A{l0 - 1}", "Six large accounts (subscription lines priced at 10x list or more)")
    b.header(ws, l0, 1, ["Year", "Large accounts' net revenue", "Total net revenue", "Share"])
    for i, r in enumerate(la.itertuples(), start=l0 + 1):
        b.inp(ws, f"A{i}", int(r.year), "0"); b.inp(ws, f"B{i}", float(r.net_revenue_large), GBP_K)
        b.inp(ws, f"C{i}", float(r.net_revenue_total), GBP_K); b.fml(ws, f"D{i}", f"=B{i}/C{i}", PCT)
        b.mark(f"large_account_share_{int(r.year)}", ws, f"D{i}", "4b_large_account_share", "large_share_of_net_pct", {"year": int(r.year)}, 0.01, 1e-6)
    # run-rate of top 10
    rr = t("4b_top10_runrate")
    k0 = l0 + 7
    b.section(ws, f"A{k0 - 1}", "Top 10 customers by 2025 net revenue: run-rate (ARR = December MRR × 12)")
    b.header(ws, k0, 1, ["Rank", "Customer", "Dec 2024 ARR", "Dec 2025 ARR", "Change", "Change %", "Peak ARR", "Change vs peak", "% vs peak", "Declining"])
    for i, r in enumerate(rr.itertuples(), start=k0 + 1):
        b.inp(ws, f"A{i}", int(r.rank_latest_year), "0"); b.inp(ws, f"B{i}", r.customer_id)
        b.inp(ws, f"C{i}", float(r.dec_arr_prior), GBP_K); b.inp(ws, f"D{i}", float(r.dec_arr_latest), GBP_K)
        b.fml(ws, f"E{i}", f"=D{i}-C{i}", GBP_K); b.fml(ws, f"F{i}", f"=IF(C{i}=0,0,E{i}/C{i})", PCT)
        b.inp(ws, f"G{i}", float(r.peak_arr), GBP_K); b.fml(ws, f"H{i}", f"=D{i}-G{i}", GBP_K)
        b.fml(ws, f"I{i}", f"=IF(G{i}=0,0,H{i}/G{i})", PCT); b.fml(ws, f"J{i}", f'=IF(E{i}<0,"yes","no")')
        b.mark(f"{r.customer_id}_arr_change", ws, f"E{i}", "4b_top10_runrate", "change_vs_prior_dec", {"customer_id": r.customer_id})
    b.commentary(ws, 24, 13, 9, 14, findings_for("4b"))


def tab_4c(b: Book):
    name = "4c Cohorts"
    ws = b.sheet(name, "4c. Cohorts and retention (tenure-matched)", "Units: % of customers or of month-3 MRR",
                 "Source: outputs/tables/4c_*.csv (notebooks/04c_cohorts.ipynb). Logo retention from subscription dates; revenue retention from invoiced MRR, cohorts from 2022Q1",
                 "Retention at 6, 12 and 18 months by signup year, older against newer cohorts, retention triangles",
                 widths=[11, 11, 11, 11, 11, 11, 11, 11, 11])
    tm = t("4c_tenure_matched")
    b.section(ws, "A5", "Logo retention at the same tenure, by signup year")
    b.header(ws, 6, 1, ["Signup year", "Customers (6m)", "Active at 6m", "Retention 6m", "Customers (12m)", "Active at 12m",
                        "Retention 12m", "Customers (18m)", "Active at 18m", "Retention 18m"])
    yrs = sorted(tm.signup_year.unique())
    for i, y in enumerate(yrs, start=7):
        b.inp(ws, f"A{i}", str(y))
        for j, T in enumerate((6, 12, 18)):
            d = tm[(tm.signup_year == y) & (tm.tenure_months == T)]
            c1, c2, c3 = col(2 + 3 * j), col(3 + 3 * j), col(4 + 3 * j)
            if len(d):
                b.inp(ws, f"{c1}{i}", int(d.customers.iloc[0]), INT); b.inp(ws, f"{c2}{i}", int(d.active_customers.iloc[0]), INT)
                b.fml(ws, f"{c3}{i}", f"={c2}{i}/{c1}{i}", PCT)
                if T == 12:
                    b.mark(f"retention_12m_{y}", ws, f"{c3}{i}", "4c_tenure_matched", "logo_retention_pct", {"signup_year": int(y), "tenure_months": 12}, 0.01, 1e-6)
            else:
                b.text(ws, f"{c3}{i}", "n/a")
    last = 6 + len(yrs)
    ws.freeze_panes = "B7"
    on = t("4c_old_vs_new_cohorts")
    o0 = last + 3
    b.section(ws, f"A{o0 - 1}", "Older (2017-2022) against newer (2023+) signups at the same tenure")
    b.header(ws, o0, 1, ["Group", "Tenure (months)", "Customers reaching tenure", "Still subscribed", "Retention"])
    for i, r in enumerate(on.itertuples(), start=o0 + 1):
        b.inp(ws, f"A{i}", r.group); b.inp(ws, f"B{i}", int(r.tenure_months), "0")
        b.inp(ws, f"C{i}", int(r.customers_reaching_tenure), INT); b.inp(ws, f"D{i}", int(r.active_customers), INT)
        b.fml(ws, f"E{i}", f"=D{i}/C{i}", PCT)
        key = "older" if r.group.startswith("2017") else "newer"
        b.mark(f"retention_{int(r.tenure_months)}m_{key}", ws, f"E{i}", "4c_old_vs_new_cohorts", "logo_retention_pct",
               {"group": r.group, "tenure_months": int(r.tenure_months)}, 0.01, 1e-6)
    ch = LineChart()
    for j, T in enumerate((6, 12, 18)):
        c = 4 + 3 * j
        ch.add_data(Reference(ws, min_col=c, min_row=6, max_row=last), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=7, max_row=last))
    b.style_chart(ch, "Logo retention at 6, 12 and 18 months by signup year", "Still subscribed", "Signup year", "0%")
    ws.add_chart(ch, "L5")
    b.commentary(ws, 24, 12, 9, 12, findings_for("4c"))
    # Logo retention triangle (inputs) with a colour scale
    tri = t("4c_logo_retention_triangle").pivot(index="signup_quarter", columns="tenure", values="logo_retention_pct")
    tri = tri[[c_ for c_ in tri.columns if c_ <= 36]]
    h0 = max(o0 + 10, 42)
    b.section(ws, f"A{h0 - 1}", "Logo retention triangle: share of each signup quarter still subscribed, by months since signup (0 to 36)")
    b.header(ws, h0, 1, ["Signup quarter"] + [str(c_) for c_ in tri.columns])
    for i, (qtr, row) in enumerate(tri.iterrows(), start=h0 + 1):
        b.inp(ws, f"A{i}", qtr)
        for j, v in enumerate(row.values):
            if pd.notna(v):
                b.inp(ws, f"{col(2 + j)}{i}", float(v) / 100, "0%")
    rng = f"B{h0 + 1}:{col(1 + len(tri.columns))}{h0 + len(tri)}"
    ws.conditional_formatting.add(rng, ColorScaleRule(start_type="num", start_value=0.5, start_color="CDE2FB",
                                                      end_type="num", end_value=1, end_color="184F95"))
    for j in range(len(tri.columns)):
        ws.column_dimensions[col(2 + j)].width = max(ws.column_dimensions[col(2 + j)].width or 0, 6)


def tab_4d(b: Book):
    name = "4d NRR GRR"
    ws = b.sheet(name, "4d. Net and gross revenue retention (2023 to 2025 only: no December 2021 in the data)",
                 "Units: £'000 for MRR; % for NRR and GRR",
                 "Source: outputs/tables/4d_nrr_grr.csv (notebooks/04d_nrr_grr.ipynb)",
                 "NRR and GRR by year with sensitivities (excluding top 5, excluding price) and indicative benchmarks",
                 widths=[34, 10, 14, 14, 14, 10, 10, 12, 12])
    n = t("4d_nrr_grr")
    b.section(ws, "A5", "NRR and GRR (December to December MRR)")
    b.header(ws, 6, 1, ["Basis", "Year", "Uplift factor k", "Opening MRR", "Closing MRR (same customers)", "Closing MRR capped at opening",
                        "NRR", "GRR", "Customers at opening", "Customers retained"])
    for i, r in enumerate(n.itertuples(), start=7):
        b.inp(ws, f"A{i}", r.basis); b.inp(ws, f"B{i}", int(r.year), "0"); b.inp(ws, f"C{i}", float(r.uplift_factor), FACTOR)
        b.inp(ws, f"D{i}", float(r.opening_mrr), GBP_K); b.inp(ws, f"E{i}", float(r.closing_mrr_same_customers), GBP_K)
        b.inp(ws, f"F{i}", float(r.closing_mrr_capped), GBP_K)
        b.fml(ws, f"G{i}", f"=E{i}/D{i}", PCT); b.fml(ws, f"H{i}", f"=F{i}/D{i}", PCT)
        b.inp(ws, f"I{i}", int(r.customers_opening), INT); b.inp(ws, f"J{i}", int(r.customers_retained), INT)
        b.mark(f"nrr_{r.basis}_{int(r.year)}", ws, f"G{i}", "4d_nrr_grr", "nrr_pct", {"year": int(r.year), "basis": r.basis}, 0.01, 1e-6)
        b.mark(f"grr_{r.basis}_{int(r.year)}", ws, f"H{i}", "4d_nrr_grr", "grr_pct", {"year": int(r.year), "basis": r.basis}, 0.01, 1e-6)
    last = 6 + len(n)
    ws.freeze_panes = "B7"
    c0 = last + 2
    b.text(ws, f"A{c0}", "Check: reported opening MRR × 12 equals prior-year ARR on the 4a tab")
    reported = n[n.basis == "reported"]
    for j, r in enumerate(reported.itertuples()):
        row = 7 + n.index[(n.basis == "reported") & (n.year == r.year)][0]
        b.check(ws, f"{col(2 + j)}{c0}", f"=ABS(D{row}*12-SUMIFS({q('4a Revenue quality')}!$B$15:$B$18,{q('4a Revenue quality')}!$A$15:$A$18,B{row}-1))<0.01",
                f"4d {int(r.year)}: opening MRR ties to the 4a ARR")
    g0 = c0 + 3
    b.section(ws, f"A{g0 - 1}", "For the chart")
    b.header(ws, g0, 1, ["Year", "NRR reported", "NRR excluding price increase", "GRR reported"])
    for i, y in enumerate((2023, 2024, 2025), start=g0 + 1):
        b.inp(ws, f"A{i}", str(y))
        b.fml(ws, f"B{i}", f'=SUMIFS($G$7:$G${last},$A$7:$A${last},"reported",$B$7:$B${last},{y})', PCT)
        b.fml(ws, f"C{i}", f'=SUMIFS($G$7:$G${last},$A$7:$A${last},"excluding price increase",$B$7:$B${last},{y})', PCT)
        b.fml(ws, f"D{i}", f'=SUMIFS($H$7:$H${last},$A$7:$A${last},"reported",$B$7:$B${last},{y})', PCT)
    ch = BarChart(); ch.type = "col"
    ch.add_data(Reference(ws, min_col=2, max_col=4, min_row=g0, max_row=g0 + 3), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=g0 + 1, max_row=g0 + 3))
    b.style_chart(ch, "NRR and GRR, 2023 to 2025", "% of opening MRR", "Year", "0%")
    ch.y_axis.scaling.min = 0.7; ch.y_axis.scaling.max = 1.1
    ws.add_chart(ch, "L5")
    bm = t("4d_benchmarks_indicative")
    k0 = g0 + 6
    b.section(ws, f"A{k0 - 1}", "What good looks like for SMB-focused B2B SaaS (indicative, not sourced)")
    b.header(ws, k0, 1, ["Measure", "Weaker", "Typical", "Strong", "Basis"])
    for i, r in enumerate(bm.itertuples(), start=k0 + 1):
        for j, v in enumerate([r.measure, r.weaker, r.typical, r.strong, r.basis]):
            b.inp(ws, f"{col(1 + j)}{i}", v)
    b.commentary(ws, 24, 12, 9, 12, findings_for("4d"))


def tab_4e(b: Book):
    name = "4e ARR bridge"
    ws = b.sheet(name, "4e. ARR bridge and revenue bridge", "Units: £'000",
                 "Source: outputs/tables/4e_arr_bridge.csv, 4e_revenue_bridge.csv (notebooks/04e_arr_bridge.ipynb)",
                 "ARR bridge December to December and the year-on-year revenue bridge",
                 widths=[14, 14, 14, 14, 12, 12, 12, 12])
    ab = t("4e_arr_bridge")
    comps = [("opening_arr", "Opening ARR"), ("new", "New customers"), ("cross_sell", "Cross-sell"), ("upsell", "Upsell"),
             ("price_increase", "Price increase"), ("downgrade", "Downgrade"), ("contraction", "Contraction"), ("churn", "Churn")]
    b.section(ws, "A5", "ARR bridge (December MRR × 12, customer × product line)")
    b.header(ws, 6, 1, ["£'000", "2023", "2024", "2025"])
    for j, (k_, lab) in enumerate(comps):
        b.text(ws, f"A{7 + j}", lab)
    close_row, cube_row, chk_row = 7 + len(comps), 8 + len(comps), 9 + len(comps)
    b.text(ws, f"A{close_row}", "Closing ARR", bold=True)
    b.text(ws, f"A{cube_row}", "Closing ARR per cube")
    b.text(ws, f"A{chk_row}", "Check")
    for i, y in enumerate((2023, 2024, 2025)):
        cl = col(2 + i)
        r = ab[ab.year == y].iloc[0]
        for j, (k_, lab) in enumerate(comps):
            if k_ == "opening_arr" and i > 0:
                b.fml(ws, f"{cl}{7}", f"={col(1 + i)}{close_row}", GBP_K)
            else:
                b.inp(ws, f"{cl}{7 + j}", float(r[k_]), GBP_K)
        b.fml(ws, f"{cl}{close_row}", f"=SUM({cl}7:{cl}{close_row - 1})", GBP_K, bold=True)
        b.fml(ws, f"{cl}{cube_row}", f"=SUMIFS({q('4a Revenue quality')}!$B$15:$B$18,{q('4a Revenue quality')}!$A$15:$A$18,{y})", GBP_K)
        b.check(ws, f"{cl}{chk_row}", f"=AND(ABS({cl}{close_row}-{cl}{cube_row})<0.01,ABS({cl}7-SUMIFS({q('4a Revenue quality')}!$B$15:$B$18,{q('4a Revenue quality')}!$A$15:$A$18,{y - 1}))<0.01)",
                f"4e ARR bridge {y}: opening plus components equals closing ARR from the cube")
        b.mark(f"arr_bridge_closing_{y}", ws, f"{cl}{close_row}", "4e_arr_bridge", "closing_arr", {"year": y})
        b.mark(f"arr_bridge_price_{y}", ws, f"{cl}{11}", "4e_arr_bridge", "price_increase", {"year": y})
    ws.freeze_panes = "B7"
    # waterfall helper for 2025 (stacked bar with an invisible base)
    w0 = chk_row + 3
    b.section(ws, f"A{w0 - 1}", "Waterfall helper, 2025 (formulas)")
    b.header(ws, w0, 1, ["Component", "Base", "Increase", "Decrease", "Total"])
    for j, (k_, lab) in enumerate(comps + [("closing", "Closing ARR")]):
        rr = w0 + 1 + j
        b.text(ws, f"A{rr}", lab)
        src = f"D{7 + j}" if k_ != "closing" else f"D{close_row}"
        if k_ in ("opening_arr", "closing"):
            b.fml(ws, f"B{rr}", "=0", GBP_K); b.fml(ws, f"C{rr}", "=0", GBP_K); b.fml(ws, f"D{rr}", "=0", GBP_K)
            b.fml(ws, f"E{rr}", f"={src}", GBP_K)
        else:
            running_before = f"SUM($D$7:D{6 + j})"
            b.fml(ws, f"B{rr}", f"=MIN({running_before},{running_before}+{src})", GBP_K)
            b.fml(ws, f"C{rr}", f"=MAX({src},0)", GBP_K); b.fml(ws, f"D{rr}", f"=MAX(-{src},0)", GBP_K)
            b.fml(ws, f"E{rr}", "=0", GBP_K)
    w_last = w0 + len(comps) + 1
    ch = BarChart(); ch.type = "col"; ch.grouping = "stacked"; ch.overlap = 100
    ch.add_data(Reference(ws, min_col=2, max_col=5, min_row=w0, max_row=w_last), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=w0 + 1, max_row=w_last))
    b.style_chart(ch, "ARR bridge 2025 (£'000; axis starts at £25m)", "£'000", "", GBP_K, width=22)
    # invisible base: filled with the page colour, which survives a LibreOffice re-save
    ch.series[0].graphicalProperties.solidFill = "FFFFFF"
    ch.series[0].graphicalProperties.line.solidFill = "FFFFFF"
    ch.series[1].graphicalProperties.solidFill = "2A78D6"
    ch.series[2].graphicalProperties.solidFill = "E34948"
    ch.series[3].graphicalProperties.solidFill = "8A8983"
    ch.y_axis.scaling.min = 25_000_000
    ws.add_chart(ch, "J5")
    # revenue bridge
    rb = t("4e_revenue_bridge")
    rcomps = [("net_revenue_prior", "Prior-year net revenue"), ("new_customers", "New customers"),
              ("full_year_effect_of_prior_year_additions", "Full-year effect of prior-year additions"), ("cross_sell", "Cross-sell"),
              ("upsell", "Upsell"), ("price_increase", "Price increase"), ("billing_gaps", "Billing gaps"), ("downgrade", "Downgrade"),
              ("contraction", "Contraction"), ("churn", "Churn"), ("credit_notes_change", "Change in credit notes"),
              ("signup_implementation_change", "Change in signup implementation"), ("other_implementation_change", "Change in other implementation")]
    r0 = w_last + 4
    b.section(ws, f"A{r0 - 1}", "Revenue bridge: year-on-year change in net revenue")
    b.header(ws, r0, 1, ["£'000", "2023", "2024", "2025"])
    for j, (k_, lab) in enumerate(rcomps):
        b.text(ws, f"A{r0 + 1 + j}", lab)
    nr_row = r0 + 1 + len(rcomps)
    b.text(ws, f"A{nr_row}", "Net revenue", bold=True)
    b.text(ws, f"A{nr_row + 1}", "Net revenue per 4a")
    b.text(ws, f"A{nr_row + 2}", "Check")
    b.text(ws, f"A{nr_row + 3}", "Of which recurring change")
    b.text(ws, f"A{nr_row + 4}", "Of which one-off change")
    for i, y in enumerate((2023, 2024, 2025)):
        cl = col(2 + i)
        r = rb[rb.year == y].iloc[0]
        for j, (k_, lab) in enumerate(rcomps):
            b.inp(ws, f"{cl}{r0 + 1 + j}", float(r[k_]), GBP_K)
        b.fml(ws, f"{cl}{nr_row}", f"=SUM({cl}{r0 + 1}:{cl}{nr_row - 1})", GBP_K, bold=True)
        b.fml(ws, f"{cl}{nr_row + 1}", f"=SUMIFS({q('4a Revenue quality')}!$F$7:$F$10,{q('4a Revenue quality')}!$A$7:$A$10,{y})", GBP_K)
        b.check(ws, f"{cl}{nr_row + 2}", f"=ABS({cl}{nr_row}-{cl}{nr_row + 1})<0.01", f"4e revenue bridge {y}: components add up to net revenue")
        b.fml(ws, f"{cl}{nr_row + 3}", f"=SUM({cl}{r0 + 2}:{cl}{r0 + 11})", GBP_K)
        b.fml(ws, f"{cl}{nr_row + 4}", f"=SUM({cl}{r0 + 12}:{cl}{r0 + 13})", GBP_K)
        b.mark(f"revenue_bridge_net_{y}", ws, f"{cl}{nr_row}", "4e_revenue_bridge", "net_revenue", {"year": y})
    b.commentary(ws, 26, 10, 10, 14, findings_for("4e"))


def tab_4f(b: Book):
    name = "4f Margin"
    ws = b.sheet(name, "4f. Gross margin: by product line, mix and rate, size band and discounting", "Units: £'000 unless stated",
                 "Source: outputs/tables/4f_*.csv (notebooks/04f_margins.ipynb); costs from costs.csv",
                 "Gross margin by line, mix against rate, reconciliation to management gross profit, size bands, discounts",
                 widths=[13, 13, 13, 13, 4, 13, 13, 13, 13])
    ln = t("4f_margin_by_line")
    lines = ["Core Platform", "Analytics Add-on", "Payments Module", "Implementation Services"]
    blocks = {}
    label_col = {"Revenue": "revenue", "Cost of delivery": "cost_of_delivery"}

    def grid(top, label, fmt, formula=None):
        """A product line x year grid. Inputs if formula is None, else formula(column, line_index)."""
        b.section(ws, f"A{top - 1}", label)
        b.header(ws, top, 1, ["Product line"] + [str(y) for y in YEARS])
        for k_, pl in enumerate(lines):
            i = top + 1 + k_
            b.text(ws, f"A{i}", pl)
            for j, y in enumerate(YEARS):
                cl = col(2 + j)
                if formula is None:
                    v = ln[(ln.product_line == pl) & (ln.year == y)][label_col[label]].iloc[0]
                    b.inp(ws, f"{cl}{i}", float(v), fmt)
                else:
                    b.fml(ws, f"{cl}{i}", formula(cl, k_), fmt)
        blocks[label] = (top + 1, top + len(lines))
        return top + len(lines)

    def total_row(row, block):
        b.text(ws, f"A{row}", "Total", bold=True)
        for j in range(len(YEARS)):
            cl = col(2 + j)
            b.fml(ws, f"{cl}{row}", f"=SUM({cl}{blocks[block][0]}:{cl}{blocks[block][1]})", GBP_K, bold=True)
        return row

    end = grid(6, "Revenue", GBP_K)
    rev_tot = total_row(end + 1, "Revenue")
    end = grid(rev_tot + 3, "Cost of delivery", GBP_K)
    cost_tot = total_row(end + 1, "Cost of delivery")
    R, C = blocks["Revenue"], blocks["Cost of delivery"]
    end = grid(cost_tot + 3, "Gross profit", GBP_K, lambda cl, k_: f"={cl}{R[0] + k_}-{cl}{C[0] + k_}")
    gp = blocks["Gross profit"]
    end = grid(end + 3, "Gross margin", PCT, lambda cl, k_: f"={cl}{gp[0] + k_}/{cl}{R[0] + k_}")
    gm = blocks["Gross margin"]
    end = grid(end + 3, "Revenue share", PCT, lambda cl, k_: f"={cl}{R[0] + k_}/{cl}${rev_tot}")
    sh = blocks["Revenue share"]
    s0 = end + 2
    b.section(ws, f"A{s0 - 1}", "Blended margin and its movement")
    rows = ["Blended gross profit", "Blended gross margin", "Change in blended margin (pts)", "Mix effect (pts)", "Rate effect (pts)", "Check: mix + rate = change"]
    for j, lab in enumerate(rows):
        b.text(ws, f"A{s0 + j}", lab, bold=j < 2)
    for j, y in enumerate(YEARS):
        cl, pv = col(2 + j), col(1 + j)
        b.fml(ws, f"{cl}{s0}", f"={cl}{rev_tot}-{cl}{cost_tot}", GBP_K, bold=True)
        b.fml(ws, f"{cl}{s0 + 1}", f"={cl}{s0}/{cl}{rev_tot}", PCT, bold=True)
        b.mark(f"gross_margin_{y}", ws, f"{cl}{s0 + 1}", "4f_margin_reconciliation", "gross_margin_pct", {"year": y}, 0.01, 1e-6)
        if j > 0:
            b.fml(ws, f"{cl}{s0 + 2}", f"=({cl}{s0 + 1}-{pv}{s0 + 1})*100", PTS)
            b.fml(ws, f"{cl}{s0 + 3}", f"=SUMPRODUCT({cl}{sh[0]}:{cl}{sh[1]}-{pv}{sh[0]}:{pv}{sh[1]},{pv}{gm[0]}:{pv}{gm[1]})*100", PTS)
            b.fml(ws, f"{cl}{s0 + 4}", f"=SUMPRODUCT({cl}{sh[0]}:{cl}{sh[1]},{cl}{gm[0]}:{cl}{gm[1]}-{pv}{gm[0]}:{pv}{gm[1]})*100", PTS)
            b.check(ws, f"{cl}{s0 + 5}", f"=ABS({cl}{s0 + 3}+{cl}{s0 + 4}-{cl}{s0 + 2})<0.000001", f"4f {y}: mix plus rate equals the change in blended margin")
            b.mark(f"mix_effect_{y}", ws, f"{cl}{s0 + 3}", "4f_mix_rate", "mix_effect_pts", {"year": y}, 1.0, 1e-6)
    # reconciliation to management gross profit
    mr = t("4f_margin_reconciliation")
    m0 = s0 + 8
    b.section(ws, f"A{m0 - 1}", "Reconciliation to management gross profit")
    mrows = ["Mgmt total revenue", "Mgmt cost of sales", "Mgmt gross profit", "Invoice-based gross profit", "Difference",
             "Unexplained adjustments to reported revenue (Reconciliation tab)", "Check"]
    for j, lab in enumerate(mrows):
        b.text(ws, f"A{m0 + j}", lab)
    for j, y in enumerate(YEARS):
        cl = col(2 + j); r = mr[mr.year == y].iloc[0]
        b.inp(ws, f"{cl}{m0}", float(r.mgmt_revenue), GBP_K); b.inp(ws, f"{cl}{m0 + 1}", float(r.mgmt_cost_of_sales), GBP_K)
        b.fml(ws, f"{cl}{m0 + 2}", f"={cl}{m0}-{cl}{m0 + 1}", GBP_K)
        b.fml(ws, f"{cl}{m0 + 3}", f"={cl}{s0}", GBP_K)
        b.fml(ws, f"{cl}{m0 + 4}", f"={cl}{m0 + 2}-{cl}{m0 + 3}", GBP)
        ra, rb_ = b.pos["recon_annual"]
        b.fml(ws, f"{cl}{m0 + 5}", f"=-SUMIFS({q('Reconciliation')}!$D${ra}:$D${rb_},{q('Reconciliation')}!$A${ra}:$A${rb_},{y})", GBP)
        b.check(ws, f"{cl}{m0 + 6}", f"=AND(ABS({cl}{m0 + 4}-{cl}{m0 + 5})<0.01,ABS({cl}{m0 + 1}-{cl}{cost_tot})<0.01)",
                f"4f {y}: gross profit ties to management apart from the unexplained revenue adjustments; costs tie")
    # discounts
    dy = t("4f_discount_by_year")
    d0 = m0 + 10
    b.section(ws, f"A{d0 - 1}", "Discounting: recurring billings against list-equivalent")
    b.header(ws, d0, 1, ["Year", "Recurring billings", "List-equivalent", "Revenue given up", "Discount % of list",
                         "Gross margin actual", "Gross margin at list"])
    for i, y in enumerate(YEARS, start=d0 + 1):
        r = dy[dy.year == y].iloc[0]; j = YEARS.index(y); cl = col(2 + j)
        b.inp(ws, f"A{i}", y, "0"); b.inp(ws, f"B{i}", float(r.recurring_billings), GBP_K); b.inp(ws, f"C{i}", float(r.list_equivalent), GBP_K)
        b.fml(ws, f"D{i}", f"=C{i}-B{i}", GBP_K); b.fml(ws, f"E{i}", f"=D{i}/C{i}", PCT)
        b.fml(ws, f"F{i}", f"={cl}{s0 + 1}", PCT)
        b.fml(ws, f"G{i}", f"=({cl}{rev_tot}+D{i}-{cl}{cost_tot})/({cl}{rev_tot}+D{i})", PCT)
        b.mark(f"discount_given_up_{y}", ws, f"D{i}", "4f_discount_by_year", "revenue_given_up", {"year": y})
    ds = t("4f_discount_by_size"); ds = ds[ds.year == 2025]
    z0 = d0 + 7
    b.section(ws, f"A{z0 - 1}", "Discount by size band, 2025")
    b.header(ws, z0, 1, ["Size band", "Recurring billings", "List-equivalent", "Revenue given up", "Discount % of list", "Share of revenue given up"])
    for i, r in enumerate(ds.itertuples(), start=z0 + 1):
        b.inp(ws, f"A{i}", r.company_size); b.inp(ws, f"B{i}", float(r.recurring_billings), GBP_K); b.inp(ws, f"C{i}", float(r.list_equivalent), GBP_K)
        b.fml(ws, f"D{i}", f"=C{i}-B{i}", GBP_K); b.fml(ws, f"E{i}", f"=D{i}/C{i}", PCT)
        b.fml(ws, f"F{i}", f"=D{i}/SUM($D${z0 + 1}:$D${z0 + len(ds)})", PCT)
    zt = z0 + len(ds) + 1
    b.text(ws, f"A{zt}", "Total", bold=True)
    for cl in "BCD":
        b.fml(ws, f"{cl}{zt}", f"=SUM({cl}{z0 + 1}:{cl}{zt - 1})", GBP_K, bold=True)
    b.check(ws, f"E{zt}", f"=ABS(D{zt}-D{d0 + 4})<0.01", "4f 2025: discount by size band adds up to the annual total")
    # size-band margin
    sb = t("4f_margin_by_size"); sb = sb[sb.year == 2025]
    y0 = zt + 3
    b.section(ws, f"A{y0 - 1}", "Margin by size band, 2025 (basis A: cost pro rata to revenue; basis B: cost per active customer line)")
    b.header(ws, y0, 1, ["Size band", "Net revenue", "Cost basis A", "Cost basis B", "Margin basis A", "Margin basis B", "Customers"])
    for i, r in enumerate(sb.itertuples(), start=y0 + 1):
        b.inp(ws, f"A{i}", r.company_size); b.inp(ws, f"B{i}", float(r.revenue), GBP_K); b.inp(ws, f"C{i}", float(r.cost_basis_a), GBP_K)
        b.inp(ws, f"D{i}", float(r.cost_basis_b), GBP_K); b.fml(ws, f"E{i}", f"=(B{i}-C{i})/B{i}", PCT); b.fml(ws, f"F{i}", f"=(B{i}-D{i})/B{i}", PCT)
        b.inp(ws, f"G{i}", int(r.customers), INT)
    yt = y0 + len(sb) + 1
    b.text(ws, f"A{yt}", "Total", bold=True)
    for cl in "BC":
        b.fml(ws, f"{cl}{yt}", f"=SUM({cl}{y0 + 1}:{cl}{yt - 1})", GBP_K, bold=True)
    # each allocated cost is rounded to the penny, so four of them can differ from the total by a few pence
    b.check(ws, f"D{yt}", f"=AND(ABS(B{yt}-E{rev_tot})<0.05,ABS(C{yt}-E{cost_tot})<0.05)", "4f 2025: size-band revenue and allocated cost add back to the totals (within 5p of rounding)")
    ch = LineChart()
    ch.add_data(Reference(ws, min_col=1, max_col=5, min_row=gm[0], max_row=gm[1]), from_rows=True, titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=2, max_col=5, min_row=gm[0] - 1))
    b.style_chart(ch, "Gross margin by product line", "Gross margin", "Year", "0%")
    ws.add_chart(ch, "K5")
    b.commentary(ws, 24, 11, 9, 14, findings_for("4f"))


def tab_4g(b: Book):
    name = "4g Segments"
    ws = b.sheet(name, "4g. Segment cuts: revenue, growth, logo churn and NRR (2025)", "Units: £'000 unless stated",
                 "Source: outputs/tables/4g_segments.csv (notebooks/04g_segments.ipynb). Logo churn and NRR are annual (December 2024 to December 2025), not tenure-matched",
                 "Revenue, growth, logo churn, NRR and GRR by industry, region, channel and size, with sample sizes",
                 widths=[24, 12, 10, 12, 12, 12, 12, 12, 10, 10, 10, 10, 20])
    sg = t("4g_segments")
    b.section(ws, "A5", "Segments (flag: risk if logo churn is 5 points above the company rate or NRR 5 points below; small if fewer than 30 customers)")
    hdr = ["Segment", "Dimension", "Customers Dec 2024", "Churned in 2025", "Opening MRR", "Closing MRR", "Closing MRR capped",
           "Net revenue 2024", "Net revenue 2025", "Growth", "Logo churn", "NRR", "GRR", "Flag"]
    b.header(ws, 6, 1, hdr)
    first = 7
    last = first + len(sg) - 1
    comp = last + 2
    for i, r in enumerate(sg.itertuples(), start=first):
        b.inp(ws, f"A{i}", r.segment); b.inp(ws, f"B{i}", r.dimension)
        b.inp(ws, f"C{i}", int(r.customers_active_dec_2024), INT); b.inp(ws, f"D{i}", int(r.churned_2025), INT)
        b.inp(ws, f"E{i}", float(r.opening_mrr), GBP_K); b.inp(ws, f"F{i}", float(r.closing_mrr), GBP_K)
        b.inp(ws, f"G{i}", float(r.closing_mrr_capped), GBP_K)
        b.inp(ws, f"H{i}", float(r.net_revenue_2024), GBP_K); b.inp(ws, f"I{i}", float(r.net_revenue_2025), GBP_K)
        b.fml(ws, f"J{i}", f"=I{i}/H{i}-1", PCT); b.fml(ws, f"K{i}", f"=D{i}/C{i}", PCT)
        b.fml(ws, f"L{i}", f"=F{i}/E{i}", PCT); b.fml(ws, f"M{i}", f"=G{i}/E{i}", PCT)
        b.fml(ws, f"N{i}", f'=IF(C{i}<30,"too small to conclude",IF(OR(K{i}>$K${comp}+0.05,L{i}<$L${comp}-0.05),"risk",'
                            f'IF(OR(K{i}<$K${comp}-0.05,L{i}>$L${comp}+0.05),"strength","none")))')
        b.mark(f"nrr_2025_{r.dimension}_{r.segment}", ws, f"L{i}", "4g_segments", "nrr_2025_pct", {"dimension": r.dimension, "segment": r.segment}, 0.01, 1e-6)
    ws.freeze_panes = "C7"
    b.text(ws, f"A{comp}", "Company (sum of the industry rows)", bold=True)
    for cl in "CDEFGHI":
        b.fml(ws, f"{cl}{comp}", f'=SUMIFS({cl}${first}:{cl}${last},$B${first}:$B${last},"industry")', GBP_K if cl in "EFGHI" else INT, bold=True)
    b.fml(ws, f"J{comp}", f"=I{comp}/H{comp}-1", PCT, bold=True); b.fml(ws, f"K{comp}", f"=D{comp}/C{comp}", PCT, bold=True)
    b.fml(ws, f"L{comp}", f"=F{comp}/E{comp}", PCT, bold=True); b.fml(ws, f"M{comp}", f"=G{comp}/E{comp}", PCT, bold=True)
    for j, dim in enumerate(["region_group", "acquisition_channel", "company_size"]):
        r = comp + 1 + j
        b.text(ws, f"A{r}", f"Check: {dim} rows add up to the company total")
        b.check(ws, f"C{r}", f'=AND(SUMIFS(C${first}:C${last},$B${first}:$B${last},"{dim}")=C{comp},ABS(SUMIFS(I${first}:I${last},$B${first}:$B${last},"{dim}")-I{comp})<0.01)',
                f"4g: {dim} segments add up to the company totals")
    r = comp + 4
    b.text(ws, f"A{r}", "Check: company 2025 revenue equals the 4a tab")
    b.check(ws, f"C{r}", f"=ABS(I{comp}-{q('4a Revenue quality')}!F10)<0.01", "4g: company 2025 revenue ties to 4a")
    ch = BarChart(); ch.type = "bar"
    ch_rows = [i for i, rr in enumerate(sg.itertuples(), start=first) if rr.dimension == "acquisition_channel"]
    ch.add_data(Reference(ws, min_col=11, min_row=ch_rows[0], max_row=ch_rows[-1]), titles_from_data=False)
    ch.set_categories(Reference(ws, min_col=1, min_row=ch_rows[0], max_row=ch_rows[-1]))
    b.style_chart(ch, "2025 logo churn by acquisition channel", "Logo churn", "", "0%")
    ch.legend = None
    ws.add_chart(ch, "P5")
    b.commentary(ws, 24, 16, 9, 12, findings_for("4g"))


def qa(b: Book):
    ws = b.sheet("Q&A log", "Questions for management", "One row per question", "Source: docs/qa_log.md (qa_log table)",
                 "Questions for management raised by Steps 2 to 4", widths=[10, 10, 26, 70, 70, 10])
    ws.column_dimensions["A"].width = 8
    d = t("qa_log")
    b.header(ws, 5, 1, ["ID", "Step", "Ref", "Topic", "Question", "Evidence", "Status"])
    ws.column_dimensions["D"].width = 24; ws.column_dimensions["E"].width = 70; ws.column_dimensions["F"].width = 70
    for i, r in enumerate(d.itertuples(), start=6):
        for j, v in enumerate([r.qa_id, r.step, r.issue_ref, r.topic, r.question, r.evidence, r.status]):
            c = b.inp(ws, f"{col(1 + j)}{i}", v)
            c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[i].height = 75
    ws.freeze_panes = "A6"


def checks(b: Book):
    ws = b.sheet("Checks", "Checks: every tie-out in the databook", "TRUE means the check passes",
                 "Each row links to a check cell on another tab", "Every tie-out as a TRUE/FALSE formula, and one overall check",
                 widths=[60, 22, 10, 10])
    ws.column_dimensions["A"].width = 6
    ws.column_dimensions["B"].width = 95
    b.text(ws, "A5", "Overall check", bold=True)
    b.header(ws, 7, 1, ["#", "Check", "Tab", "Cell", "Result"])
    first = 8
    for i, (desc, sheet, ref) in enumerate(b.checks, start=first):
        b.text(ws, f"A{i}", i - first + 1); b.text(ws, f"B{i}", desc); b.text(ws, f"C{i}", sheet); b.text(ws, f"D{i}", ref)
        b.fml(ws, f"E{i}", f"={q(sheet)}!{ref}")
    last = first + len(b.checks) - 1
    c = b.fml(ws, "C5", f"=AND(E{first}:E{last})", bold=True)
    b.cells["overall_check"] = {"sheet": "Checks", "cell": "C5"}
    ws.column_dimensions["C"].width = 22
    ws.freeze_panes = "A8"


def build() -> Path:
    b = Book()
    cover(b)
    # Built in dependency order (Basis reads positions on Reconciliation); sheets are
    # put in reading order afterwards.
    reconciliation(b)
    tab_4a(b)
    tab_4b(b)
    tab_4c(b)
    tab_4d(b)
    tab_4e(b)
    tab_4f(b)
    tab_4g(b)
    basis(b)
    qa(b)
    order = ["Cover", "Basis", "Reconciliation", "4a Revenue quality", "4b Concentration", "4c Cohorts", "4d NRR GRR",
             "4e ARR bridge", "4f Margin", "4g Segments", "Q&A log"]
    b.tabs.sort(key=lambda x: order.index(x[0]))
    checks(b)
    contents(b)
    order = ["Cover", "Contents"] + order[1:] + ["Checks"]
    b.wb._sheets = [b.wb[n] for n in order]
    b.wb.properties.creator = "Northbridge pipeline (databook/build_databook.py)"
    stamp = dt.datetime.fromisoformat(CONFIG["document_date"])
    b.wb.properties.created = stamp
    b.wb.properties.modified = stamp
    OUT.parent.mkdir(exist_ok=True)
    b.wb.save(OUT)
    CELL_MAP.write_text(json.dumps(b.cells, indent=2), encoding="utf-8")
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"built {path.relative_to(ROOT)}")
    sys.path.insert(0, str(Path(__file__).parent))
    from recalc import recalc

    result = recalc(str(path))
    # LibreOffice stamps the save time and new random chart axis ids; fix them so a rerun
    # with the same numbers gives the same bytes.
    sys.path.insert(0, str(ROOT / "tools"))
    from normalise_ooxml import normalise

    normalise(path)
    (ROOT / "databook" / "recalc_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "errors"}, indent=2))
    if "error" in result or result.get("status") != "success":
        print(json.dumps(result, indent=2))
        sys.exit(1)
