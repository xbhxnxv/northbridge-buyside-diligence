# Rebuilding Step 2 in Alteryx Designer

This describes how to rebuild the SQL pipeline for Steps 2.1 to 2.4 as one Alteryx workflow. Each tool container mirrors one SQL file, and the check totals at the end of this page are what each container should produce. If the Alteryx output matches these totals, it matches the SQL cube.

Conventions: one Input Data tool per CSV, Browse tools after every check, and a Message tool (or a Test tool) wherever a check must be exactly zero.

## Container 1: Load (`sql/00_load.sql`)

1. **Input Data** × 6: `customers.csv`, `products.csv`, `subscriptions.csv`, `invoices.csv`, `costs.csv` and `management_accounts.csv`. Set "First row contains field names" and read every field as V_String, so nothing is converted before you choose the type.
2. **Select** after each input to set types explicitly. Use Date for all date fields and FixedDecimal 14.2 for money. Use FixedDecimal 8.4 for `discount_pct` and `gross_margin_pct`, Int32 for `contract_term_months` and V_String for all ids. Rename `revenue_analytics_add-on` to `revenue_analytics_addon`.
3. **Filter** on each typed stream for `IsNull([date field])`, excluding `end_date`. The True side must be empty. A non-empty True side means a value failed to convert.
4. **Summarize** each stream to Count and to Sum of the money fields. Compare with the Load check totals below.

## Container 2: Profile (`sql/01_profile.sql`)

1. **Unique** on each primary key: `customer_id`, `product_id`, `subscription_id`, `invoice_id`, `month` + `product_line` for costs and `month` for the management accounts. The Duplicates output must be empty.
2. **Join** invoices to customers on `customer_id` and to products on `product_id`. The Left and Right unjoined outputs show orphans; the Left side must be empty. Do the same for subscriptions.
3. **Formula** `[revenue_type] = [Right_revenue_type]` on the invoice-product join to check revenue types agree.
4. **Summarize** invoices grouped by `status` and `revenue_type`: Count, Sum, Min, Max, Avg and Percentile (25, 50, 75) of `amount`. Add a Filter `[amount] < 0` for the negative counts.
5. **Duplicates:** Summarize invoices grouped by customer_id, product_id, invoice_date, amount, revenue_type and status with Count, then Filter `Count > 1`.
6. **Negative non-credit:** Filter `[amount] < 0 AND [status] != "credited"`.
7. **Credit-note matching:** Filter status = credited, Formula `abs_amount = -[amount]`, then Join to the non-credited invoices on customer_id, product_id, invoice_date and `abs_amount = amount`. Unmatched credit notes (the Left output) must be empty.
8. **Outliers:** Summarize positive non-credited invoices by `product_id` for Percentile 25 and 75, Formula `fence = [Q3] + 3*([Q3]-[Q1])`, Join back, then Filter `[amount] > [fence]`.
9. **Management accounts:** Formula `lines_less_total = [revenue_core_platform]+[revenue_analytics_addon]+[revenue_payments_module]+[revenue_implementation_services]-[total_revenue]`, then Filter `ABS([lines_less_total]) > 0.005`.
10. **Costs:** Summarize costs by month (Sum of `total_cost_of_delivery`), Join to the management accounts on month, and Formula for the difference.
11. **Names:** see container 3, step 4.

## Container 3: Clean (`sql/02_clean.sql`)

1. **Duplicates (A01):** Sort invoices by `invoice_id` ascending, then **Unique** on customer_id, product_id, invoice_date, amount, revenue_type and status. The Unique output is `clean_invoices` before the other steps. The Duplicates output is the 40 removed copies; send it to an Output Data tool as the removal list.
2. **Credit-note link (A03):** as in container 2, step 7. Join the matched original `invoice_id` back as `credit_note_original_id`, and join in the reverse direction for `credited_by_id`. Use a Union to bring matched and unmatched rows back together.
3. **Invoice flags (A02, A07, A09):** one Formula tool with these fields:
   - `month_start = DateTimeTrim([invoice_date], "month")`
   - `anomaly_flag = [amount] < 0 AND [status] != "credited"`
   - `amount_flipped = IIF([anomaly_flag], -[amount], [amount])`
   - `amount_excluded = IIF([anomaly_flag], 0, [amount])`
   - `oneoff_category = IIF([revenue_type] = "one-off", IIF(DateTimeTrim([invoice_date],"month") = DateTimeTrim([signup_date],"month"), "signup_implementation", "other_implementation"), Null())`. This needs a Join to customers first, for `signup_date`.
   - `before_signup_flag = [invoice_date] < [signup_date]`
4. **Customer names (A05, A06):** Data Cleansing (remove leading and trailing whitespace, and replace duplicate whitespace), then **Find Replace** or a Formula with `REGEX_Replace` to strip trailing punctuation and map Limited to Ltd, Grp to Group and "and" to "&". Build `name_key` with `Uppercase()`. Summarize by `name_key` with Count and join the count back: `name_collision_flag = [Count] > 1`. Fuzzy Match (match style: Company Name) is a useful second pass to review near-matches, but it must not merge ids.
5. **Missing industry (A04):** Formula `industry_missing_flag = IsNull([industry])`, `industry = IIF(IsNull([industry]), "Unknown", [industry])`.
6. **Customer derived fields and large accounts (A10):** Formula for `signup_month`, `signup_year`, `signup_quarter = ToString(DateTimeYear([signup_date])) + "Q" + ToString(Ceil(DateTimeMonth([signup_date])/3))` and `tenure_months_at_dec_2025 = DateTimeDiff("2025-12-01", [signup_month], "months")`. For `is_large_account`, join subscriptions to products, use Formula `[monthly_price] >= 10*[list_price]`, then Summarize by customer with Max.
7. **Management accounts (A08):** Formula for `revenue_sum_of_lines`, `lines_less_total` and `lines_total_mismatch_flag`.

## Container 4: Revenue cube (`sql/03_revenue_cube.sql`)

1. **Text Input** holding one field, `anomaly_treatment`, with the value `as_reported` (the workflow's equivalent of `cfg_settings`). Append Fields adds it to every invoice row. A Formula `amt = Switch([anomaly_treatment], [amount], "flipped", [amount_flipped], "excluded", [amount_excluded])` then picks the amount.
2. **Formula** helper columns: `gross = IIF([is_credit_note], 0, [amt])`, `credit = IIF([is_credit_note], [amt], 0)`, `recurring = IIF([revenue_type]="recurring", [amt], 0)` and so on for one-off, the two one-off categories, anomaly and overdue.
3. **Summarize** grouped by customer_id, product_id and month_start: Sum of each helper, Count of non-credit rows and Count of credit rows. This is `fact_revenue_monthly`.
4. **MRR:** Filter `[revenue_type] = "recurring" AND NOT [is_credit_note]`, Summarize the same grain with Sum of `amt`, then Filter `[mrr] != 0`. This is `fact_mrr_monthly`.
5. **Dimensions:** `dim_customer` is the container 3 customer stream. `dim_product` is products. `dim_date` is a Generate Rows tool from 2022-01-01 to 2025-12-01 stepping one month, with a Formula for year, quarter, month number and the year-end flag.
6. **Cross Tab** of `fact_revenue_monthly`: Sum of `net_revenue` with year as columns, to compare with the check totals.
7. **Output Data** × 5 to CSV, matching `data/clean/`.

## Check totals

Every value below is taken from the SQL pipeline on each run.

<!-- BEGIN GENERATED: check_totals -->
### Container 1: Load

| stream | row_count | amount_total |
| --- | ---: | ---: |
| raw_customers | 2,192 |  |
| raw_products | 6 |  |
| raw_subscriptions | 3,502 | £4,235,007.42 |
| raw_invoices | 92,732 | £143,523,452.89 |
| raw_costs | 192 | £33,928,247.76 |
| raw_management_accounts | 48 | £143,439,339.45 |

### Container 2: Profile

| check_name | value |
| --- | ---: |
| duplicate primary keys (all tables) | 0 |
| orphan ids in invoices and subscriptions | 0 |
| exact duplicate groups | 40 |
| negative non-credit invoices | 15 |
| credit notes unmatched | 0 |
| recurring invoices above the Rule A fence | 780 |
| management months where lines do not add up | 4 |
| months where costs do not equal cost_of_sales | 0 |

### Container 3: Clean

| check_name | value |
| --- | ---: |
| clean_invoices rows | 92,692 |
| clean_invoices amount total | 143,426,495.63 |
| removed duplicate rows | 40 |
| removed duplicate amount | 96,957.26 |
| credit notes linked to an original | 1,084 |
| anomaly_flag rows | 15 |
| other_implementation rows | 45 |
| other_implementation amount | 4,076,574.31 |
| before_signup_flag rows | 1,423 |
| customers with industry Unknown | 132 |
| customers with name_collision_flag | 458 |
| customers with is_large_account | 6 |
| management months flagged | 4 |

### Container 4: Revenue cube (anomaly setting as_reported)

| table_name | row_count |
| --- | ---: |
| fact_revenue_monthly | 91,608 |
| fact_mrr_monthly | 90,388 |
| dim_customer | 2,192 |
| dim_product | 6 |
| dim_date | 48 |

| year | gross_billings | credit_notes | net_revenue | recurring_net | oneoff_net | mrr_total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022 | £28,555,567.47 | (£329,204.58) | £28,226,362.89 | £27,242,503.30 | £983,859.59 | £27,571,707.88 |
| 2023 | £32,467,804.68 | (£277,053.69) | £32,190,750.99 | £31,012,547.19 | £1,178,203.80 | £31,289,600.88 |
| 2024 | £37,576,199.35 | (£321,374.32) | £37,254,825.03 | £36,110,610.21 | £1,144,214.82 | £36,431,984.53 |
| 2025 | £46,163,393.20 | (£408,836.48) | £45,754,556.72 | £40,473,234.52 | £5,281,322.20 | £40,882,071.00 |
<!-- END GENERATED: check_totals -->
