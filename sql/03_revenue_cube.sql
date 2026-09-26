-- 03_revenue_cube.sql
-- Revenue cube and dimensions, exported to data/clean/ as CSV.
--
-- The P06 anomaly treatment is a single setting in cfg_settings:
--   as_reported  keep the negative amounts as supplied (default until Step 3 decides)
--   flipped      reverse their sign
--   excluded     treat them as zero
-- revenue_cube(t) and mrr_cube(t) build the facts for any treatment, so Step 3 and the
-- tests can compare options without rebuilding anything.

CREATE OR REPLACE TABLE cfg_settings AS
SELECT 'as_reported' AS anomaly_treatment;

CREATE OR REPLACE MACRO invoice_amount(t, as_reported, flipped, excluded) AS
    CASE t WHEN 'as_reported' THEN as_reported
           WHEN 'flipped' THEN flipped
           WHEN 'excluded' THEN excluded
           ELSE error('unknown anomaly_treatment: ' || t) END;

-- One row per customer x product x month with any billing or credit.
CREATE OR REPLACE MACRO revenue_cube(t) AS TABLE
WITH inv AS (
    SELECT *, invoice_amount(t, amount_as_reported, amount_flipped, amount_excluded) AS amt
    FROM clean_invoices
)
SELECT customer_id,
       product_id,
       month_start,
       any_value(product_line) AS product_line,
       any_value(revenue_type) AS revenue_type,
       sum(amt) FILTER (WHERE NOT is_credit_note)::DECIMAL(14,2) AS gross_billings,
       coalesce(sum(amt) FILTER (WHERE is_credit_note), 0)::DECIMAL(14,2) AS credit_notes,
       coalesce(sum(amt), 0)::DECIMAL(14,2) AS net_revenue,
       coalesce(sum(amt) FILTER (WHERE revenue_type = 'recurring'), 0)::DECIMAL(14,2) AS recurring_net,
       coalesce(sum(amt) FILTER (WHERE revenue_type = 'one-off'), 0)::DECIMAL(14,2) AS oneoff_net,
       coalesce(sum(amt) FILTER (WHERE oneoff_category = 'signup_implementation'), 0)::DECIMAL(14,2) AS oneoff_signup_net,
       coalesce(sum(amt) FILTER (WHERE oneoff_category = 'other_implementation'), 0)::DECIMAL(14,2) AS oneoff_other_net,
       coalesce(sum(amt) FILTER (WHERE anomaly_flag), 0)::DECIMAL(14,2) AS anomaly_amount,
       coalesce(sum(amt) FILTER (WHERE is_overdue), 0)::DECIMAL(14,2) AS overdue_amount,
       count(*) FILTER (WHERE NOT is_credit_note) AS invoice_count,
       count(*) FILTER (WHERE is_credit_note) AS credit_note_count
FROM inv
GROUP BY customer_id, product_id, month_start;

-- MRR basis: recurring billings before credit notes. Credit notes are service
-- concessions; netting them in would make a customer look as if it churned or
-- contracted in the month of a concession. Rows with zero MRR are dropped.
CREATE OR REPLACE MACRO mrr_cube(t) AS TABLE
SELECT customer_id,
       product_id,
       month_start,
       any_value(product_line) AS product_line,
       sum(invoice_amount(t, amount_as_reported, amount_flipped, amount_excluded))::DECIMAL(14,2) AS mrr,
       count(*) AS invoice_count
FROM clean_invoices
WHERE revenue_type = 'recurring' AND NOT is_credit_note
GROUP BY customer_id, product_id, month_start
HAVING sum(invoice_amount(t, amount_as_reported, amount_flipped, amount_excluded)) <> 0;

CREATE OR REPLACE TABLE fact_revenue_monthly AS
SELECT * FROM revenue_cube((SELECT anomaly_treatment FROM cfg_settings))
ORDER BY month_start, customer_id, product_id;

CREATE OR REPLACE TABLE fact_mrr_monthly AS
SELECT * FROM mrr_cube((SELECT anomaly_treatment FROM cfg_settings))
ORDER BY month_start, customer_id, product_id;

-- Credit notes left out of MRR, by year (reported in metric_definitions.md)
CREATE OR REPLACE TABLE mrr_credit_notes_excluded AS
SELECT year(month_start) AS year,
       count(*) AS credit_notes,
       sum(amount) AS credit_note_amount
FROM clean_invoices
WHERE is_credit_note AND revenue_type = 'recurring'
GROUP BY 1
ORDER BY 1;

-- ---------------------------------------------------------------------------
-- Dimensions
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE dim_customer AS
SELECT customer_id, customer_name, customer_name_std, name_collision_flag,
       signup_date, signup_month, signup_year, signup_quarter, is_pre_window,
       tenure_months_at_dec_2025, industry, industry_missing_flag, region, region_group,
       company_size, acquisition_channel, account_manager, is_large_account,
       first_subscription_start, last_subscription_end, has_active_subscription,
       (SELECT min(month_start) FROM clean_invoices i WHERE i.customer_id = c.customer_id) AS first_invoice_month,
       (SELECT max(month_start) FROM clean_invoices i WHERE i.customer_id = c.customer_id) AS last_invoice_month
FROM clean_customers c
ORDER BY customer_id;

CREATE OR REPLACE TABLE dim_product AS
SELECT product_id, product_name, product_line, revenue_type, list_price
FROM clean_products
ORDER BY product_id;

CREATE OR REPLACE TABLE dim_date AS
SELECT d::DATE AS month_start,
       year(d) AS year,
       quarter(d) AS quarter,
       year(d) || 'Q' || quarter(d) AS year_quarter,
       month(d) AS month_number,
       strftime(d, '%b') AS month_name,
       strftime(d, '%Y-%m') AS year_month,
       month(d) = 12 AS is_year_end,
       month(d) IN (3, 6, 9, 12) AS is_quarter_end
FROM range(DATE '2022-01-01', DATE '2026-01-01', INTERVAL 1 MONTH) AS r(d)
ORDER BY d;

COMMENT ON COLUMN fact_revenue_monthly.customer_id IS 'Customer key (dim_customer).';
COMMENT ON COLUMN fact_revenue_monthly.product_id IS 'Product key (dim_product).';
COMMENT ON COLUMN fact_revenue_monthly.month_start IS 'Revenue month (dim_date).';
COMMENT ON COLUMN fact_revenue_monthly.product_line IS 'Product line.';
COMMENT ON COLUMN fact_revenue_monthly.revenue_type IS 'recurring or one-off.';
COMMENT ON COLUMN fact_revenue_monthly.gross_billings IS 'Sum of invoices other than credit notes, under the current anomaly setting.';
COMMENT ON COLUMN fact_revenue_monthly.credit_notes IS 'Sum of credit notes (negative).';
COMMENT ON COLUMN fact_revenue_monthly.net_revenue IS 'gross_billings + credit_notes.';
COMMENT ON COLUMN fact_revenue_monthly.recurring_net IS 'net_revenue on recurring products.';
COMMENT ON COLUMN fact_revenue_monthly.oneoff_net IS 'net_revenue on one-off products.';
COMMENT ON COLUMN fact_revenue_monthly.oneoff_signup_net IS 'One-off revenue with oneoff_category signup_implementation.';
COMMENT ON COLUMN fact_revenue_monthly.oneoff_other_net IS 'One-off revenue with oneoff_category other_implementation.';
COMMENT ON COLUMN fact_revenue_monthly.anomaly_amount IS 'Amount of P06 anomaly rows included under the current setting.';
COMMENT ON COLUMN fact_revenue_monthly.overdue_amount IS 'Billings with status overdue (included in net_revenue).';
COMMENT ON COLUMN fact_revenue_monthly.invoice_count IS 'Number of invoices other than credit notes.';
COMMENT ON COLUMN fact_revenue_monthly.credit_note_count IS 'Number of credit notes.';

COMMENT ON COLUMN fact_mrr_monthly.customer_id IS 'Customer key.';
COMMENT ON COLUMN fact_mrr_monthly.product_id IS 'Product key (recurring products only).';
COMMENT ON COLUMN fact_mrr_monthly.month_start IS 'Month.';
COMMENT ON COLUMN fact_mrr_monthly.product_line IS 'Product line.';
COMMENT ON COLUMN fact_mrr_monthly.mrr IS 'Recurring billings before credit notes, under the current anomaly setting.';
COMMENT ON COLUMN fact_mrr_monthly.invoice_count IS 'Number of recurring invoices in the cell.';

COMMENT ON COLUMN dim_customer.first_invoice_month IS 'First month with any invoice in the window (NULL if none).';
COMMENT ON COLUMN dim_customer.last_invoice_month IS 'Last month with any invoice in the window (NULL if none).';

COMMENT ON COLUMN dim_date.month_start IS 'First day of the month; key.';
COMMENT ON COLUMN dim_date.year IS 'Calendar year.';
COMMENT ON COLUMN dim_date.quarter IS 'Calendar quarter (1 to 4).';
COMMENT ON COLUMN dim_date.year_quarter IS 'Label, e.g. 2024Q3.';
COMMENT ON COLUMN dim_date.month_number IS 'Month number (1 to 12).';
COMMENT ON COLUMN dim_date.month_name IS 'Short month name.';
COMMENT ON COLUMN dim_date.year_month IS 'Label, e.g. 2024-07.';
COMMENT ON COLUMN dim_date.is_year_end IS 'TRUE for December (ARR snapshot month).';
COMMENT ON COLUMN dim_date.is_quarter_end IS 'TRUE for March, June, September and December.';

-- ---------------------------------------------------------------------------
-- Export (data/clean/ is created by run_all.py)
-- ---------------------------------------------------------------------------

COPY fact_revenue_monthly TO 'data/clean/fact_revenue_monthly.csv' (HEADER);
COPY fact_mrr_monthly TO 'data/clean/fact_mrr_monthly.csv' (HEADER);
COPY dim_customer TO 'data/clean/dim_customer.csv' (HEADER);
COPY dim_product TO 'data/clean/dim_product.csv' (HEADER);
COPY dim_date TO 'data/clean/dim_date.csv' (HEADER);
