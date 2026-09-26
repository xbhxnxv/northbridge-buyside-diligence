# Overnight report

## MORNING SUMMARY

### 1. Status by step

| Step | Status |
|---|---|
| 3 Reconciliation | Done. The cube ties to the management accounts' product lines in all 48 months; four unexplained manual adjustments to the reported total. |
| 4 Core analyses | Done. 4a to 4g plus key findings; 13 charts, 39 output tables, Q15 to Q21 added. |
| 5 Excel databook | Done. 13 tabs, 901 formulas, 0 errors, 53 of 53 checks TRUE. |
| 6 Power BI plan | Done, except the `.pbix` and screenshots, which need Power BI Desktop. |
| 7 Findings memo | Done. Two pages; PDF built via Word and LibreOffice. |
| 8 Packaging | Done. README, CV bullets and interview prep; fresh-clone run passed; `v1.0` is on GitHub at `8dead6c`. |

### 2. Headline findings

| # | Finding | Number | Investor question | Materiality |
|---|---|---|---|---|
| 1 | One-off implementation billing inflates 2025 | £4.08m (8.9% of revenue); growth 22.8% falls to 11.9% without it | Q2 recurring | High |
| 2 | Growth is price-led | ARR +10.3% in 2025, +3.1% before the 7% price rise | Q6 revenue change | High |
| 3 | Retention weakening | NRR 95.4% (89.2% before price); GRR 88.8% | Q3 customers | High |
| 4 | Newer customers leave faster | 12-month retention 78.6% (2023+) against 92.5% (2017 to 2022) | Q3 customers | High |
| 5 | Largest customer shrinking | C1052 ARR down £983,535 (42.4%); six large accounts are 20.8% of revenue | Q4 concentration | High |
| 6 | Margin diluted by services mix | Gross margin 77.8% to 73.8%; mix effect 4.03 points | Q5 margin | Medium |
| 7 | Heavy discounting of large customers | £5.35m given up in 2025; large customers 22.2% off list | Q5 margin | Medium |
| 8 | Revenue is real but reported total has manual entries | Ties 48 of 48 months to product lines; +£15,000 in 2025 | Q1 real revenue | Low |

### 3. Planted issues found

Duplicate invoices; negative "paid" invoices; manual adjustments to reported revenue; the 2025 implementation-invoice cluster; uniform 5% and 7% price rises; newer cohorts churning faster; large-customer contraction; margin dilution from services; and data-quality items (Ltd/Limited name pairs, missing industry, invoices dated before signup). Detail is in "Planted issues found" at the end of this report.

### 4. Recommendation

**Proceed, with price and structure protections.** The revenue is real, reconciles to the management accounts and is 88.5% recurring, so there is no reason to walk away. But 2025 growth rests on £4.08m of one-off billing and on price increases, underlying ARR growth was 3.1%, and retention and the largest customer are both weakening. Value on ARR or recurring revenue. Add an earn-out on ARR or NRR, a specific warranty and indemnity on the 2025 implementation contracts, and escrow tied to large-account renewals.

### 5. Decisions made on your behalf

Full entries are in `docs/decisions_log.md`. **Review first** marks the ones worth reading before anything else.

- D01: anomaly treatment "excluded" (your decision; confirmed: 48 of 48 months tie to lines).
- D02: sum of product lines trusted in the four adjustment months (your decision; confirmed).
- D03: duplicates are an extract fault; management already excludes them.
- D04: materiality £1,000 a month to flag, 0.5% of month material, 0.1% of year material; labels tied, explained, unexplained.
- D05: anomaly setting moved to `02_clean.sql` so the cleaning log shows its real impact.
- D06 **Review first**: I approved the metric definitions myself.
- D07: invoice ledger is the source of truth; the uplift over subscription prices is a price increase.
- D08: penny-rounding residuals (under £1 of ARR per line) counted as price.
- D09: revenue bridge adds full-year effect, billing gaps and credit-note change so it adds up exactly.
- D10: cohort cells shown only once the whole cohort has reached the tenure; month-3 baseline.
- D11: NRR sensitivities use the five largest opening customers, and closing MRR deflated by k.
- D12 **Review first**: SaaS benchmark ranges are indicative and not sourced.
- D13: size-band margin shown on two cost bases (revenue share and equal share per customer line).
- D14: discount measured by grossing up at the contract line's discount_pct.
- D15: segment flags at plus or minus 5 points; under 30 customers is too small.
- D16 **Review first**: materiality ratings (High, Medium, Low) are my judgement.
- D17: Step 4 questions are inserted into the Q&A log by the findings notebook.
- D18: databook stores pounds and displays £'000, so tie-outs work to the penny.
- D19: LibreOffice recalculation (fallbacks not needed).
- D20: chart and layout choices in the databook.
- D21: Power BI model CSVs are regenerated, not committed (8MB).
- D22: model shape; top-10 concentration ignores customer slicers; gross profit blank under customer filters.
- D23: memo PDF via python-docx and LibreOffice (no pandoc).
- D24 **Review first**: recommendation to proceed with protections.
- D25: memo figures generated and tested against `outputs/tables/`.
- D26: README, CV bullets and interview prep generated from the pipeline.
- D27: style rules enforced by a test.

### 6. Limitations and anything that failed

- LibreOffice was installed without its spreadsheet component, so it could not open any spreadsheet. The first `apt-get install` failed on a stale package index; `apt-get update` then installing `libreoffice-calc` worked. `libreoffice-writer` was then installed for the memo. A new environment needs both (the README says so).
- pandoc is not available, so the memo uses the second route (Word, then LibreOffice to PDF).
- PyMuPDF was installed only to render pages for visual checks. It is not a pipeline dependency.
- No Power BI Desktop: the DAX has been checked in Python against the same logic, not run in Power BI.
- Notebooks, the xlsx, the docx and the PDF carry run metadata, so they show as modified after every run even when every number is the same. The CSV outputs, charts and markdown are byte-identical from run to run.
- Benchmarks in 4d are not sourced (D12).
- Pushing the `v1.0` tag from this session was refused with HTTP 403 by the session's egress policy, and I did not retry. Abhinav then created the `v1.0` release through the GitHub web interface at `8dead6c`.

### 7. What you need to do by hand

1. Build the Power BI report following `dashboard/README.md` section 7, check it against `dashboard/expected_values.csv`, and save five screenshots to `dashboard/screenshots/`.
2. Databook polish (Step 5 summary, item 9): rewrite the DRAFT commentary boxes in your words, tidy chart styling, and adjust column widths.
3. Memo: read `memo/findings_memo.pdf` and adjust wording to your voice (edit `memo/build_memo.py`, then rerun, so the numbers stay tested).
4. Read the four decisions flagged **Review first**.
5. Practise `docs/interview_prep.md` out loud.

### 8. Repo state

| Item | Value |
|---|---|
| Final commit | `8dead6c` for code and outputs; later commits on `main` only correct this report |
| Tag | `v1.0` on GitHub, pointing at `8dead6c`. The push from this session was refused (HTTP 403); Abhinav created the release through the GitHub web interface. |
| Tests | 106 passed |
| `run_all.py` from a fresh clone | 65.3 seconds (plus 46 seconds for `pip install`) |
| `main` | up to date with the session branch |

### 9. Read this first (15 minutes)

1. `memo/findings_memo.pdf` (3 min): the story in two pages.
2. `outputs/key_findings.md` (2 min): every finding with its number and investor question.
3. `docs/overnight_report.md`, "Planted issues found" (3 min): what each issue is and how it plays out in a deal.
4. `docs/metric_definitions.md`, sections on MRR, NRR/GRR and the ARR bridge (3 min): the definitions interviewers probe.
5. `notebooks/03_reconciliation.ipynb` sections 1 and 7 (2 min): how the anomaly treatment was chosen and what the flagged months contain.
6. `databook/Northbridge_Databook.xlsx`, Reconciliation and Checks tabs (2 min): what the other side's adviser would open first.

### 10. Be ready to explain

1. How did you reconcile the cube to the management accounts? (Monthly and by product line; three anomaly options tested; 48 of 48 months tie to lines.)
2. What did you do with differences you could not explain? (Labelled unexplained, quantified by year, Q12 to Q14; no adjustment.)
3. How are NRR and GRR defined and what are their limits? (December to December; GRR capped; no 2022; price lifts NRR, 89.2% before price.)
4. Why exclude credit notes from MRR? (Concessions would look like churn in the month they are issued.)
5. What is the biggest red flag? (£4.08m other implementation in 2025; growth 22.8% to 11.9%; warranty and valuation on recurring.)
6. How did you find the price increases? (Subscription vs invoiced MRR gap; 100% of lines move by exactly 5% then 7%.)
7. Why compare cohorts at matched tenure? (Older cohorts have had longer to churn; 78.6% against 92.5% at 12 months.)
8. Why did gross margin fall? (Mix: implementation work at 27.1% margin; no line's margin fell.)
9. One cleaning judgement call? (Did not merge 229 name pairs; attributes no closer than random; Q01.)
10. How do you know the databook, memo and README match the analysis? (Generated from `outputs/tables/`; tests check every £ and % and every check cell.)


## Step 3 summary: Reconciliation

**1. Status.** Done. The cube reconciles to the management accounts in every month. Every month is labelled tied, explained or unexplained, and the only unexplained items are four manual adjustments to reported total revenue.

**2. Readings of your four decisions (checked against the data; all confirmed).**
- Anomaly treatment: `excluded` ties to management's product lines in 48 of 48 months; `as_reported` and `flipped` tie in 36. All 15 invoices have the same positive amount in the months either side. Probable understatement of reported revenue: £13,843.82 over four years.
- The four round-number months: the cube equals the sum of the product lines to the penny in each, so the reported total carries adjustments not allocated to any line. June 2023 is 0.681% of that month's reported revenue, above the 0.5% monthly threshold. February 2025 adds £15,000 to the 2025 reported total.
- Duplicates and credit notes: all 29 months that held a removed duplicate tie to the lines, so reported revenue excludes the duplicates and includes the credit notes. Q06 on receivables stands.
- Labels: 33 months tied, 11 explained (months holding anomaly invoices), 4 unexplained (the adjustment months; March 2024 also holds two anomaly invoices, which makes 12 anomaly months in all).

**3. Adjustments (change to net revenue from the raw invoices).**

| Adjustment | Rows | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| A01 duplicates removed | 40 | (£8,597) | (£70,158) | (£7,116) | (£11,086) |
| A02 negative paid invoices excluded | 15 | £5,789 | £2,119 | £4,073 | £1,863 |
| All other actions (flags, links, categories) | | £0 | £0 | £0 | £0 |

**4. Source-to-reported walk (£, anomaly setting `excluded`).**

| | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|
| Raw gross billings | 28,564,164 | 32,537,963 | 37,583,315 | 46,174,480 |
| Less duplicates | (8,597) | (70,158) | (7,116) | (11,086) |
| Anomaly treatment | 5,789 | 2,119 | 4,073 | 1,863 |
| Credit notes | (329,205) | (277,054) | (321,374) | (408,836) |
| Cube net | 28,232,152 | 32,192,870 | 37,258,899 | 45,756,419 |
| Unreconciled (manual adjustments) | 0 | (18,500) | 2,500 | 15,000 |
| Management total | 28,232,152 | 32,174,370 | 37,261,399 | 45,771,419 |

**5. Cube against management reported revenue.** Differences (cube less reported): 2022 £0, 2023 £18,500, 2024 (£2,500), 2025 (£15,000). Every product line ties in every month (192 of 192). Costs tie to cost of sales in all 48 months.

**6. Files created or changed.**
- `sql/02_clean.sql`: anomaly setting moved here and set to `excluded`; A02 rule and rationale record the decision.
- `sql/03_revenue_cube.sql`: reads the setting from `02_clean.sql`.
- `sql/04_reconciliation.sql`: status labels and explanations, unexplained-items register, effects on reported totals, Q11 to Q14.
- `notebooks/03_reconciliation.ipynb`: executed reconciliation.
- `outputs/tables/step3_*.csv`: options, monthly, annual, product-line, internal checks, costs, walk, drill-down, unexplained items, effects.
- `docs/decisions_log.md`: new; D01 to D05.
- `docs/qa_log.md`, `docs/cleaning_log.md`, `docs/metric_definitions.md`: regenerated or updated for the setting.
- `tests/test_tieouts.py`: 7 new Step 3 tests.

**7. Tests and runtime.** 67 passed. `run_all.py` from scratch: 16.0 seconds.

**8. Git.** Committed and pushed to `main` (see the commit list in the morning summary).

**9. Judgement calls to review.**
- March 2024 is labelled unexplained although it also holds two anomaly invoices: the £12,000 adjustment is the part the data cannot explain.
- The probable understatement from the anomalies (£13,844) is reported, not booked. Booking it would mean the cube no longer ties to management's lines.

**10. Be ready to explain.**
- Why is "excluded" the right treatment when the invoices look like sign errors, and what would flipping them do?
- Why trust the product lines over the reported total in the four adjustment months?
- What is the difference between "explained" and "unexplained", and why does it matter to the buyer?
- Why does the February 2025 adjustment matter more than the June 2023 one, even though June 2023 is the only one above the monthly threshold?
- How do you show the other side that the annual differences are made up only of documented items?

**11. What Step 4 does first.** Writes the full metric definitions, then checks subscription-based MRR against invoiced MRR at each year end before relying on either.

## Step 4 summary: Core analyses

**1. Status.** Done. Metric definitions were written first (D06), then 4a to 4g and a findings notebook (4h). There are 13 charts, 39 output tables, `outputs/key_findings.md` and seven new Q&A items (Q15 to Q21).

**2. Readings.** Revenue is real, but its quality is weaker than the headline:
- 2025 growth of 22.8% falls to 12.1% on recurring revenue and 11.9% without the 45 other-implementation invoices.
- ARR growth before the price increases was 3.1% in 2025.
- Retention is falling, especially for customers won from 2023.
- The largest customer cut its ARR by 42% in September 2025.

**3. Adjustments.** None in Step 4 (analysis only). The cleaning adjustments are unchanged from Step 3.

**4. Revenue walk (£m).** Net revenue was 28.23, 32.19, 37.26 and 45.76 for 2022 to 2025. The 2025 increase of 8.50 breaks down as: other implementation 4.08, new customers 3.07, full-year effect 2.18, price 2.46, cross-sell 0.28, churn (2.64), downgrade (0.90), credit notes and signup implementation (0.03).

**5. Headline figures.**

| | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|
| ARR (£m, December MRR × 12) | 29.01 | 32.78 | 37.50 | 41.36 |
| ARR growth before price increase | | 13.0% | 8.9% | 3.1% |
| NRR (2023 to 2025 only) | | 95.8% | 98.7% | 95.4% |
| NRR excluding price increase | | 95.8% | 94.0% | 89.2% |
| GRR | | 94.5% | 92.9% | 88.8% |
| Logo churn | | 8.9% | 11.0% | 12.7% |
| Recurring share of revenue | 96.5% | 96.3% | 96.9% | 88.5% |
| Six large accounts' share | 32.7% | | | 20.8% |
| Gross margin | 77.4% | 77.4% | 77.8% | 73.8% |

**6. Files created.**
- `docs/metric_definitions.md`: rewritten in full.
- `notebooks/charts.py`: validated palette and chart style.
- `notebooks/04a` to `04h`: the executed analyses.
- `sql/analysis/*.sql`: 11 query files.
- `outputs/tables/4*.csv`, `key_figures.csv` and `key_findings.csv`.
- `outputs/charts/4*.png`: 13 charts.
- `outputs/key_findings.md`.
- `docs/qa_log.md`: now Q01 to Q21.
- `docs/decisions_log.md`: D06 to D17 added.
- `tests/test_tieouts.py`: 12 new tests.

**7. Tests and runtime.** 79 passed. From scratch, `run_all.py` takes 53.8 seconds.

**8. Git.** Pushed to `main` at the end of the step.

**9. Judgement calls to review.**
- D06: I approved the metric definitions myself.
- D12: the benchmark ranges are indicative and unsourced.
- D16: the materiality ratings are my judgement.
- D13: margin by size band depends heavily on the cost allocation basis (70.5% against 50.6% for Micro customers in 2025). I would not quote either without a cost-to-serve driver from management.

**10. Be ready to explain.**
- Why is NRR excluding price the better measure here, and why is GRR less affected by the price increase?
- Why compare cohorts at matched tenure, and what does the 2024 cohort's 74.6% at 12 months tell you?
- How does the ARR bridge prove itself, and why are upsell and contraction zero?
- Why did gross margin fall in 2025 when no product line's margin fell?
- How would you present the 2025 other-implementation revenue to an investment committee?

**11. What Step 5 does first.** Builds the databook from `outputs/tables/`, with input values in blue and every total, share and check as a live Excel formula. It then recalculates the workbook in LibreOffice and scans every cell for errors.

## Step 8 summary: Portfolio packaging

**1. Status.** Done. The README, CV bullets and interview prep are generated from the pipeline, the fresh-clone run passed, and `v1.0` is on GitHub at `8dead6c` (the push from this session was refused with HTTP 403; Abhinav created the release through the GitHub web interface).

**2. Readings.** The README is 397 words, with five headline findings and three charts. There are three CV bullets. The interview prep has five answers of about 135 to 165 words each (roughly 60 to 75 seconds spoken), with two follow-ups per answer. Every £ and % in them is tested against `outputs/tables/`.

**3. Adjustments.** None.

**4. Revenue walk.** Not applicable.

**5. Fresh-clone check.**

| Check | Result |
|---|---|
| Clone | `main`, new virtual environment from `requirements.txt` (46 seconds to install) |
| `run_all.py` from nothing (data, database, outputs, databook, memo deleted) | exit 0 in 65.3 seconds |
| Tests | 106 passed |
| Regenerated CSVs, charts and markdown | identical to the committed versions |

**6. Files created.**
- `docs/build_readme.py`: the generator.
- `README.md`: rewritten.
- `docs/cv_bullets.md` and `docs/interview_prep.md`: new.
- `tests/test_tieouts.py`: style, README and figure tests.

**7. Tests and runtime.** 106 passed. From a fresh clone, `run_all.py` takes 65.3 seconds.

**8. Git.** Pushed to `main`; `v1.0` is on GitHub at `8dead6c`.

**9. Judgement calls to review.** The interview answers are in a plain spoken style. Adjust the phrasing to how you speak, in `docs/build_readme.py`, so the figures stay tested.

**10. Be ready to explain.** See section 10 of the morning summary.

**11. Next.** Nothing further in the brief. Your hand steps are in section 7 of the morning summary.

## Planted issues found

I have not read the generator, so this is my reading of which issues were planted. Each entry covers what the issue is, how it was found, the evidence, the £ impact, and what it means in a real deal.

1. **Exact duplicate invoices.**
   - What it is: 40 invoices duplicated on every field except the ID. Every copy is overdue, and every second copy sits in a block at the end of the invoice numbering.
   - How it was found: grouping on all business fields except the ID (profile P04).
   - Evidence: the management accounts already exclude them; the cube ties once they are removed.
   - Impact: £96,957 of revenue that should not be counted. Immaterial to revenue.
   - In a real deal: a data-extract quality point. Check the receivables ledger (Q06), because overdue copies would overstate debtors in the completion accounts and the working capital peg.

2. **Negative amounts on invoices marked paid.**
   - What it is: 15 negative "paid" invoices. Each is the only billing that month, and the months either side carry the same amount as a positive.
   - How it was found: profile P06, then the three-way reconciliation test (only "excluded" ties to the management accounts).
   - Impact: reported revenue probably understated by £13,844 over four years. Immaterial.
   - In a real deal: a billing-controls point (Q11).

3. **Manual adjustments to reported total revenue.**
   - What it is: in four months the product lines don't add up to the total, by round amounts.
   - How it was found: the internal check on the management accounts (P05), then the reconciliation, where the cube ties to the lines and not the total.
   - Impact: the reported total is £18,500 below the invoices in 2023, £2,500 above in 2024 and £15,000 above in 2025.
   - In a real deal: small in £ but a controls red flag. Ask for the journals (Q12 to Q14), confirm which figure is in the information memorandum, and seek a warranty on the management accounts.

4. **A cluster of large one-off implementation invoices in 2025.**
   - What it is: 45 invoices worth £4.08m (8.9% of 2025 revenue), all to existing customers, none in the signup month. The median is about 28 times a normal implementation invoice, and the IDs form one block.
   - How it was found: the outlier fence, the timing against signup month, and the ID sequence (P02).
   - Impact: headline 2025 growth of 22.8% falls to 11.9% without them. Implementation cost of delivery rose to £3.85m.
   - In a real deal: the most price-relevant finding. Exclude it from run-rate revenue and EBITDA, value the business on recurring revenue, and ask for contracts and acceptance evidence (Q02 to Q05). Consider a specific warranty or indemnity.

5. **Across-the-board price increases.**
   - What it is: every recurring line bills 5% more from January 2024 and 7% more from January 2025. The subscription table does not record the increases.
   - How it was found: comparing subscription MRR with invoiced MRR, then the distribution of same-line changes (100% of lines move by exactly the same %).
   - Impact: £1.52m of ARR in 2024 and £2.31m in 2025. ARR growth before price is 3.1% in 2025.
   - In a real deal: growth is price-led. NRR excluding price is 89.2%. Test whether the price rises contributed to churn, and underwrite the forecast on volume.

6. **Newer cohorts churn faster.**
   - What it is: at matched tenure, 12-month retention is 78.6% for 2023+ signups against 92.5% for 2017 to 2022 signups. The 2024 cohort is at 74.6%.
   - How it was found: tenure-matched cohort analysis (4c). Cumulative churn hid it, because older cohorts show more churn to date.
   - Impact: logo churn rose from 8.9% to 12.7%, and GRR fell to 88.8%.
   - In a real deal: lower retention assumptions in the model and a lower price, or an earn-out tied to retention or ARR (Q18, Q19).

7. **Contraction of the largest customers.**
   - What it is: C1052 dropped Analytics and Payments in September 2025, cutting its ARR by £983,535 (42%). C1545 dropped Payments in February 2025, cutting ARR by £243,915 (12%). The six large accounts are 20.8% of 2025 revenue.
   - How it was found: the top-10 run-rate analysis (4b) and the downgrade line of the ARR bridge (£1.53m in 2025).
   - In a real deal: adjust the price for lost run-rate, review renewal and change-of-control terms (Q16, Q17), and consider escrow or warranties linked to large-account renewals.

8. **Margin dilution from the implementation mix.**
   - What it is: gross margin fell 4.0 points in 2025, all through mix. No product line's margin fell.
   - How it was found: the mix/rate split (4f).
   - In a real deal: normalise EBITDA for the one-off services work.

9. **Data-quality items.** None of these changes revenue totals.
   - 229 pairs of customer IDs differ only by "Ltd" against "Limited". Not merged; raised as Q01.
   - 132 customers have no industry. Set to Unknown.
   - 5 customer names have irregular punctuation.
   - 1,423 invoices are dated a few days before signup, always in the same month.
   - In a real deal: they affect customer counts, cohort dates and segment analysis. Log them and raise them, but they don't change value.

## Step 5 summary: Excel databook

**1. Status.** Done. `databook/Northbridge_Databook.xlsx` has 13 tabs, is built by `databook/build_databook.py` from `outputs/tables/`, and is recalculated by LibreOffice. It contains 901 formulas and 0 errors, and all 53 check cells are TRUE.

**2. Readings.** Every total, share, growth rate, difference and check on the analysis tabs is a live formula. The only values are the inputs loaded from the pipeline (in blue). Source totals tie on the face of each tab: 4a to Reconciliation, 4b and 4g to 4a, 4d opening MRR to 4a ARR, the 4e bridges to 4a, and 4f gross profit to management gross profit after the unexplained adjustments.

**3. Adjustments.** None.

**4. Revenue walk.** Shown on the Reconciliation tab as formulas: raw gross billings, less duplicates, anomaly treatment and credit notes give cube net revenue; adding the unreconciled difference gives the management total.

**5. Verification.**

| Check | Result |
|---|---|
| Recalculation method | LibreOffice 24.2 headless, Basic macro `calculateAll` (D19) |
| Formulas / errors | 901 / 0 (`databook/recalc_report.json`) |
| Check cells TRUE | 53 of 53; overall check TRUE |
| Key figures against `outputs/tables/` | 147 of 147 within £0.005 (ratios within 1e-6) |
| Inputs blue, formulas black | Tested on seven analysis tabs |

**6. Files created.**
- `databook/build_databook.py`: the builder.
- `databook/recalc.py`: LibreOffice recalculation and error scan.
- `databook/Northbridge_Databook.xlsx`: the databook.
- `databook/cell_map.json` and `databook/recalc_report.json`: for the tests.
- `report_config.json`: project name, report date, disclaimer.
- `notebooks/nb_utils.py`: saved tables rounded to 6 decimals so runs are identical.
- `tests/test_tieouts.py`: 5 databook tests.

**7. Tests and runtime.** 84 passed. From scratch, `run_all.py` takes 59.8 seconds.

**8. Git.** Pushed to `main`.

**9. Polish by hand.**
- Commentary: the DRAFT boxes use the generated key-findings text word for word. Rewrite each in your own words and cut it to two or three sentences per tab.
- Charts: openpyxl charts are plain. Worth tidying:
  - Axis number formats on the 4b and 4d charts.
  - The ARR waterfall: its base series is white, so check it prints cleanly.
  - Legend placement.
- Column widths:
  - The Reconciliation explanation column is 100 wide.
  - The 4c triangle columns are narrow.
  - The Q&A log rows are fixed at 75 points high; long evidence text may need more.
- Number formats: the Reconciliation monthly % column uses three decimals so small differences show. Change it to one if you prefer the house style.

**10. Be ready to explain.**
- Why keep inputs in pounds and display thousands, instead of dividing by 1,000?
- What does each check on the Checks tab prove, and which one would you show a reviewer first?
- Why are inputs blue and formulas black, and what would a hardcoded total hide?
- How do you know the databook matches the analysis?

**11. What Step 6 does first.** Exports the star-schema CSVs for Power BI and writes the relationships and DAX measures.

## Step 6 summary: Power BI build plan

**1. Status.** Done, apart from the `.pbix` and screenshots, which need Power BI Desktop.

**2. Readings.**
- The model is a star with one snowflake level: `DimProductLine` sits above `DimProduct`, so a single product-line slicer filters revenue, MRR and cost.
- There are 24 measures in `dashboard/measures.dax`, each commented.
- Measures that deliberately ignore slicers:
  - Top 10 concentration ignores customer slicers.
  - Cohort measures ignore the year slicer.
  - Gross profit is blank under customer filters, because cost has no customer grain.

**3. Adjustments.** None.

**4. Revenue walk.** Not applicable.

**5. Expected values.** 624 rows in `dashboard/expected_values.csv` across these contexts: each year; each year × product line; 2025 × region group, region and size band. The year rows match the Step 4 outputs exactly. Example for 2025:

| Net revenue | ARR | Recurring % | NRR | GRR | Top 10 share | Gross margin |
|---:|---:|---:|---:|---:|---:|---:|
| £45.76m | £41.36m | 88.5% | 95.4% | 88.8% | 22.3% | 73.8% |

**6. Files created.**
- `dashboard/export_model_data.py`: exports the model and computes the expected values.
- `dashboard/measures.dax`: the measures.
- `dashboard/README.md`: model, relationships, wireframes, slicers and numbered build steps.
- `dashboard/expected_values.csv`: the expected values.
- `dashboard/model_data/*.csv`: generated, not committed (D21).

**7. Tests and runtime.** 88 passed. Runtime is in the Step 8 summary.

**8. Git.** Pushed to `main`.

**9. Judgement calls to review.**
- D22: gross profit is blank under region and size filters. You may prefer to show the allocated margin from 4f instead, but it is an allocation.
- The DAX has not been run in Power BI. It follows standard patterns, but check it against `expected_values.csv` as you build.

**10. Be ready to explain.**
- Why does FactCost need a product-line dimension, and what goes wrong if you join it to DimProduct?
- Why does the Top 10 measure remove customer filters?
- How do the NRR and GRR measures pick the opening and closing Decembers?
- How would you prove your Power BI numbers match the databook?

**11. What Step 7 does first.** Writes the findings memo from the key figures, then exports it to PDF and checks the page count.

## Step 7 summary: Findings memo

**1. Status.** Done. `memo/findings_memo.md`, `.docx` and `.pdf` are generated by `memo/build_memo.py`. The PDF is 2 pages and about 1,050 words.

**2. Readings.** The recommendation is to proceed with price and structure protections (D24). The revenue is real, reconciles and is 88.5% recurring. The problems are its quality and trend:
- one-off implementation billing;
- price-led growth;
- weakening retention;
- a shrinking largest customer.

**3. Adjustments.** The suggested view of 2025 revenue:

| Basis | 2025 | Growth |
|---|---:|---:|
| Reported total | £45.77m | |
| Net revenue (invoice ledger) | £45.76m | 22.8% |
| Excluding other implementation | £41.68m | 11.9% |
| Recurring only | £40.48m | 12.1% |
| ARR, December 2025 | £41.36m | 10.3% (3.1% before price) |

**4. Revenue walk.** As in Step 3.

**5. Red flags.**

| Red flag | Rating |
|---|---|
| Other implementation revenue | High |
| Price-led growth | High |
| Retention weakening | High |
| Largest customers contracting | High |
| Margin dilution from services | Medium |
| Manual adjustments to reported revenue | Low |

The memo lists 14 questions for management, drawn from Q01 to Q21. It names five protections, each linked to a red flag:
- price adjustment;
- earn-out on ARR or NRR;
- specific warranty and indemnity;
- escrow or retention on large-account renewals;
- completion accounts.

**6. Files created.**
- `memo/build_memo.py`: the memo builder.
- `memo/findings_memo.md`, `.docx` and `.pdf`: the memo.
- `memo/memo_report.json`: page and word count.
- `run_all.py`: new memo and readme stages.
- `requirements.txt`: adds python-docx and pypdf.
- `tests/test_tieouts.py`: 4 new tests.

**7. Tests and runtime.** 92 passed. Runtime is in the Step 8 summary.

**8. Git.** Pushed to `main`.

**9. Judgement calls to review.**
- D24: the recommendation.
- The red-flag ratings.
- Whether a buyer would treat the £4.08m as non-recurring outright, or only until evidence arrives. I chose the second.

**10. Be ready to explain.**
- Walk the investment committee through the memo in two minutes.
- Why proceed rather than walk away?
- Which protection addresses which finding, and why an earn-out and not only a lower price?
- Why is the 3.1% ARR growth before price increases the most important number in the memo?

**11. What Step 8 does first.** Rewrites the README from the pipeline figures, writes the CV bullets and interview prep, then runs the fresh-clone check and tags v1.0.
