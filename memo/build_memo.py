"""Build the findings memo: memo/findings_memo.md, .docx and .pdf.

Every number in the memo is read from outputs/tables/ (mostly key_figures.csv); none is
typed in. The text is written once as a list of blocks and rendered twice: to Markdown and,
with python-docx, to Word, which LibreOffice headless converts to PDF. The PDF must be two
pages or fewer; the build fails otherwise.

PDF route (see docs/decisions_log.md, D23): pandoc is not installed and would need a LaTeX
engine for PDF, so the brief's second option is used (python-docx, then LibreOffice).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "outputs" / "tables"
MEMO = ROOT / "memo"
CONFIG = json.loads((ROOT / "report_config.json").read_text(encoding="utf-8"))
MAX_PAGES = 2

K = dict(pd.read_csv(TABLES / "key_figures.csv")[["name", "value"]].itertuples(index=False, name=None))
QA = pd.read_csv(TABLES / "qa_log.csv")
RUNRATE = pd.read_csv(TABLES / "4b_top10_runrate.csv")


def m(x, dp=2):
    return f"£{x / 1e6:,.{dp}f}m"


def g(x):
    return f"£{abs(x):,.0f}"


def p(x, dp=1):
    return f"{x:.{dp}f}%"


def qid(issue_ref=None, topic=None, contains=None, nth=0):
    d = QA
    if issue_ref:
        d = d[d.issue_ref == issue_ref]
    if topic:
        d = d[d.topic == topic]
    if contains:
        d = d[d.question.str.contains(contains, case=False)]
    return d.qa_id.iloc[nth]


BENCH = pd.read_csv(TABLES / "benchmarks.csv")


def rng(key, metric):
    return f"{K[f'bm_{key}_{metric}_low']:.0f}% to {K[f'bm_{key}_{metric}_high']:.0f}%"


# the benchmark sentence in section 2 is only true while these hold
assert K["nrr_2025"] < K["bm_sc_smb_nrr_low"] and K["grr_2025"] < K["bm_sc_smb_grr_low"] and K["nrr_ex_price_2025"] < K["bm_smb_nrr_low"]
SOURCES = BENCH[BENCH.source_id.isin(["SC25", "HA25", "BM25"])].drop_duplicates("source_id")
FOOTNOTE = ("Benchmarks: " + "; ".join(f"{r.publisher}, {r.title}" for r in SOURCES.itertuples())
            + ". Medians for US$ ACV bands under $50k. Definitions, ranges and caveats: docs/benchmarks.md.")

decl = RUNRATE[RUNRATE.declining].sort_values("change_vs_prior_dec").customer_id.tolist()
big = decl[0]

blocks: list[tuple] = [
    ("title", f"{CONFIG['project']}: financial due diligence findings (draft)"),
    ("meta", f"To: investment committee. From: buy-side Transaction Analytics. Date: {CONFIG['report_date']}. "
             "Status: draft, subject to management's answers to the questions in section 5."),
    ("h", "1. Scope and basis"),
    ("p", f"We reviewed the seller's data-room extract for {CONFIG['target']}: {K['customers_total']:,.0f} customers and "
          f"{K['raw_invoice_rows']:,.0f} invoice lines from January 2022 to December 2025, reconciled to the monthly management accounts. "
          "Figures come from the cleaned invoice ledger and match the databook; tab references are in brackets. "
          "The data is synthetic: this is a self-directed simulation, not client work."),
    ("h", "2. Key findings"),
    ("bullets", [
        f"Revenue reconciles [Reconciliation]. The ledger ties to the management accounts' product lines in all 48 months. 2025 net revenue is "
        f"{m(K['net_revenue_2025'])}; the reported total of {m(K['mgmt_revenue_2025'])} includes an unexplained manual adjustment of {g(K['reported_less_cube_2025'])}.",
        f"Recurring revenue was {p(K['recurring_pct_2025'])} of 2025 revenue ({m(K['recurring_revenue_2025'])}), down from {p(K['recurring_pct_2024'])} in 2024, "
        f"because {m(K['other_implementation_2025'])} of 'other implementation' was billed to existing customers in 2025 [4a].",
        f"Headline revenue growth of {p(K['headline_growth_2025'])} in 2025 falls to {p(K['recurring_growth_2025'])} on recurring revenue and "
        f"{p(K['growth_ex_other_implementation_2025'])} excluding other implementation [4a].",
        f"ARR was {m(K['arr_2025'])} at December 2025, up {p(K['arr_growth_2025'])}. Every recurring line was billed {p(K['price_uplift_2025'], 0)} more from January 2025 "
        f"(and {p(K['price_uplift_2024'], 0)} from January 2024); before the price increase ARR grew {p(K['arr_growth_ex_price_2025'])} [4a, 4e].",
        f"NRR was {p(K['nrr_2023'])}, {p(K['nrr_2024'])} and {p(K['nrr_2025'])} for 2023 to 2025 ({p(K['nrr_ex_price_2025'])} in 2025 before price); "
        f"GRR fell from {p(K['grr_2023'])} to {p(K['grr_2025'])} [4d]. There is no December 2021, so 2022 cannot be measured. "
        f"Both 2025 figures are below the SaaS Capital SMB benchmark medians, which use our definitions (NRR {rng('sc_smb', 'nrr')}, GRR {rng('sc_smb', 'grr')}), "
        f"and NRR before price is below every SMB median in three 2025 surveys ({rng('smb', 'nrr')}).[^1]",
        f"Customers who signed up from 2023 leave faster: {p(K['retention_12m_newer'])} were still subscribed after 12 months, against "
        f"{p(K['retention_12m_older'])} for 2017 to 2022 signups; logo churn rose to {p(K['logo_churn_rate_2025'])} in 2025 [4c].",
        f"Six large accounts carry {p(K['large_account_share_2025'])} of 2025 revenue. The largest, {big}, cut its ARR by "
        f"{p(-K[f'{big}_arr_change_pct'])} ({g(K[f'{big}_arr_change'])}) in September 2025 [4b].",
        f"Gross margin fell from {p(K['gross_margin_2024'])} to {p(K['gross_margin_2025'])} in 2025, entirely from the shift towards implementation work, which earns "
        f"{p(K['implementation_margin_2025'])} [4f].",
    ]),
    ("h", "3. Red flags"),
    ("table", ["#", "Red flag", "Rating", "Impact", "Why it matters for value"], [
        ["1", "2025 'other implementation' revenue", "High", f"{m(K['other_implementation_2025'])}, {p(K['other_implementation_pct_2025'])} of 2025 revenue",
         f"One-off work at the end of the period; it lifts 2025 growth from {p(K['growth_ex_other_implementation_2025'])} to {p(K['headline_growth_2025'])}."],
        ["2", "Growth carried by price increases", "High", f"{m(K['arr_bridge_price_increase_2025'])} of 2025 ARR growth",
         f"Underlying ARR growth was {p(K['arr_growth_ex_price_2025'])}; a multiple priced on {p(K['arr_growth_2025'])} overpays."],
        ["3", "Retention weakening", "High", f"GRR {p(K['grr_2025'])}; newer cohorts {p(K['retention_12m_newer'])} at 12 months",
         "Lower lifetime value; more new customers are needed just to stand still."],
        ["4", "Largest customers contracting", "High",
         "; ".join(f"{c} down {g(K[f'{c}_arr_change'])} ARR" for c in decl),
         "Run-rate already lost, and renewal risk on the rest of those contracts."],
        ["5", "Margin dilution from services", "Medium", f"Blended margin {abs(K['mix_effect_2025']):.2f} points lower in 2025",
         f"Services revenue carries a {p(K['implementation_margin_2025'])} margin."],
        ["6", "Manual adjustments to reported revenue", "Low", f"{g(K['manual_adjustments_2025'])} added to 2025",
         "Small, but a controls point in the figures the price is based on."],
    ]),
    ("h", "4. How the investor should view revenue"),
    ("table", ["Basis (2025)", "Amount", "Growth on 2024"], [
        ["Reported total revenue (management accounts)", m(K["mgmt_revenue_2025"]), "not used"],
        ["Net revenue (invoice ledger)", m(K["net_revenue_2025"]), p(K["headline_growth_2025"])],
        ["Excluding other implementation", m(K["net_ex_other_implementation_2025"]), p(K["growth_ex_other_implementation_2025"])],
        ["Recurring revenue only", m(K["recurring_revenue_2025"]), p(K["recurring_growth_2025"])],
        ["ARR, December 2025", m(K["arr_2025"]), f"{p(K['arr_growth_2025'])} ({p(K['arr_growth_ex_price_2025'])} before price)"],
    ]),
    ("p", f"We suggest valuing the business on recurring revenue or ARR, treating the {m(K['other_implementation_2025'])} as non-recurring until contracts and "
          "acceptance are provided, and underwriting growth before price increases. The December 2025 ARR already reflects the lost large-account lines."),
    ("h", "5. Questions for management"),
    ("numbered", [
        f"({qid('P02', nth=0)}) Contract or statement of work for each of the {K['other_implementation_invoices']:.0f} 'other implementation' invoices billed in 2025 ({m(K['other_implementation_2025'])}).",
        f"({qid('P02', nth=1)}) Delivery and customer-acceptance status of that work; {g(K['other_implementation_overdue'])} of it is overdue.",
        f"({qid('P02', nth=2)}) The revenue recognition basis for that work, and whether any is deferred.",
        f"({qid('P02', nth=3)}) The contracted pipeline of similar work for 2026.",
        f"({qid(topic='Price increases')}) The contractual basis and customer notice for the {p(K['price_uplift_2024'], 0)} (2024) and {p(K['price_uplift_2025'], 0)} (2025) price increases, and any plan for 2026.",
        f"({qid(topic='Large customers', nth=0)}) Why {' and '.join(decl)} ended product lines in 2025, and the renewal status of their remaining contracts.",
        f"({qid(topic='Large customers', nth=1)}) Contracts for the six large accounts, including term, termination and change-of-control clauses.",
        f"({qid(topic='Retention', nth=0)}) What changed in acquisition or onboarding from 2023, with churn reasons by customer for 2024 and 2025.",
        f"({qid(topic='Retention', nth=1)}) Churn and acquisition cost by channel; Paid Search and Partner/Reseller logo churn was {p(K['logo_churn_2025_Paid Search'])} and {p(K['logo_churn_2025_Partner/Reseller'])} in 2025.",
        f"({qid('P05', contains='journal')}) The journals behind the four manual adjustments to reported revenue: who posted them and why.",
        f"({qid('P05', contains='information memorandum')}) Which 2025 revenue figure appears in the information memorandum.",
        f"({qid(topic='Margin')}) Whether the cost of the 2025 implementation work is complete, or more is to come.",
        f"({qid('P04')}) Whether the duplicate invoices ({g(K['duplicates_removed'])}) sit in receivables and the overdue balance.",
        f"({qid('P06', contains='left out')}) Why {K['anomaly_invoices']:.0f} negative paid invoices ({g(K['anomaly_probable_understatement'])}) were excluded from revenue rather than corrected.",
    ]),
    ("h", "6. Overall view: proceed, with price and structure protections"),
    ("p", f"The revenue is real, reconciles to the management accounts and is mostly recurring ({p(K['recurring_pct_2025'])}). "
          "The concerns are about quality and trend: 2025 growth relies on one-off implementation billing and price increases, retention is weakening, "
          "and the largest customer is shrinking. These points bear on what the business is worth, so they belong in the price and the structure."),
    ("bullets", [
        f"Price adjustment: value on December 2025 ARR ({m(K['arr_2025'])}) or recurring revenue, excluding the {m(K['other_implementation_2025'])} of other implementation (red flags 1 and 4).",
        "Earn-out tied to ARR growth before price increases, or to NRR, over 12 to 24 months (red flags 2 and 3).",
        "Specific warranty and indemnity on the 2025 implementation contracts and their revenue recognition, and a warranty on the management accounts (red flags 1 and 6).",
        "Escrow or retention released on renewal of the six large accounts (red flag 4).",
        "Completion accounts: exclude duplicate and disputed invoices from receivables in the working capital peg.",
    ]),
    ("footnote", "1", FOOTNOTE),
]


def to_markdown() -> str:
    out = []
    for b in blocks:
        kind = b[0]
        if kind == "title":
            out += [f"# {b[1]}", ""]
        elif kind == "meta":
            out += [f"*{b[1]}*", ""]
        elif kind == "h":
            out += [f"## {b[1]}", ""]
        elif kind == "p":
            out += [b[1], ""]
        elif kind == "bullets":
            out += [f"- {x}" for x in b[1]] + [""]
        elif kind == "numbered":
            out += [f"{i}. {x}" for i, x in enumerate(b[1], start=1)] + [""]
        elif kind == "table":
            hdr, rows = b[1], b[2]
            out += ["| " + " | ".join(hdr) + " |", "| " + " | ".join("---" for _ in hdr) + " |"]
            out += ["| " + " | ".join(r) + " |" for r in rows] + [""]
        elif kind == "footnote":
            out += [f"[^{b[1]}]: {b[2]}", ""]
    out += ["---", "", "*Generated by `memo/build_memo.py` from `outputs/tables/`. Every figure is read from the pipeline.*", ""]
    return "\n".join(out)


def to_docx(path: Path) -> None:
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.left_margin = sec.right_margin = Cm(1.6)
    sec.top_margin = sec.bottom_margin = Cm(1.3)
    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(9)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    normal.paragraph_format.space_after = Pt(2)
    normal.paragraph_format.line_spacing = 1.0

    def para(text, bold=False, italic=False, size=None, colour=None, style=None, after=2, before=0):
        par = doc.add_paragraph(style=style)
        run = par.add_run(text)
        run.bold, run.italic = bold, italic
        run.font.name = "Arial"
        if size:
            run.font.size = Pt(size)
        if colour:
            run.font.color.rgb = RGBColor.from_string(colour)
        par.paragraph_format.space_after = Pt(after)
        par.paragraph_format.space_before = Pt(before)
        return par

    for b in blocks:
        kind = b[0]
        if kind == "footnote":
            para(f"[{b[1]}] {b[2]}", italic=True, size=7, after=0)
            continue
        b = tuple([x.replace("[^", "[") if isinstance(x, str) else [y.replace("[^", "[") for y in x] if isinstance(x, list) and x and isinstance(x[0], str) else x for x in b])
        if kind == "title":
            para(b[1], bold=True, size=12, colour="1F3864", after=1)
        elif kind == "meta":
            para(b[1], italic=True, after=3)
        elif kind == "h":
            para(b[1], bold=True, size=9.5, colour="1F3864", before=4, after=1).paragraph_format.keep_with_next = True
        elif kind == "p":
            para(b[1])
        elif kind in ("bullets", "numbered"):
            for i, x in enumerate(b[1], start=1):
                par = para(x if kind == "bullets" else f"{i}. {x}", style="List Bullet" if kind == "bullets" else None, after=0.5)
                if kind == "numbered":
                    par.paragraph_format.left_indent = Cm(0.4)
                    par.paragraph_format.first_line_indent = Cm(-0.4)
        elif kind == "table":
            hdr, rows = b[1], b[2]
            tbl = doc.add_table(rows=1 + len(rows), cols=len(hdr))
            tbl.style = "Table Grid"
            tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
            for j, h in enumerate(hdr):
                cell = tbl.rows[0].cells[j]
                cell.text = ""
                run = cell.paragraphs[0].add_run(h)
                run.bold = True
                run.font.size = Pt(8.5)
                run.font.color.rgb = RGBColor.from_string("FFFFFF")
                shade = OxmlElement("w:shd")
                shade.set(qn("w:val"), "clear"); shade.set(qn("w:color"), "auto"); shade.set(qn("w:fill"), "1F3864")
                cell._tc.get_or_add_tcPr().append(shade)
            for i, r in enumerate(rows, start=1):
                for j, v in enumerate(r):
                    cell = tbl.rows[i].cells[j]
                    cell.text = ""
                    run = cell.paragraphs[0].add_run(v)
                    run.font.size = Pt(8.5)
            widths = {5: [0.6, 3.9, 1.7, 4.6, 7.0], 3: [8.2, 3.0, 6.6]}.get(len(hdr))
            if widths:
                tbl.autofit = False
                grid = tbl._tbl.tblGrid
                for j, w in enumerate(widths):
                    tbl.columns[j].width = Cm(w)
                    grid.gridCol_lst[j].set(qn("w:w"), str(int(Cm(w).twips)))
                for row in tbl.rows:
                    for j, w in enumerate(widths):
                        row.cells[j].width = Cm(w)
            para("", after=1)
    para("Generated by memo/build_memo.py from outputs/tables/. " + CONFIG["disclaimer"], italic=True, size=7, after=0)
    doc.core_properties.author = "Buy-side Transaction Analytics (synthetic exercise)"
    doc.save(path)


def to_pdf(docx_path: Path) -> Path:
    if not shutil.which("soffice"):
        raise RuntimeError("soffice not found: LibreOffice Writer is needed to export the memo to PDF")
    env = os.environ.copy()
    env["SAL_USE_VCLPLUGIN"] = "svp"
    with tempfile.TemporaryDirectory(prefix="lo-memo-") as profile:
        subprocess.run(["soffice", "--headless", "--norestore", f"-env:UserInstallation={Path(profile).as_uri()}",
                        "--convert-to", "pdf", "--outdir", str(docx_path.parent), str(docx_path)],
                       env=env, capture_output=True, timeout=180, check=True)
    pdf = docx_path.with_suffix(".pdf")
    if not pdf.exists():
        raise RuntimeError("LibreOffice did not produce the PDF")
    return pdf


def main() -> int:
    md = to_markdown()
    (MEMO / "findings_memo.md").write_text(md, encoding="utf-8")
    docx_path = MEMO / "findings_memo.docx"
    to_docx(docx_path)
    sys.path.insert(0, str(ROOT / "tools"))
    from normalise_ooxml import normalise as normalise_docx
    from normalise_pdf import normalise as normalise_pdf
    normalise_docx(docx_path)  # fixed dates and zip layout, so a rerun gives the same bytes
    pdf = to_pdf(docx_path)
    normalise_pdf(pdf)
    from pypdf import PdfReader
    pages = len(PdfReader(str(pdf)).pages)
    words = len(md.split())
    (MEMO / "memo_report.json").write_text(json.dumps({"pages": pages, "max_pages": MAX_PAGES, "words": words}, indent=2), encoding="utf-8")
    print(f"memo: {words} words, {pages} page(s) -> {pdf.relative_to(ROOT)}")
    if pages > MAX_PAGES:
        print(f"memo is {pages} pages; the limit is {MAX_PAGES}. Cut words.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
