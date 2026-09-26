"""Write README.md, docs/cv_bullets.md and docs/interview_prep.md from the pipeline.

Every figure is read from outputs/tables/ (mostly key_figures.csv), so the portfolio text
cannot drift from the analysis. The tests check every £ and % in these files against
outputs/tables/.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TABLES = ROOT / "outputs" / "tables"
CONFIG = json.loads((ROOT / "report_config.json").read_text(encoding="utf-8"))
K = dict(pd.read_csv(TABLES / "key_figures.csv")[["name", "value"]].itertuples(index=False, name=None))
QA = pd.read_csv(TABLES / "qa_log.csv")
RUN = pd.read_csv(TABLES / "4b_top10_runrate.csv")
BIG = RUN[RUN.declining].sort_values("change_vs_prior_dec").customer_id.iloc[0]


def m(x, dp=2):
    return f"£{x / 1e6:,.{dp}f}m"


def g(x):
    return f"£{abs(x):,.0f}"


def p(x, dp=1):
    return f"{x:.{dp}f}%"


def readme() -> str:
    return f"""# Northbridge Software Ltd: buy-side financial due diligence

A self-directed simulation of the Transaction Analytics work on a buy-side deal, run on **synthetic data** for a fictional UK B2B SaaS company. It is not client work and uses no real company's data.

**Scenario.** A private equity fund is considering buying Northbridge Software Ltd (about {m(K['net_revenue_2025'], 1)} revenue in 2025). The seller's data room holds six tables: customers, products, subscriptions, {K['raw_invoice_rows']:,.0f} invoice lines, costs and monthly management accounts for January 2022 to December 2025.

**Method.** Profile and clean the data in SQL (DuckDB), logging every adjustment. Reconcile the invoice ledger to the management accounts month by month. Analyse revenue quality, concentration, cohorts, NRR and GRR, ARR and revenue bridges, margin and segments in Python notebooks. Present the results in an Excel databook with live formulas and TRUE/FALSE checks, a Power BI build plan with DAX and expected values, and a two-page memo. One command rebuilds everything, and pytest tie-outs check each step.

**Headline findings** (details in [`memo/findings_memo.pdf`](memo/findings_memo.pdf)):

- The ledger ties to the management accounts' product lines in all 48 months; reported 2025 revenue carries an unexplained {g(K['reported_less_cube_2025'])} manual adjustment.
- 2025 revenue grew {p(K['headline_growth_2025'])}, but {p(K['recurring_growth_2025'])} on recurring revenue: {m(K['other_implementation_2025'])} of one-off implementation work was billed to existing customers in 2025.
- ARR reached {m(K['arr_2025'])} at December 2025, up {p(K['arr_growth_2025'])}; before a {p(K['price_uplift_2025'], 0)} price increase on every line it grew {p(K['arr_growth_ex_price_2025'])}.
- NRR was {p(K['nrr_2025'])} in 2025 ({p(K['nrr_ex_price_2025'])} before price) and GRR {p(K['grr_2025'])}; customers who joined from 2023 keep {p(K['retention_12m_newer'])} after 12 months against {p(K['retention_12m_older'])} before.
- The largest customer cut its ARR by {p(-K[f'{BIG}_arr_change_pct'])} in September 2025. Recommendation: proceed, with price and structure protections.

![Net revenue by type](outputs/charts/4a_revenue_mix.png)
![ARR bridge](outputs/charts/4e_arr_bridge.png)
![Retention at the same tenure](outputs/charts/4c_tenure_matched.png)

**Repository.**

```
data/generator/   seeded generator for the data room (data/raw/ is rebuilt, not committed)
sql/              00_load, 01_profile, 02_clean, 03_revenue_cube, 04_reconciliation; analysis/ queries
notebooks/        02 preparation, 03 reconciliation, 04a-04g analyses, 04h key findings
outputs/          tables/ (feed the databook), charts/, key_findings.md
databook/         build_databook.py and Northbridge_Databook.xlsx
dashboard/        Power BI build plan, measures.dax, expected_values.csv
memo/             findings memo (md, docx, pdf)
docs/             data profile, cleaning log, data dictionary, metric definitions, Q&A log, decisions log
tests/            pytest tie-outs
```

**Reproduce.** `pip install -r requirements.txt`, install LibreOffice Calc and Writer (for example `apt-get install libreoffice-calc libreoffice-writer`), then `python run_all.py`. It takes about a minute.

**Tools.** Python (pandas, numpy, matplotlib, openpyxl, python-docx), SQL (DuckDB), Jupyter, pytest, LibreOffice, Power BI (DAX).
"""


def cv_bullets() -> str:
    return f"""# CV bullets

Self-directed project on synthetic data. Keep the word "simulated" or "synthetic" in whichever version you use.

- Built a simulated buy-side financial due diligence on a synthetic UK SaaS company: profiled, cleaned and reconciled a six-table data room ({K['raw_invoice_rows']:,.0f} invoice lines, {K['customers_total']:,.0f} customers, 48 months) to the management accounts in SQL (DuckDB), logging every adjustment and tying revenue to the reported product lines in every month.
- Analysed revenue quality, customer concentration, tenure-matched cohorts, NRR and GRR, ARR and revenue bridges, margin and segments in Python, and found that {p(K['headline_growth_2025'])} headline growth fell to {p(K['recurring_growth_2025'])} on recurring revenue and that ARR growth was {p(K['arr_growth_ex_price_2025'])} before price increases.
- Delivered an Excel databook with live formulas and automated tie-out checks, a Power BI build plan (star schema, DAX, expected values) and a two-page investment memo with rated red flags and deal protections; the whole pipeline rebuilds from one command with pytest checks.
"""


def interview_prep() -> str:
    q_other = QA[QA.issue_ref == "P02"].qa_id.iloc[0]
    return f"""# Interview prep

Five questions I am most likely to be asked about this project, with answers to say out loud (about 60 to 90 seconds each) and two follow-ups each. Every figure is from the pipeline. The project is a self-directed simulation on synthetic data.

## 1. How did you reconcile the data, and what did you do with differences you couldn't explain?

I rebuilt revenue from the invoice ledger, customer by product by month, and compared it with the management accounts every month, at total and at product-line level. Before that I cleaned out {K['duplicate_rows']:.0f} exact duplicate invoices worth {g(K['duplicates_removed'])}. There were also {K['anomaly_invoices']:.0f} negative amounts on invoices marked paid, and I tested three treatments for those against the management accounts. Only excluding them tied every month, so management had left them out. With that, the ledger tied to the product lines in all 48 months. The reported total still differed in four months, by round amounts: reported 2025 revenue was {g(K['manual_adjustments_2025'])} higher than the invoices support. I couldn't explain those from the data, so I labelled them unexplained, quantified them by year, and put specific questions in the Q&A log: the journals, who posted them, and which figure is in the information memorandum. I flagged any month with a difference above {g(K['materiality_flag_gbp'])} and treated anything above {p(K['materiality_monthly_pct'])} of a month's revenue as material.

- *Why not just adjust the total to match the lines?* Because that would be me deciding which number is right without evidence. The cube is unaffected either way; the question goes to management.
- *How would the other side's adviser attack this?* They'd say the differences are immaterial. They are, at under {p(K['materiality_annual_pct'])} of any year. But manual entries to reported revenue are a controls point, and the buyer should know which figure it is paying on.

## 2. How did you define NRR and GRR, and what are their limits here?

NRR is December MRR from the customers who were active the previous December, divided by their MRR that previous December. Churned customers count at zero and new customers are left out. GRR is the same, but each customer's closing MRR is capped at its opening MRR, so it shows only losses. MRR is recurring billings before credit notes, because credit notes are one-off concessions and would make a customer look as if it had churned. NRR was {p(K['nrr_2023'])}, {p(K['nrr_2024'])} and {p(K['nrr_2025'])} for 2023 to 2025, and GRR fell from {p(K['grr_2023'])} to {p(K['grr_2025'])}. There are two limits. The data starts in January 2022, so there's no December 2021 and no 2022 figure. And every line had a {p(K['price_uplift_2024'], 0)} price increase in 2024 and {p(K['price_uplift_2025'], 0)} in 2025, which lifts NRR without any change in behaviour. Taking the price out, 2025 NRR was {p(K['nrr_ex_price_2025'])}.

- *Why does the price increase barely move GRR?* GRR caps each customer at its opening MRR, so a price rise can't push a customer above 100%; it only offsets some downgrades.
- *What would you want from management?* Confirmation of the price increases and their contract basis ({QA[QA.topic == 'Price increases'].qa_id.iloc[0]}), and churn reasons by customer.

## 3. What was the biggest red flag, and what does it mean for price or structure?

The biggest one is the {m(K['other_implementation_2025'])} of implementation revenue billed in 2025. Every other implementation invoice in the data is billed in the month a new customer signs up, with a median of {g(K['signup_implementation_median'])}. These {K['other_implementation_invoices']:.0f} were all to existing customers, none in their signup month, much larger, and all in the year before the sale. They take 2025 growth from {p(K['growth_ex_other_implementation_2025'])} to {p(K['headline_growth_2025'])}. They also came with delivery cost, which is why gross margin fell {abs(K['mix_effect_2025']):.1f} points. On price, I'd value the business on recurring revenue or ARR and treat that {m(K['other_implementation_2025'])} as non-recurring until we see contracts and acceptance. On structure, a specific warranty and indemnity on those contracts. And because ARR growth before price was only {p(K['arr_growth_ex_price_2025'])}, an earn-out tied to ARR or NRR protects the buyer if the growth story doesn't hold.

- *How did you find it?* An outlier screen by product, then comparing each implementation invoice's date with the customer's signup month, then the invoice ID sequence, which showed them as one block.
- *Could it be legitimate?* Yes: it could be real project work. That's why it goes to management as a question ({q_other} onwards) and into the SPA as a warranty, and the data stays as it is.

## 4. Tell me about one judgement call you made in cleaning.

The customer names. Once I normalised legal forms, {K['name_pairs']:.0f} pairs of customer IDs had the same name, differing only by Ltd against Limited. The easy thing would have been to merge them. I checked whether they looked like the same business: region, size, industry and account manager agreed no more often than for two random customers, and most pairs had contracts running at the same time. So I didn't merge anything. I flagged them and asked management whether any are the same legal entity. Merging on a guess would have changed customer counts, churn and concentration, which are exactly the numbers a buyer relies on. I kept the raw name and put a standardised name next to it, so anyone can see what changed, and the cleaning log records the rule, the {2 * K['name_pairs']:.0f} customer IDs affected and the alternative I rejected. That record matters in a deal, because the seller's adviser can challenge any adjustment and I need to show why I made it.

- *What if management says some are the same?* Then I'd merge those specific pairs through a mapping table, rerun the pipeline and show the effect on churn and concentration.
- *Another judgement you made?* Keeping the {m(K['other_implementation_2025'])} of implementation revenue in the cube with a flag. Whether it counts is a revenue-quality judgement, so I made it in the analysis and the memo and left the cleaning step to fix data errors only.

## 5. What would you do differently with real client data?

First, I'd get the general ledger and bank data so I could tie the invoices to cash as well as to the management accounts. Cash is the stronger test of whether revenue is real. Second, contracts for the largest customers, so ARR can be checked against contracted terms. Third, I'd agree definitions with the deal team before building, because NRR, churn and ARR mean slightly different things at different firms. On the build, the pipeline would run in the client's environment, for example Snowflake or Alteryx; I wrote an Alteryx version of the preparation steps with check totals for that reason. Real data would also be less tidy than this: billing and CRM systems with customer IDs that don't match, more than one currency, and revenue recognised differently from how it is invoiced. Each of those needs a mapping or a policy agreed with the client before the analysis starts. And I'd have a manager review the cleaning log before anything went to the client.

- *What would you automate first?* The reconciliation and its checks, because they rerun every time the data room is refreshed.
- *What was hardest?* Keeping every number in the databook, memo and README tied to one source. I solved it by generating them from the same output tables and testing the figures.
"""


def main():
    (ROOT / "README.md").write_text(readme(), encoding="utf-8")
    (ROOT / "docs" / "cv_bullets.md").write_text(cv_bullets(), encoding="utf-8")
    (ROOT / "docs" / "interview_prep.md").write_text(interview_prep(), encoding="utf-8")
    print("wrote README.md, docs/cv_bullets.md, docs/interview_prep.md")


if __name__ == "__main__":
    main()
