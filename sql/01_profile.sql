-- 01_profile.sql
-- Profile the raw_* tables before any cleaning. Every result lands in a prof_* table;
-- notebooks/02_data_preparation.ipynb renders them into docs/data_profile.md.
-- Nothing here changes the raw data.
--
-- Data window: January 2022 to December 2025.

-- ---------------------------------------------------------------------------
-- 0. Shared definitions
-- ---------------------------------------------------------------------------

-- Customer-name matching key, used here and again in 02_clean.sql so the profile and
-- the cleaning rule cannot drift apart. Steps, in order:
--   1. trim and collapse repeated spaces
--   2. strip trailing punctuation (. , ; :)
--   3. upper-case
--   4. legal forms: LIMITED -> LTD, GRP -> GROUP, AND -> &, drop full stops in CO./PLC./LTD.
CREATE OR REPLACE MACRO customer_name_key(nm) AS
    trim(regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace(
        upper(regexp_replace(regexp_replace(trim(nm), '\s+', ' ', 'g'), '[.,;:]+$', '')),
        '\bLIMITED\b', 'LTD', 'g'),
        '\bGRP\b', 'GROUP', 'g'),
        '\bAND\b', '&', 'g'),
        '\b(CO|PLC|LTD|LLP)\.', '\1', 'g'),
        '\s+', ' ', 'g'));

CREATE OR REPLACE TEMP MACRO prof_cols(tname) AS TABLE
WITH nn AS (UNPIVOT (SELECT count(COLUMNS(*)) FROM query_table(tname))
                ON COLUMNS(*) INTO NAME column_name VALUE non_null),
     dd AS (UNPIVOT (SELECT count(DISTINCT COLUMNS(*)) FROM query_table(tname))
                ON COLUMNS(*) INTO NAME column_name VALUE distinct_values),
     mn AS (UNPIVOT (SELECT min(COLUMNS(*))::VARCHAR FROM query_table(tname))
                ON COLUMNS(*) INTO NAME column_name VALUE min_value),
     mx AS (UNPIVOT (SELECT max(COLUMNS(*))::VARCHAR FROM query_table(tname))
                ON COLUMNS(*) INTO NAME column_name VALUE max_value),
     rc AS (SELECT count(*) AS row_count FROM query_table(tname))
SELECT tname AS table_name, column_name, row_count,
       row_count - non_null AS null_count, distinct_values, min_value, max_value
FROM nn JOIN dd USING (column_name) JOIN mn USING (column_name) JOIN mx USING (column_name), rc;

-- ---------------------------------------------------------------------------
-- 1. Row counts, nulls, distinct counts, primary keys
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE prof_columns AS
WITH p AS (
    SELECT * FROM prof_cols('raw_customers')
    UNION ALL SELECT * FROM prof_cols('raw_products')
    UNION ALL SELECT * FROM prof_cols('raw_subscriptions')
    UNION ALL SELECT * FROM prof_cols('raw_invoices')
    UNION ALL SELECT * FROM prof_cols('raw_costs')
    UNION ALL SELECT * FROM prof_cols('raw_management_accounts')
)
SELECT p.table_name, c.column_index AS ordinal, p.column_name, c.data_type,
       p.row_count, p.null_count, round(100.0 * p.null_count / p.row_count, 2) AS null_pct,
       p.distinct_values, p.min_value, p.max_value
FROM p
JOIN duckdb_columns() c ON c.table_name = p.table_name AND c.column_name = p.column_name
ORDER BY p.table_name, c.column_index;

CREATE OR REPLACE TABLE prof_primary_keys AS
SELECT * EXCLUDE (ord) FROM (
SELECT 1 AS ord, 'raw_customers' AS table_name, 'customer_id' AS key_columns,
       count(*) AS row_count, count(DISTINCT customer_id) AS distinct_keys,
       count(*) FILTER (WHERE customer_id IS NULL) AS null_keys FROM raw_customers
UNION ALL
SELECT 2, 'raw_products', 'product_id', count(*), count(DISTINCT product_id),
       count(*) FILTER (WHERE product_id IS NULL) FROM raw_products
UNION ALL
SELECT 3, 'raw_subscriptions', 'subscription_id', count(*), count(DISTINCT subscription_id),
       count(*) FILTER (WHERE subscription_id IS NULL) FROM raw_subscriptions
UNION ALL
SELECT 4, 'raw_invoices', 'invoice_id', count(*), count(DISTINCT invoice_id),
       count(*) FILTER (WHERE invoice_id IS NULL) FROM raw_invoices
UNION ALL
SELECT 5, 'raw_costs', 'month, product_line', count(*), count(DISTINCT (month, product_line)),
       count(*) FILTER (WHERE month IS NULL OR product_line IS NULL) FROM raw_costs
UNION ALL
SELECT 6, 'raw_management_accounts', 'month', count(*), count(DISTINCT month),
       count(*) FILTER (WHERE month IS NULL) FROM raw_management_accounts
) ORDER BY ord;

-- ---------------------------------------------------------------------------
-- 2. Date ranges and dates outside the January 2022 to December 2025 window
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE prof_date_ranges AS
WITH d AS (
    SELECT 'raw_customers' AS table_name, 'signup_date' AS column_name, signup_date AS dt FROM raw_customers
    UNION ALL SELECT 'raw_subscriptions', 'start_date', start_date FROM raw_subscriptions
    UNION ALL SELECT 'raw_subscriptions', 'end_date', end_date FROM raw_subscriptions
    UNION ALL SELECT 'raw_invoices', 'invoice_date', invoice_date FROM raw_invoices
    UNION ALL SELECT 'raw_costs', 'month', month FROM raw_costs
    UNION ALL SELECT 'raw_management_accounts', 'month', month FROM raw_management_accounts
)
SELECT table_name, column_name,
       min(dt) AS min_date, max(dt) AS max_date,
       count(*) FILTER (WHERE dt IS NULL) AS null_dates,
       count(*) FILTER (WHERE dt < DATE '2022-01-01') AS before_window,
       count(*) FILTER (WHERE dt > DATE '2025-12-31') AS after_window,
       count(*) FILTER (WHERE dt IS NOT NULL AND day(dt) <> 1) AS not_first_of_month
FROM d
GROUP BY table_name, column_name
ORDER BY table_name, column_name;

-- Invoices dated before the customer's signup date
CREATE OR REPLACE TABLE prof_invoice_before_signup AS
SELECT count(*) AS invoices,
       count(DISTINCT i.customer_id) AS customers,
       sum(i.amount) AS amount,
       min(c.signup_date - i.invoice_date) AS min_days_before,
       median(c.signup_date - i.invoice_date) AS median_days_before,
       max(c.signup_date - i.invoice_date) AS max_days_before,
       count(*) FILTER (WHERE date_trunc('month', i.invoice_date) < date_trunc('month', c.signup_date))
           AS in_earlier_calendar_month
FROM raw_invoices i
JOIN raw_customers c USING (customer_id)
WHERE i.invoice_date < c.signup_date;

-- ---------------------------------------------------------------------------
-- 3. Amount distributions by status and revenue_type
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE prof_amounts AS
SELECT coalesce(status, 'all') AS status,
       coalesce(revenue_type, 'all') AS revenue_type,
       count(*) AS invoices,
       sum(amount) AS total,
       min(amount) AS min_amount,
       quantile_cont(amount, 0.01)::DECIMAL(14,2) AS p01,
       quantile_cont(amount, 0.25)::DECIMAL(14,2) AS p25,
       quantile_cont(amount, 0.50)::DECIMAL(14,2) AS median,
       avg(amount)::DECIMAL(14,2) AS mean,
       quantile_cont(amount, 0.75)::DECIMAL(14,2) AS p75,
       quantile_cont(amount, 0.99)::DECIMAL(14,2) AS p99,
       max(amount) AS max_amount,
       count(*) FILTER (WHERE amount < 0) AS negative_count,
       coalesce(sum(amount) FILTER (WHERE amount < 0), 0) AS negative_total,
       count(*) FILTER (WHERE amount = 0) AS zero_count
FROM raw_invoices
GROUP BY GROUPING SETS ((status, revenue_type), ())
ORDER BY status = 'all', status, revenue_type;

-- Invoice-id prefix against status
CREATE OR REPLACE TABLE prof_invoice_prefix AS
SELECT regexp_extract(invoice_id, '^[A-Z]+') AS id_prefix, status,
       count(*) AS invoices, sum(amount) AS total
FROM raw_invoices
GROUP BY ALL
ORDER BY ALL;

-- Overdue billings by year (a cash-collection point, not a revenue adjustment)
CREATE OR REPLACE TABLE prof_overdue_by_year AS
SELECT year(invoice_date) AS year,
       sum(amount) FILTER (WHERE status <> 'credited') AS gross_billings,
       count(*) FILTER (WHERE status = 'overdue') AS overdue_invoices,
       coalesce(sum(amount) FILTER (WHERE status = 'overdue'), 0) AS overdue_amount,
       round(100.0 * coalesce(sum(amount) FILTER (WHERE status = 'overdue'), 0)
             / sum(amount) FILTER (WHERE status <> 'credited'), 2) AS overdue_pct
FROM raw_invoices
GROUP BY 1
ORDER BY 1;

-- ---------------------------------------------------------------------------
-- 4. Allowed values
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE prof_domain_values AS
WITH v AS (
    SELECT 'raw_invoices' AS table_name, 'status' AS column_name, status AS value FROM raw_invoices
    UNION ALL SELECT 'raw_invoices', 'revenue_type', revenue_type FROM raw_invoices
    UNION ALL SELECT 'raw_products', 'product_line', product_line FROM raw_products
    UNION ALL SELECT 'raw_products', 'revenue_type', revenue_type FROM raw_products
    UNION ALL SELECT 'raw_costs', 'product_line', product_line FROM raw_costs
    UNION ALL SELECT 'raw_customers', 'company_size', company_size FROM raw_customers
    UNION ALL SELECT 'raw_customers', 'region', region FROM raw_customers
    UNION ALL SELECT 'raw_customers', 'acquisition_channel', acquisition_channel FROM raw_customers
    UNION ALL SELECT 'raw_customers', 'industry', industry FROM raw_customers
    UNION ALL SELECT 'raw_customers', 'account_manager', account_manager FROM raw_customers
    UNION ALL SELECT 'raw_subscriptions', 'contract_term_months', contract_term_months::VARCHAR FROM raw_subscriptions
)
SELECT table_name, column_name, coalesce(value, '(null)') AS value, count(*) AS rows
FROM v
GROUP BY ALL
ORDER BY table_name, column_name, rows DESC, value;

-- ---------------------------------------------------------------------------
-- 5. Referential integrity and revenue-type consistency
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE prof_referential_integrity AS
SELECT * EXCLUDE (ord) FROM (
SELECT 1 AS ord, 'invoices.customer_id not in customers' AS check_name, count(*) AS orphan_rows
FROM raw_invoices i WHERE NOT EXISTS (SELECT 1 FROM raw_customers c WHERE c.customer_id = i.customer_id)
UNION ALL
SELECT 2, 'invoices.product_id not in products', count(*)
FROM raw_invoices i WHERE NOT EXISTS (SELECT 1 FROM raw_products p WHERE p.product_id = i.product_id)
UNION ALL
SELECT 3, 'subscriptions.customer_id not in customers', count(*)
FROM raw_subscriptions s WHERE NOT EXISTS (SELECT 1 FROM raw_customers c WHERE c.customer_id = s.customer_id)
UNION ALL
SELECT 4, 'subscriptions.product_id not in products', count(*)
FROM raw_subscriptions s WHERE NOT EXISTS (SELECT 1 FROM raw_products p WHERE p.product_id = s.product_id)
UNION ALL
SELECT 5, 'costs.product_line not in products', count(*)
FROM raw_costs k WHERE NOT EXISTS (SELECT 1 FROM raw_products p WHERE p.product_line = k.product_line)
UNION ALL
SELECT 6, 'customers with no subscription', count(*)
FROM raw_customers c WHERE NOT EXISTS (SELECT 1 FROM raw_subscriptions s WHERE s.customer_id = c.customer_id)
UNION ALL
SELECT 7, 'customers with no invoice in the window', count(*)
FROM raw_customers c WHERE NOT EXISTS (SELECT 1 FROM raw_invoices i WHERE i.customer_id = c.customer_id)
UNION ALL
SELECT 8, 'of which: a subscription line live at any point in the window', count(*)
FROM raw_customers c
WHERE NOT EXISTS (SELECT 1 FROM raw_invoices i WHERE i.customer_id = c.customer_id)
  AND EXISTS (SELECT 1 FROM raw_subscriptions s
              WHERE s.customer_id = c.customer_id
                AND (s.end_date IS NULL OR s.end_date > DATE '2022-01-01'))
) ORDER BY ord;

CREATE OR REPLACE TABLE prof_revenue_type_consistency AS
SELECT i.revenue_type AS invoice_revenue_type, p.revenue_type AS product_revenue_type,
       p.product_line, count(*) AS invoices, sum(i.amount) AS total,
       i.revenue_type = p.revenue_type AS consistent
FROM raw_invoices i
JOIN raw_products p USING (product_id)
GROUP BY ALL
ORDER BY ALL;

-- ---------------------------------------------------------------------------
-- 6. Exact duplicate invoices: identical on every business field except invoice_id
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE prof_duplicate_invoices AS
SELECT customer_id, product_id, invoice_date, amount, revenue_type, status,
       count(*) AS copies,
       list(invoice_id ORDER BY invoice_id) AS invoice_ids,
       (count(*) - 1) * amount AS excess_amount
FROM raw_invoices
GROUP BY customer_id, product_id, invoice_date, amount, revenue_type, status
HAVING count(*) > 1
ORDER BY invoice_date, customer_id, product_id;

CREATE OR REPLACE TABLE prof_duplicate_by_year AS
SELECT year(invoice_date) AS year, status,
       count(*) AS duplicate_groups,
       sum(copies - 1) AS excess_rows,
       sum(excess_amount) AS excess_amount,
       max(amount) AS largest_single_amount
FROM prof_duplicate_invoices
GROUP BY ALL
ORDER BY ALL;

-- Customer x product x month cells carrying more than one billing (excluding credit notes)
CREATE OR REPLACE TABLE prof_multi_billing_cells AS
WITH cells AS (
    SELECT customer_id, product_id, date_trunc('month', invoice_date) AS month_start,
           count(*) AS billings, count(DISTINCT amount) AS distinct_amounts
    FROM raw_invoices
    WHERE status <> 'credited'
    GROUP BY ALL
)
SELECT billings, distinct_amounts, count(*) AS cells
FROM cells
WHERE billings > 1
GROUP BY ALL
ORDER BY ALL;

-- ---------------------------------------------------------------------------
-- 7. Negative amounts and credit notes
-- ---------------------------------------------------------------------------

-- Negative amounts on invoices that are not credit notes, with the same customer and
-- product's billings in the same, previous and next month for context
CREATE OR REPLACE TABLE prof_negative_non_credit AS
SELECT n.invoice_id, n.customer_id, n.product_id, n.invoice_date, n.amount, n.status,
       (SELECT count(*) FROM raw_invoices o
         WHERE o.customer_id = n.customer_id AND o.product_id = n.product_id
           AND o.invoice_id <> n.invoice_id
           AND date_trunc('month', o.invoice_date) = date_trunc('month', n.invoice_date)) AS other_rows_same_month,
       (SELECT sum(o.amount) FROM raw_invoices o
         WHERE o.customer_id = n.customer_id AND o.product_id = n.product_id AND o.status <> 'credited'
           AND date_trunc('month', o.invoice_date) = date_trunc('month', n.invoice_date) - INTERVAL 1 MONTH) AS prior_month_billing,
       (SELECT sum(o.amount) FROM raw_invoices o
         WHERE o.customer_id = n.customer_id AND o.product_id = n.product_id AND o.status <> 'credited'
           AND date_trunc('month', o.invoice_date) = date_trunc('month', n.invoice_date) + INTERVAL 1 MONTH) AS next_month_billing
FROM raw_invoices n
WHERE n.amount < 0 AND n.status <> 'credited'
ORDER BY n.invoice_date;

-- Credit notes: count and value by year, and whether each matches an original invoice
-- on customer, product, date and absolute amount
CREATE OR REPLACE TABLE prof_credit_notes AS
SELECT year(cn.invoice_date) AS year,
       count(*) AS credit_notes,
       sum(cn.amount) AS credit_total,
       count(*) FILTER (WHERE EXISTS (
           SELECT 1 FROM raw_invoices o
           WHERE o.status <> 'credited' AND o.customer_id = cn.customer_id
             AND o.product_id = cn.product_id AND o.invoice_date = cn.invoice_date
             AND o.amount = -cn.amount)) AS matched_to_original,
       count(*) FILTER (WHERE cn.amount >= 0) AS non_negative_credit_notes
FROM raw_invoices cn
WHERE cn.status = 'credited'
GROUP BY 1
ORDER BY 1;

-- ---------------------------------------------------------------------------
-- 8. Outliers
-- Rule A (product level): positive, non-credited invoices above Q3 + 3 x IQR of all
--   positive, non-credited invoices for the same product (Tukey's "far out" fence).
-- Rule B (customer level): an invoice more than 3x, or less than one third of, the
--   median of the same customer's invoices for the same product (recurring products
--   only; a customer normally has a single implementation invoice).
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE prof_outlier_fences AS
WITH pos AS (
    SELECT * FROM raw_invoices WHERE status <> 'credited' AND amount > 0
),
f AS (
    SELECT product_id,
           quantile_cont(amount, 0.25) AS q1,
           median(amount) AS median_amount,
           quantile_cont(amount, 0.75) AS q3,
           count(*) AS invoices
    FROM pos GROUP BY 1
)
SELECT f.product_id, p.product_name, p.list_price, f.invoices,
       f.q1::DECIMAL(14,2) AS q1, f.median_amount::DECIMAL(14,2) AS median_amount, f.q3::DECIMAL(14,2) AS q3,
       (f.q3 + 3 * (f.q3 - f.q1))::DECIMAL(14,2) AS upper_fence,
       count(pos.invoice_id) FILTER (WHERE pos.amount > f.q3 + 3 * (f.q3 - f.q1)) AS invoices_above,
       coalesce(sum(pos.amount) FILTER (WHERE pos.amount > f.q3 + 3 * (f.q3 - f.q1)), 0) AS amount_above,
       count(DISTINCT pos.customer_id) FILTER (WHERE pos.amount > f.q3 + 3 * (f.q3 - f.q1)) AS customers_above
FROM f
JOIN raw_products p USING (product_id)
LEFT JOIN pos USING (product_id)
GROUP BY ALL
ORDER BY f.product_id;

-- Recurring customer x product lines with any invoice above the Rule A fence
CREATE OR REPLACE TABLE prof_outlier_recurring_lines AS
WITH pos AS (
    SELECT * FROM raw_invoices WHERE status <> 'credited' AND amount > 0
)
SELECT pos.customer_id, pos.product_id, f.list_price, f.upper_fence,
       count(*) AS invoices,
       count(*) FILTER (WHERE pos.amount > f.upper_fence) AS invoices_above_fence,
       min(pos.amount) AS min_amount, median(pos.amount)::DECIMAL(14,2) AS median_amount, max(pos.amount) AS max_amount,
       round(median(pos.amount) / f.list_price, 1) AS median_multiple_of_list,
       sum(pos.amount) AS total
FROM pos
JOIN prof_outlier_fences f USING (product_id)
JOIN raw_products p USING (product_id)
WHERE p.revenue_type = 'recurring'
GROUP BY pos.customer_id, pos.product_id, f.list_price, f.upper_fence
HAVING count(*) FILTER (WHERE pos.amount > f.upper_fence) > 0
ORDER BY total DESC, pos.customer_id, pos.product_id;

CREATE OR REPLACE TABLE prof_outlier_within_customer AS
WITH pos AS (
    SELECT i.* FROM raw_invoices i JOIN raw_products p USING (product_id)
    WHERE i.status <> 'credited' AND i.amount > 0 AND p.revenue_type = 'recurring'
),
m AS (
    SELECT customer_id, product_id, median(amount) AS med FROM pos GROUP BY ALL
)
SELECT pos.*, m.med::DECIMAL(14,2) AS customer_product_median, round(pos.amount / m.med, 2) AS ratio
FROM pos JOIN m USING (customer_id, product_id)
WHERE pos.amount > 3 * m.med OR pos.amount < m.med / 3
ORDER BY ratio DESC;

-- Implementation Services invoices: timing relative to the customer's signup month
CREATE OR REPLACE TABLE prof_implementation_timing AS
SELECT year(i.invoice_date) AS year,
       date_trunc('month', i.invoice_date) = date_trunc('month', c.signup_date) AS in_signup_month,
       count(*) AS invoices,
       count(DISTINCT i.customer_id) AS customers,
       sum(i.amount) AS total,
       min(i.amount) AS min_amount,
       median(i.amount)::DECIMAL(14,2) AS median_amount,
       max(i.amount) AS max_amount,
       count(*) FILTER (WHERE i.amount > f.upper_fence) AS above_rule_a_fence,
       min(i.invoice_id) AS first_invoice_id,
       max(i.invoice_id) AS last_invoice_id
FROM raw_invoices i
JOIN raw_customers c USING (customer_id)
JOIN prof_outlier_fences f USING (product_id)
WHERE i.product_id = '6' AND i.status <> 'credited'
GROUP BY ALL
ORDER BY ALL;

CREATE OR REPLACE TABLE prof_implementation_off_cycle AS
SELECT i.invoice_id, i.customer_id, c.signup_date, year(c.signup_date) AS signup_year,
       i.invoice_date, i.amount, i.status,
       EXISTS (SELECT 1 FROM raw_invoices r
               WHERE r.customer_id = i.customer_id AND r.product_id <> '6'
                 AND date_trunc('month', r.invoice_date) = date_trunc('month', i.invoice_date)) AS recurring_billing_same_month,
       (SELECT count(*) FROM raw_invoices o
         WHERE o.customer_id = i.customer_id AND o.product_id = '6' AND o.invoice_id <> i.invoice_id) AS other_implementation_invoices
FROM raw_invoices i
JOIN raw_customers c USING (customer_id)
WHERE i.product_id = '6'
  AND date_trunc('month', i.invoice_date) <> date_trunc('month', c.signup_date)
ORDER BY i.invoice_id;

-- ---------------------------------------------------------------------------
-- 9. Subscriptions
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE prof_subscription_checks AS
SELECT * EXCLUDE (ord) FROM (
SELECT 1 AS ord, 'contract lines' AS metric, count(*)::DOUBLE AS value FROM raw_subscriptions
UNION ALL SELECT 2, 'start_date after end_date', count(*) FILTER (WHERE end_date < start_date) FROM raw_subscriptions
UNION ALL SELECT 3, 'start_date equal to end_date', count(*) FILTER (WHERE end_date = start_date) FROM raw_subscriptions
UNION ALL SELECT 4, 'active (blank end_date)', count(*) FILTER (WHERE end_date IS NULL) FROM raw_subscriptions
UNION ALL SELECT 5, 'active share %', round(100.0 * count(*) FILTER (WHERE end_date IS NULL) / count(*), 1) FROM raw_subscriptions
UNION ALL SELECT 6, 'ended', count(*) FILTER (WHERE end_date IS NOT NULL) FROM raw_subscriptions
UNION ALL SELECT 7, 'ended before the window (end_date <= 2022-01-01)', count(*) FILTER (WHERE end_date <= DATE '2022-01-01') FROM raw_subscriptions
UNION ALL SELECT 8, 'end_date not on the 1st of a month', count(*) FILTER (WHERE end_date IS NOT NULL AND day(end_date) <> 1) FROM raw_subscriptions
UNION ALL SELECT 9, 'customer x product with more than one active line',
    (SELECT count(*) FROM (SELECT customer_id, product_id FROM raw_subscriptions WHERE end_date IS NULL GROUP BY ALL HAVING count(*) > 1))
UNION ALL SELECT 10, 'lines starting before the customer signup_date',
    (SELECT count(*) FROM raw_subscriptions s JOIN raw_customers c USING (customer_id) WHERE s.start_date < c.signup_date)
UNION ALL SELECT 11, 'recurring invoice months not covered by any subscription line',
    (SELECT count(*) FROM (
        SELECT DISTINCT i.customer_id, i.product_id, date_trunc('month', i.invoice_date) AS m
        FROM raw_invoices i JOIN raw_products p USING (product_id)
        WHERE p.revenue_type = 'recurring' AND i.status <> 'credited') inv
     WHERE NOT EXISTS (
        SELECT 1 FROM raw_subscriptions s
        WHERE s.customer_id = inv.customer_id AND s.product_id = inv.product_id
          AND date_trunc('month', s.start_date) <= inv.m
          AND (s.end_date IS NULL OR s.end_date > inv.m)))
) ORDER BY ord;

CREATE OR REPLACE TABLE prof_subscription_terms AS
SELECT contract_term_months, count(*) AS lines,
       count(*) FILTER (WHERE end_date IS NULL) AS active_lines,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS share_pct
FROM raw_subscriptions
GROUP BY 1
ORDER BY 1;

CREATE OR REPLACE TABLE prof_subscription_prices AS
SELECT s.product_id, p.product_name, p.list_price, count(*) AS lines,
       min(s.monthly_price) AS min_price, median(s.monthly_price)::DECIMAL(14,2) AS median_price,
       max(s.monthly_price) AS max_price,
       min(s.discount_pct) AS min_discount, median(s.discount_pct)::DECIMAL(8,4) AS median_discount,
       max(s.discount_pct) AS max_discount
FROM raw_subscriptions s
JOIN raw_products p USING (product_id)
GROUP BY ALL
ORDER BY s.product_id;

-- ---------------------------------------------------------------------------
-- 10. Management accounts: internal consistency
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE prof_mgmt_consistency AS
SELECT month,
       revenue_core_platform + revenue_analytics_addon + revenue_payments_module
           + revenue_implementation_services AS sum_of_lines,
       total_revenue,
       revenue_core_platform + revenue_analytics_addon + revenue_payments_module
           + revenue_implementation_services - total_revenue AS lines_less_total,
       total_revenue - cost_of_sales - gross_profit AS gp_arithmetic_diff,
       round(gross_profit / total_revenue, 4) - gross_margin_pct AS margin_pct_diff
FROM raw_management_accounts
ORDER BY month;

-- ---------------------------------------------------------------------------
-- 11. Costs: completeness, component arithmetic, tie to management cost_of_sales
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE prof_costs_completeness AS
WITH grid AS (
    SELECT m.month, l.product_line
    FROM (SELECT DISTINCT month FROM raw_management_accounts) m
    CROSS JOIN (SELECT DISTINCT product_line FROM raw_products) l
)
SELECT count(*) AS expected_cells,
       count(k.month) AS present_cells,
       count(*) - count(k.month) AS missing_cells,
       (SELECT count(*) FROM raw_costs) AS cost_rows,
       (SELECT count(*) FROM raw_costs
         WHERE abs(hosting_cost + support_staff_cost + third_party_licence_cost - total_cost_of_delivery) > 0.01)
           AS component_mismatches_over_1p,
       (SELECT sum(hosting_cost + support_staff_cost + third_party_licence_cost - total_cost_of_delivery)
          FROM raw_costs) AS component_less_total
FROM grid
LEFT JOIN raw_costs k USING (month, product_line);

CREATE OR REPLACE TABLE prof_costs_vs_cos AS
SELECT m.month, k.cost_of_delivery, m.cost_of_sales,
       k.cost_of_delivery - m.cost_of_sales AS difference
FROM raw_management_accounts m
LEFT JOIN (SELECT month, sum(total_cost_of_delivery) AS cost_of_delivery FROM raw_costs GROUP BY 1) k USING (month)
ORDER BY m.month;

-- ---------------------------------------------------------------------------
-- 12. Customer names and missing attributes
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE prof_name_formats AS
SELECT * EXCLUDE (ord) FROM (
SELECT 1 AS ord, 'leading or trailing spaces' AS pattern, count(*) FILTER (WHERE customer_name <> trim(customer_name)) AS customers FROM raw_customers
UNION ALL SELECT 2, 'double spaces', count(*) FILTER (WHERE customer_name LIKE '%  %') FROM raw_customers
UNION ALL SELECT 3, 'trailing punctuation', count(*) FILTER (WHERE regexp_matches(customer_name, '[.,;:]$')) FROM raw_customers
UNION ALL SELECT 4, 'all upper case', count(*) FILTER (WHERE customer_name = upper(customer_name)) FROM raw_customers
UNION ALL SELECT 5, 'all lower case', count(*) FILTER (WHERE customer_name = lower(customer_name)) FROM raw_customers
UNION ALL SELECT 6, 'ends "Ltd"', count(*) FILTER (WHERE regexp_matches(customer_name, '\bLtd\.?$')) FROM raw_customers
UNION ALL SELECT 7, 'ends "Limited"', count(*) FILTER (WHERE regexp_matches(customer_name, '\bLimited\.?$')) FROM raw_customers
UNION ALL SELECT 8, 'ends "PLC"', count(*) FILTER (WHERE regexp_matches(customer_name, '\bPLC\.?$')) FROM raw_customers
UNION ALL SELECT 9, 'ends "LLP"', count(*) FILTER (WHERE regexp_matches(customer_name, '\bLLP\.?$')) FROM raw_customers
UNION ALL SELECT 10, 'ends "& Co"', count(*) FILTER (WHERE regexp_matches(customer_name, '& Co\.?$')) FROM raw_customers
UNION ALL SELECT 11, 'ends "and Co"', count(*) FILTER (WHERE regexp_matches(customer_name, '\band Co\.?$')) FROM raw_customers
UNION ALL SELECT 12, 'contains "Grp"', count(*) FILTER (WHERE regexp_matches(customer_name, '\bGrp\b')) FROM raw_customers
UNION ALL SELECT 13, 'contains " and "', count(*) FILTER (WHERE regexp_matches(customer_name, '\band\b')) FROM raw_customers
) ORDER BY ord;

CREATE OR REPLACE TABLE prof_name_irregular AS
SELECT customer_id, customer_name, customer_name_key(customer_name) AS name_key,
       (SELECT count(*) FROM raw_customers o
         WHERE customer_name_key(o.customer_name) = customer_name_key(c.customer_name)
           AND o.customer_id <> c.customer_id) AS other_ids_with_same_key
FROM raw_customers c
WHERE regexp_matches(customer_name, '[.,;:]$')
   OR regexp_matches(customer_name, '\band\b')
   OR regexp_matches(customer_name, '\bGrp\b')
   OR customer_name <> trim(customer_name)
   OR customer_name LIKE '%  %'
ORDER BY customer_id;

-- Pairs of different customer_ids that share a name once the key is applied, with
-- their attributes side by side
CREATE OR REPLACE TABLE prof_name_shared_pairs AS
WITH k AS (SELECT *, customer_name_key(customer_name) AS name_key FROM raw_customers),
life AS (
    SELECT customer_id, min(start_date) AS first_start,
           max(coalesce(end_date, DATE '2099-12-31')) AS last_end
    FROM raw_subscriptions GROUP BY 1
)
SELECT a.name_key,
       a.customer_id AS id_a, a.customer_name AS name_a, b.customer_id AS id_b, b.customer_name AS name_b,
       a.signup_date AS signup_a, b.signup_date AS signup_b,
       a.region = b.region AS same_region,
       a.company_size = b.company_size AS same_size,
       a.industry IS NOT DISTINCT FROM b.industry AS same_industry,
       a.acquisition_channel = b.acquisition_channel AS same_channel,
       a.account_manager = b.account_manager AS same_account_manager,
       la.first_start <= lb.last_end AND lb.first_start <= la.last_end AS subscriptions_overlap
FROM k a
JOIN k b ON a.name_key = b.name_key AND a.customer_id < b.customer_id
JOIN life la ON la.customer_id = a.customer_id
JOIN life lb ON lb.customer_id = b.customer_id
ORDER BY a.name_key;

-- How often shared-name pairs agree on each attribute, against the rate two customers
-- picked at random would agree (sum of squared category shares)
CREATE OR REPLACE TABLE prof_name_shared_summary AS
WITH chance AS (
    SELECT 'region' AS attribute, sum(power(n / tot, 2)) AS random_pair_rate
      FROM (SELECT count(*)::DOUBLE AS n, sum(count(*)) OVER ()::DOUBLE AS tot FROM raw_customers GROUP BY region)
    UNION ALL SELECT 'company_size', sum(power(n / tot, 2))
      FROM (SELECT count(*)::DOUBLE AS n, sum(count(*)) OVER ()::DOUBLE AS tot FROM raw_customers GROUP BY company_size)
    UNION ALL SELECT 'industry', sum(power(n / tot, 2))
      FROM (SELECT count(*)::DOUBLE AS n, sum(count(*)) OVER ()::DOUBLE AS tot FROM raw_customers GROUP BY industry)
    UNION ALL SELECT 'acquisition_channel', sum(power(n / tot, 2))
      FROM (SELECT count(*)::DOUBLE AS n, sum(count(*)) OVER ()::DOUBLE AS tot FROM raw_customers GROUP BY acquisition_channel)
    UNION ALL SELECT 'account_manager', sum(power(n / tot, 2))
      FROM (SELECT count(*)::DOUBLE AS n, sum(count(*)) OVER ()::DOUBLE AS tot FROM raw_customers GROUP BY account_manager)
),
pairs AS (
    SELECT 'region' AS attribute, avg(same_region::INT) AS shared_name_rate FROM prof_name_shared_pairs
    UNION ALL SELECT 'company_size', avg(same_size::INT) FROM prof_name_shared_pairs
    UNION ALL SELECT 'industry', avg(same_industry::INT) FROM prof_name_shared_pairs
    UNION ALL SELECT 'acquisition_channel', avg(same_channel::INT) FROM prof_name_shared_pairs
    UNION ALL SELECT 'account_manager', avg(same_account_manager::INT) FROM prof_name_shared_pairs
)
SELECT attribute,
       (SELECT count(*) FROM prof_name_shared_pairs) AS pairs,
       round(100 * shared_name_rate, 1) AS shared_name_pairs_agree_pct,
       round(100 * random_pair_rate, 1) AS random_pairs_agree_pct
FROM pairs JOIN chance USING (attribute)
ORDER BY attribute;

CREATE OR REPLACE TABLE prof_missing_industry AS
SELECT count(*) AS customers,
       count(*) FILTER (WHERE EXISTS (SELECT 1 FROM raw_invoices i WHERE i.customer_id = c.customer_id)) AS with_invoices,
       (SELECT coalesce(sum(i.amount), 0) FROM raw_invoices i
         JOIN raw_customers c2 USING (customer_id) WHERE c2.industry IS NULL) AS invoiced_amount,
       round(100.0 * (SELECT coalesce(sum(i.amount), 0) FROM raw_invoices i
         JOIN raw_customers c2 USING (customer_id) WHERE c2.industry IS NULL)
         / (SELECT sum(amount) FROM raw_invoices), 2) AS share_of_invoiced_pct
FROM raw_customers c
WHERE c.industry IS NULL;

-- ---------------------------------------------------------------------------
-- 13. Issue register: every finding above with the rows and £ it touches, by year.
-- touches = 'amount' when adjusting the item would change revenue totals, and
-- 'attribute' when it affects classification, timing or cash but not revenue totals.
-- gross_abs is the sum of absolute values, the most the item could move revenue.
-- This orders the list for review. It is not a judgement on treatment.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE prof_issues AS
WITH shared_ids AS (
    SELECT id_a AS customer_id FROM prof_name_shared_pairs
    UNION SELECT id_b FROM prof_name_shared_pairs
),
items AS (
    SELECT 'P01' AS issue_id, 'amount' AS touches, 'invoices' AS table_name,
           'Recurring invoices above the product-level outlier fence (Rule A)' AS issue,
           i.invoice_date AS dt, i.amount
    FROM raw_invoices i
    JOIN prof_outlier_fences f USING (product_id)
    JOIN raw_products p USING (product_id)
    WHERE p.revenue_type = 'recurring' AND i.status <> 'credited' AND i.amount > f.upper_fence
    UNION ALL
    SELECT 'P02', 'amount', 'invoices',
           'Implementation Services invoices billed outside the customer''s signup month',
           i.invoice_date, i.amount
    FROM raw_invoices i JOIN raw_customers c USING (customer_id)
    WHERE i.product_id = '6' AND date_trunc('month', i.invoice_date) <> date_trunc('month', c.signup_date)
    UNION ALL
    SELECT 'P03', 'amount', 'invoices', 'Credit notes (status credited)', invoice_date, amount
    FROM raw_invoices WHERE status = 'credited'
    UNION ALL
    SELECT 'P04', 'amount', 'invoices', 'Exact duplicate invoices (excess copies only)', invoice_date, amount
    FROM (SELECT *, row_number() OVER (PARTITION BY customer_id, product_id, invoice_date, amount, revenue_type, status
                                       ORDER BY invoice_id) AS rn FROM raw_invoices)
    WHERE rn > 1
    UNION ALL
    SELECT 'P05', 'amount', 'management_accounts',
           'Product-line revenue does not sum to total_revenue', month, lines_less_total
    FROM prof_mgmt_consistency WHERE abs(lines_less_total) > 0.005
    UNION ALL
    SELECT 'P06', 'amount', 'invoices', 'Negative amounts on invoices marked paid or overdue', invoice_date, amount
    FROM raw_invoices WHERE amount < 0 AND status <> 'credited'
    UNION ALL
    SELECT 'P07', 'attribute', 'customers',
           'Customer IDs that share a name once legal forms are normalised (their invoices)',
           i.invoice_date, i.amount
    FROM raw_invoices i JOIN shared_ids USING (customer_id)
    UNION ALL
    SELECT 'P08', 'attribute', 'customers', 'Customers with missing industry (their invoices)', i.invoice_date, i.amount
    FROM raw_invoices i JOIN raw_customers c USING (customer_id) WHERE c.industry IS NULL
    UNION ALL
    SELECT 'P09', 'attribute', 'invoices', 'Invoices with status overdue', invoice_date, amount
    FROM raw_invoices WHERE status = 'overdue'
    UNION ALL
    SELECT 'P10', 'attribute', 'invoices', 'Invoices dated before the customer''s signup_date',
           i.invoice_date, i.amount
    FROM raw_invoices i JOIN raw_customers c USING (customer_id) WHERE i.invoice_date < c.signup_date
    UNION ALL
    SELECT 'P11', 'attribute', 'customers',
           'Customer names with trailing punctuation or "and" for "&" (their invoices)', i.invoice_date, i.amount
    FROM raw_invoices i JOIN prof_name_irregular USING (customer_id)
)
SELECT issue_id, touches, table_name, issue,
       count(*) AS rows_affected,
       sum(amount) AS amount_net,
       sum(abs(amount)) AS amount_gross_abs,
       coalesce(sum(amount) FILTER (WHERE year(dt) = 2022), 0) AS net_2022,
       coalesce(sum(amount) FILTER (WHERE year(dt) = 2023), 0) AS net_2023,
       coalesce(sum(amount) FILTER (WHERE year(dt) = 2024), 0) AS net_2024,
       coalesce(sum(amount) FILTER (WHERE year(dt) = 2025), 0) AS net_2025
FROM items
GROUP BY ALL
ORDER BY touches, sum(abs(amount)) DESC;
