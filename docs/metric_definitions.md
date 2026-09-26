# Metric definitions

Status: final for Steps 4 to 7. Written before any Step 4 analysis and approved by the analyst in Abhinav's absence during the overnight run (decision D06 in `docs/decisions_log.md`). Every analysis, the databook, the dashboard measures and the memo use these definitions unchanged.

Figures inside the generated blocks are rewritten on every run of `python run_all.py`. Do not edit them by hand.

## Source of truth

**Revenue, MRR and ARR come from the invoice ledger** (the cleaned revenue cube). It ties to the management accounts' product lines in all 48 months (Step 3). The subscriptions table is used for customer lifecycle dates (logo retention across a customer's whole life, including before 2022), contract attributes (term, discount) and the large-account flag. It is not used for revenue.

**Subscription prices against invoiced amounts.** Before relying on either source, subscription-based MRR (active lines × `monthly_price`) was compared with invoiced MRR at each year end:

<!-- BEGIN GENERATED: sub_vs_invoice -->
| year_end | subscription_lines | invoiced_lines | unmatched_lines | subscription_mrr | invoiced_mrr | gap | invoiced_over_subscription | lines_at_that_ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-12-01 | 1,566 | 1,566 | 0 | £2,417,140 | £2,417,140 | £0 | 1.0000 | 1,566 |
| 2023-12-01 | 1,893 | 1,893 | 0 | £2,731,779 | £2,731,779 | £0 | 1.0000 | 1,893 |
| 2024-12-01 | 2,149 | 2,149 | 0 | £2,975,939 | £3,124,736 | £148,797 | 1.0500 | 2,149 |
| 2025-12-01 | 2,355 | 2,355 | 0 | £3,067,781 | £3,446,652 | £378,872 | 1.1235 | 2,355 |
<!-- END GENERATED: sub_vs_invoice -->

The two sources agree line for line on which customers hold which products. The gap is a uniform uplift: from January 2024 every recurring line bills at `monthly_price` × 1.05, and from January 2025 at × 1.1235 (a further 7%). The subscription table keeps the price at contract start and does not record the increases. This analysis treats the uplift as an across-the-board price increase, which is the "price increase" component of the ARR bridge. Management has not confirmed the increases (Q15).

## Revenue

**Revenue month.** The calendar month of `invoice_date` (`month_start`). The day is ignored, because invoice days vary from month to month for the same customer and product.

**Gross billings.** Invoices other than credit notes.

**Credit notes.** Invoices with status `credited`, negative, counted in the month they are dated and linked to the invoice they reverse.

**Net revenue.** Gross billings plus credit notes. This is the figure reconciled to the management accounts.

**Recurring and one-off.** From the product's `revenue_type`. Core Platform, Analytics Add-on and Payments Module are recurring; Implementation Services is one-off. One-off revenue is split by `oneoff_category`: `signup_implementation` (billed in the customer's signup month) and `other_implementation` (the rest).

**Anomaly treatment (P06).** The 15 negative amounts on invoices marked paid are excluded (`cfg_settings.anomaly_treatment = excluded`, decision D01). They contribute nothing to revenue or MRR.

**Overdue.** Stays in revenue; reported separately as a cash-collection point.

**Headline growth.** Year-on-year change in net revenue. **Recurring growth:** the same on recurring net revenue. **Growth excluding other implementation:** net revenue less `other_implementation`. **Normalised growth:** recurring net revenue only, which excludes all one-off revenue.

## MRR and ARR

**MRR.** Recurring billings before credit notes in a month, per customer and product (`fact_mrr_monthly`). Credit notes are service concessions; netting them in would make a customer look as if it had contracted or churned in the month of a concession. The credit notes left out of MRR are:

<!-- BEGIN GENERATED: mrr_credit_notes -->
| year | credit_notes | credit_note_amount |
| ---: | ---: | ---: |
| 2022 | 201 | (£329,205) |
| 2023 | 258 | (£277,054) |
| 2024 | 288 | (£321,374) |
| 2025 | 337 | (£408,836) |

Total left out of MRR across 2022 to 2025: (£1,336,469) on 1,084 credit notes.
<!-- END GENERATED: mrr_credit_notes -->

Net revenue still includes these credit notes, so MRR and net revenue differ by design.

**ARR at a year end.** December MRR × 12.

**Active customer.** A customer with MRR above zero in the month.

## Retention

**Logo churn (annual).** A customer active in December Y−1 with no MRR in December Y. Logo churn rate = churned customers / customers active in December Y−1.

**NRR for year Y.** December Y MRR from customers active in December Y−1, divided by their December Y−1 MRR. Customers who churned count at zero; new customers are excluded.

**GRR for year Y.** As NRR, with each customer's December Y MRR capped at their December Y−1 level.

**NRR and GRR are available for 2023, 2024 and 2025 only.** The data has no December 2021. This limit is repeated wherever the figures appear.

**NRR and GRR sensitivities.** (a) Excluding the five customers with the largest December Y−1 MRR. (b) Excluding the price increase: each customer's December Y MRR is divided by the year's uplift factor before the calculation.

## Benchmarks

**Source figures.** SaaS retention benchmarks are read from published surveys into `data/reference/benchmarks_source.csv` and copied by the 04d notebook to `outputs/tables/benchmarks.csv`. Sources, sample sizes, each source's own definitions, the figures and the caveats are in [`docs/benchmarks.md`](benchmarks.md); how they were chosen is in decisions D35 to D39.

**SMB segment.** Companies whose annual contract value is under US$50k. $50k to $250k is mid-market and above $250k enterprise; those are shown as context only.

**Adopted SMB range.** For NRR and GRR, the lowest to the highest SMB median in the latest edition of each source rated high or medium for comparability. SaaS Capital's SMB medians are also shown on their own, because its NRR and GRR definitions are the same as the ones above.

**Comparability.** High: the source's definition matches ours. Medium: close, but the treatment of price increases or the revenue basis is not stated. Low: a different method or population. A benchmark places Northbridge in a distribution; it is not a pass mark.

## ARR bridge (December to December, at customer × product line)

For opening December Y−1 and closing December Y:

- **New:** customer not active in the opening December, active in the closing December. Value: closing ARR.
- **Churn:** customer active in the opening December, not active in the closing December. Value: minus opening ARR.
- For customers active in both Decembers, by product line:
  - **Cross-sell:** line held at close but not at open. Value: closing ARR of the line.
  - **Downgrade:** line held at open but not at close. Value: minus opening ARR of the line.
  - **Price increase:** for lines held at both, opening ARR × (k − 1), where k is the year's uniform uplift factor.
  - **Upsell / contraction:** for lines held at both, closing ARR − opening ARR × k. Positive is upsell (for example a tier change), negative is contraction.

Opening ARR plus all components equals closing ARR in every year (tested).

**How k is measured.** For each year, the distribution of same-line % changes in MRR between consecutive Decembers, for customer × product lines held in both:

<!-- BEGIN GENERATED: price_change_evidence -->
| year | pct_change | lines | share_of_lines_pct |
| ---: | ---: | ---: | ---: |
| 2023 | 0.00% | 1,425 | 100.0% |
| 2024 | 5.00% | 1,686 | 100.0% |
| 2025 | 7.00% | 1,890 | 100.0% |

| year | k | share_of_lines_at_k_pct | continuing_lines |
| ---: | ---: | ---: | ---: |
| 2023 | 1.0000 | 100.0% | 1,425 |
| 2024 | 1.0500 | 100.0% | 1,686 |
| 2025 | 1.0700 | 100.0% | 1,890 |
<!-- END GENERATED: price_change_evidence -->

k is the most common same-line ratio in the year. Because every continuing line moves by exactly that percentage, the upsell / contraction residual is zero. No customer changed Core Platform tier in the data, so there are no tier upsells, and the bridge reports zero for them.

## Revenue bridge (year on year, for investor question 6)

Year-on-year change in net revenue, split into recurring and one-off. Recurring billings are analysed at customer × product line on annual totals:

- **New customers:** recurring billings in Y from customers with none in Y−1.
- **Churn:** minus Y−1 billings from customers with none in Y, plus the part-year loss on customers who stop being billed during Y (fewer billed months than in Y−1 and no MRR in December Y).
- **Cross-sell:** Y billings on a product line a continuing customer did not have in Y−1.
- **Downgrade:** minus Y−1 billings on a line a continuing customer no longer has in Y, plus the part-year loss on lines that stop during Y while the customer stays.
- **Price increase:** on lines billed in both years, Y billings × (1 − 1/k).
- **Full-year effect of prior-year additions:** on lines billed in both years, the extra months billed in Y at Y−1 prices (a customer or line that started part-way through Y−1 is billed for more months in Y).
- **Upsell / contraction:** same-line change not explained by price or months billed (zero in this data).
- **Credit notes:** change in credit notes.
- One-off: **signup implementation** and **other implementation**, each as the change on the year.

The components add up to the change in cube net revenue in every year (tested).

## Cohorts and tenure

**Cohort.** Signup quarter from `customers.signup_date` (`signup_quarter`).

**Cohort month 0.** The calendar month of `signup_date`. Some first invoices are dated a few days before `signup_date`, always in the same calendar month (P10, Q09); counting from the signup month keeps them in month 0.

**Tenure.** Whole calendar months from the signup month.

**Logo retention triangle.** Share of a cohort's customers with any subscription line live at each tenure month (subscription start and end dates, so cohorts back to 2017 are included).

**Revenue retention triangle.** A cohort's MRR at each tenure month divided by its MRR at month 3. Month 3 is the baseline because add-on products can be taken up in the first months after signup. Only cohorts that start inside the data window (2022Q1 onwards) are used, because there are no invoices before 2022. The figures are nominal and include the 2024 and 2025 price increases.

**Tenure-matched comparison.** Cohorts are compared at the same tenure (6, 12 and 18 months), never on cumulative churn to date. An older cohort has had longer to lose customers, so comparing cumulative churn across cohorts of different ages confuses age with quality.

## Concentration

**Top-N share.** Net revenue of the N largest customers in a year (ranked on that year's net revenue) divided by total net revenue; also on recurring net revenue. N = 1, 5, 10, 20. A customer is flagged above 5% and above 10% of a year's net revenue.

**Declining top customer.** A top-10 customer (on 2025 net revenue) whose December 2025 ARR is below its December 2024 ARR. Run-rate impact: December 2025 ARR against December 2024 ARR, and against its peak ARR (highest monthly MRR × 12 in the window).

## Margin

**Gross margin by product line.** (Net revenue of the line − total cost of delivery of the line) / net revenue of the line, from `costs.csv` and the cube. The sum across lines is the invoice-based gross profit; its difference to management gross profit is the unexplained manual adjustments to reported revenue (Step 3).

**Margin by size band.** Each product line's monthly cost is allocated to customers pro rata to their net revenue on that line in that month. Limit: this assumes cost moves with revenue, so size bands differ only through product mix; a large discounted customer is not shown as costing more or less to serve per £. A second basis, cost shared equally across active customer lines, is shown as a sensitivity.

**Discount.** Each recurring invoice is grossed up to a list-equivalent at its line's `discount_pct`: list-equivalent = amount / (1 − discount_pct). Revenue given up = list-equivalent − amount. Margin at list = (list-equivalent revenue − cost) / list-equivalent revenue.

**Mix and rate effects.** Change in blended margin from Y−1 to Y. Mix effect = Σ (revenue share in Y − share in Y−1) × line margin in Y−1. Rate effect = Σ revenue share in Y × (line margin in Y − line margin in Y−1). Mix + rate = change in blended margin.

## Segments

Industry (including Unknown), region group (UK against EU), acquisition channel and company size. Revenue and growth use net revenue. Logo churn is the annual December-to-December measure (not tenure-matched). NRR is 2025. A segment with fewer than 30 customers active in December 2024 is flagged as too small to support a conclusion.

## Large accounts

**`is_large_account`.** A customer with any subscription line priced at 10 times list price or more.

<!-- BEGIN GENERATED: large_accounts -->
The rule flags 6 customers (18 subscription lines, priced at 15.6 times list or more). Every other subscription line is priced at no more than 1.07 times list, so the 10x threshold separates the two groups with a wide margin.
<!-- END GENERATED: large_accounts -->
