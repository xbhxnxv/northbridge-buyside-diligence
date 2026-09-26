# Q&A log

Questions for management raised by the data. Generated from the `qa_log` table, which the Step 2 and 3 SQL and the Step 4 findings notebook append to. The evidence is built from the tables on every run. Do not edit by hand.

## Q01: Customer identity (P07, Step 2)

**Question.** For each pair of customer_ids whose names differ only in "Ltd" against "Limited", are the two ids the same legal entity? If so, which id should revenue and contract history sit under?

**Evidence.** 229 pairs (458 customer_ids) share a normalised name. Within a pair, region, size, industry and account manager agree no more often than for random pairs, and most pairs run contracts at the same time. List in docs/data_profile.md section 12.

**Status.** open

## Q02: Other implementation revenue (P02, Step 2)

**Question.** What work do the 2025 implementation invoices billed outside the customer's signup month relate to? Please provide the statement of work or contract for each.

**Evidence.** 45 invoices, £4,076,574 in total, ranging £32,292 to £147,347, all dated 2025, all for existing customers. Implementation invoices billed at signup have a median of £3,180.

**Status.** open

## Q03: Other implementation revenue (P02, Step 2)

**Question.** What is the delivery and customer-acceptance status of each of these projects at December 2025?

**Evidence.** 3 of the 45 invoices (£277,704) are overdue.

**Status.** open

## Q04: Other implementation revenue (P02, Step 2)

**Question.** On what basis is this revenue recognised: on invoice, on milestone, or on completion and acceptance? Is any of it deferred in the management accounts?

**Evidence.** £4,076,574 billed in 2025 on 45 invoices.

**Status.** open

## Q05: Other implementation revenue (P02, Step 2)

**Question.** Are further projects of this kind contracted or expected in 2026? Please provide the pipeline with values and expected dates.

**Evidence.** None were billed in 2022 to 2024; all fall in 2025.

**Status.** open

## Q06: Duplicate invoices (P04, Step 2)

**Question.** Were the duplicate invoice copies issued to customers, and are they included in the receivables ledger and the overdue balance?

**Evidence.** 40 exact duplicates removed, £96,957.26. Original and copy are both marked overdue in every case.

**Status.** open

## Q07: Management accounts (P05, Step 2)

**Question.** In the months listed, the four product-line revenue figures do not add up to total revenue. Which figure is correct, and what caused the difference?

**Evidence.** 4 months: Jun 2023 +£18,500, Mar 2024 -£12,000, Nov 2024 +£9,500, Feb 2025 -£15,000.

**Status.** open

## Q08: Negative invoices (P06, Step 2)

**Question.** What are the negative amounts on invoices marked paid? Are they credit notes recorded without the credit-note status, or sign errors?

**Evidence.** 15 invoices, -£13,843.82 in total. Each is the only billing for its customer, product and month; the months either side carry the same amount as a positive.

**Status.** open

## Q09: Contract dates (P10, Step 2)

**Question.** What event does customers.signup_date record (contract signature, go-live or account creation)? Why are some first invoices dated before it?

**Evidence.** 1,423 invoices for 806 customers are dated 1 to 26 days before signup_date, always in the same calendar month.

**Status.** open

## Q10: Customer attributes (P08, Step 2)

**Question.** Can management supply the industry for customers where it is blank?

**Evidence.** 132 customers have no industry; they are reported as Unknown.

**Status.** open

## Q11: Negative invoices (P06, Step 3)

**Question.** Why were the negative amounts on invoices marked paid left out of reported revenue instead of being corrected? If they are sign errors, will the invoices and the management accounts be restated?

**Evidence.** 15 invoices. Reported revenue excludes them: the cube ties to the product lines in all 48 months only when they are excluded. The months either side of each carry the same amount as a positive, so reported revenue is probably understated by £13,843.82 (2022 £5,788.75, 2023 £2,118.96, 2024 £4,073.48, 2025 £1,862.63).

**Status.** open

## Q12: Management accounts (P05, Step 3)

**Question.** Please provide the journal listing behind the four manual differences between product-line revenue and reported total revenue, showing who posted each entry, when, and why.

**Evidence.** Reported total less the sum of product lines: Jun 2023 -£18,500, Mar 2024 +£12,000, Nov 2024 -£9,500, Feb 2025 +£15,000. The invoice data ties to the product lines in each of these months.

**Status.** open

## Q13: Management accounts (P05, Step 3)

**Question.** What is the policy on manual adjustments to reported revenue, who can approve them, and are they reviewed at month end?

**Evidence.** Four months carry round-number differences between reported total revenue and the sum of the product lines.

**Status.** open

## Q14: Management accounts (P05, Step 3)

**Question.** Which 2025 revenue figure appears in the information memorandum: the reported total or the sum of the product lines?

**Evidence.** 2025 reported total revenue is £45,771,419.35; the sum of the product lines is £45,756,419.35. The February 2025 adjustment adds £15,000 to the reported total.

**Status.** open

## Q15: Price increases (4a, Step 4)

**Question.** Please confirm the price increases applied from January 2024 and January 2025, the contractual basis for them, how customers were notified, and whether a further increase is planned for 2026.

**Evidence.** Every recurring line bills 5% above its contracted price in 2024 and a further 7% in 2025. The subscription table does not record the increases.

**Status.** open

## Q16: Large customers (4b, Step 4)

**Question.** Why did C1052 end Analytics Add-on (ended 2025-09-01) and Payments Module (ended 2025-09-01)? What is the renewal date and status of its remaining contract? Why did C1545 end Payments Module (ended 2025-02-01)? What is the renewal date and status of its remaining contract?

**Evidence.** C1052: December ARR £2.32m in 2024, £1.34m in 2025 (down 42.4%). C1545: December ARR £2.05m in 2024, £1.81m in 2025 (down 11.9%).

**Status.** open

## Q17: Large customers (4b, Step 4)

**Question.** Please provide the contracts for the six customers priced at 10 times list or more, including term, renewal dates, termination and change-of-control clauses.

**Evidence.** They carry 20.8% of 2025 revenue.

**Status.** open

## Q18: Retention (4c, Step 4)

**Question.** What changed in customer acquisition, onboarding or pricing from 2023 that could explain faster churn among newer customers? Please provide churn reasons by customer for 2024 and 2025.

**Evidence.** 12-month logo retention: 78.6% for 2023+ signups against 92.5% for 2017 to 2022 signups; Micro customers 66.1%.

**Status.** open

## Q19: Retention (4g, Step 4)

**Question.** Why do customers acquired through Paid Search and Partner/Reseller churn faster, and what is the acquisition cost of each channel?

**Evidence.** 2025 logo churn: Paid Search 19.5%, Partner/Reseller 19.7%, Direct Sales 8.6%.

**Status.** open

## Q20: Margin (4f, Step 4)

**Question.** Is the Implementation Services cost of delivery for the 2025 projects complete, and is further cost to come on work already billed?

**Evidence.** Implementation cost of delivery rose from £0.80m in 2024 to £3.85m in 2025; margin 27.1%.

**Status.** open

## Q21: Pricing (4f, Step 4)

**Question.** What is the discount policy for large customers, who approves discounts, and are any discounts due to fall away or be renegotiated at renewal?

**Evidence.** Large customers average 22.2% off list; £5.35m given up across all customers in 2025.

**Status.** open
