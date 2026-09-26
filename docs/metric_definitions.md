# Metric definitions

Status: draft. The revenue, MRR, cohort and tenure definitions below are fixed by the Step 2 cube. The full set is to be signed off before Step 4, and every analysis uses these definitions unchanged.

Figures inside the generated blocks are rewritten by `notebooks/02_data_preparation.ipynb` on every run of `python run_all.py`. Do not edit them by hand.

## Revenue

**Revenue month.** The calendar month of `invoice_date` (`month_start` in the cube). The day of the month is ignored: invoice days vary from month to month for the same customer and product, so the month is the meaningful grain.

**Gross billings.** The sum of invoices other than credit notes in a month.

**Credit notes.** Invoices with status `credited`. They are negative and count as revenue in the month they are dated. Each is linked to the original invoice it reverses.

**Net revenue.** Gross billings plus credit notes. This is the figure reconciled to the management accounts.

**Recurring and one-off.** Taken from the product's `revenue_type`. Core Platform, Analytics Add-on and Payments Module are recurring. Implementation Services is one-off. One-off revenue is split further by `oneoff_category`: `signup_implementation` for invoices billed in the customer's signup month, and `other_implementation` for the rest.

**Overdue.** Billings with status `overdue` stay in revenue because the service was billed and delivered. They are reported separately as a cash-collection point.

**Anomaly treatment (P06).** Negative amounts on invoices marked `paid` are flagged. The cube uses one of three treatments, set in `cfg_settings.anomaly_treatment`: `as_reported`, `flipped` or `excluded`. Step 3 settled it as `excluded`, the only treatment under which the cube ties to the management accounts' product lines in every month (decision D01). These invoices therefore contribute nothing to revenue or MRR.

## MRR and ARR

**MRR.** Recurring billings before credit notes in a month, per customer and product (`fact_mrr_monthly`). Credit notes are left out because they are service concessions. Netting them in would make a customer look as if it had contracted or churned in the month of a concession, which would distort churn and the ARR bridge. The credit notes left out of MRR are:

<!-- BEGIN GENERATED: mrr_credit_notes -->
| year | credit_notes | credit_note_amount |
| ---: | ---: | ---: |
| 2022 | 201 | (£329,205) |
| 2023 | 258 | (£277,054) |
| 2024 | 288 | (£321,374) |
| 2025 | 337 | (£408,836) |

Total left out of MRR across 2022 to 2025: (£1,336,469) on 1,084 credit notes.
<!-- END GENERATED: mrr_credit_notes -->

Net revenue still includes these credit notes. MRR and net revenue therefore differ by design.

**ARR at a year end.** December MRR × 12.

**Active customer.** A customer with MRR above zero in the month.

## Retention

**Logo churn.** A customer active at the start point with no recurring MRR at the end point.

**NRR for year Y.** December Y MRR from customers who were active in December Y−1, divided by their December Y−1 MRR. It can only be computed for 2023, 2024 and 2025, because the data has no December 2021.

**GRR for year Y.** As NRR, with each customer's December Y MRR capped at their December Y−1 level. The same 2023 to 2025 limit applies.

## Cohorts and tenure

**Cohort.** Signup quarter from `customers.signup_date` (`signup_quarter`).

**Cohort month 0.** The calendar month of `signup_date` (`signup_month`). Some first invoices are dated a few days before `signup_date`, always in the same calendar month (P10, Q09). Counting from the signup month keeps those invoices in month 0.

**Tenure.** Whole calendar months from the signup month. An invoice in the signup month is tenure 0, the next month is tenure 1, and so on.

**Data-window caveat.** Customers who signed up before January 2022 are left-censored in the invoice data (`is_pre_window`). Logo retention across a customer's whole life uses subscription start and end dates. Revenue retention triangles use only cohorts that start inside the window (2022Q1 onwards).

## Large accounts

**`is_large_account`.** A customer with any subscription line priced at 10 times list price or more. The rule is set on the subscription table so it does not depend on invoice outliers.

<!-- BEGIN GENERATED: large_accounts -->
The rule flags 6 customers (18 subscription lines, priced at 15.6 times list or more). Every other subscription line is priced at no more than 1.07 times list, so the 10x threshold separates the two groups with a wide margin.
<!-- END GENERATED: large_accounts -->
