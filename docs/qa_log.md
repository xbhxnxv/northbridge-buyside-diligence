# Q&A log

Questions for management raised by the data. Generated from the `qa_log` table, which each step's SQL appends to. The evidence is built from the tables on every run. Do not edit by hand.

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
