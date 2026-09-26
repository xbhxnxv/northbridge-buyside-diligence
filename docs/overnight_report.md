# Overnight report

<!-- MORNING SUMMARY: written at the end of the run -->

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
