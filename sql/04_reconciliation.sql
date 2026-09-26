-- 04_reconciliation.sql
-- Reconcile the revenue cube and cost data to the management accounts.
--
-- Materiality (cfg_materiality):
--   flag_gbp       a month is flagged for investigation if |difference| > £1,000
--   material_pct   a flagged month is material if |difference| > 0.5% of that month's
--                  management revenue
--   annual_pct     a year is material if |net difference| > 0.1% of annual revenue
-- Rationale: £1,000 is about 0.03% to 0.05% of a month's revenue, low enough to catch
-- a single mid-sized invoice. 0.5% of a month is the level at which a monthly trend
-- chart would visibly move. At annual level 0.1% (about £30,000 to £45,000) is well
-- below anything that would move a valuation, so nothing that matters is waved through.

CREATE OR REPLACE TABLE cfg_materiality AS
SELECT 1000.00::DECIMAL(14,2) AS flag_gbp, 0.005 AS material_pct, 0.001 AS annual_pct;

-- ---------------------------------------------------------------------------
-- 1. Anomaly options: cube net under each P06 treatment against the management
--    accounts' reported total and the sum of their product lines, by month
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE recon_options_monthly AS
WITH cube AS (
    SELECT 'as_reported' AS treatment, month_start, sum(net_revenue) AS cube_net FROM revenue_cube('as_reported') GROUP BY ALL
    UNION ALL SELECT 'flipped', month_start, sum(net_revenue) FROM revenue_cube('flipped') GROUP BY ALL
    UNION ALL SELECT 'excluded', month_start, sum(net_revenue) FROM revenue_cube('excluded') GROUP BY ALL
)
SELECT c.treatment, m.month, c.cube_net, m.total_revenue AS mgmt_total, m.revenue_sum_of_lines AS mgmt_lines,
       c.cube_net - m.total_revenue AS diff_vs_total,
       c.cube_net - m.revenue_sum_of_lines AS diff_vs_lines
FROM clean_management_accounts m
JOIN cube c ON c.month_start = m.month
ORDER BY c.treatment, m.month;

CREATE OR REPLACE TABLE recon_options_summary AS
SELECT treatment,
       count(*) FILTER (WHERE abs(diff_vs_total) < 0.005) AS months_tied_to_total,
       count(*) FILTER (WHERE abs(diff_vs_lines) < 0.005) AS months_tied_to_lines,
       sum(abs(diff_vs_total)) AS abs_diff_vs_total,
       sum(abs(diff_vs_lines)) AS abs_diff_vs_lines,
       sum(diff_vs_total) FILTER (WHERE year(month) = 2022) AS net_vs_total_2022,
       sum(diff_vs_total) FILTER (WHERE year(month) = 2023) AS net_vs_total_2023,
       sum(diff_vs_total) FILTER (WHERE year(month) = 2024) AS net_vs_total_2024,
       sum(diff_vs_total) FILTER (WHERE year(month) = 2025) AS net_vs_total_2025
FROM recon_options_monthly
GROUP BY 1
ORDER BY CASE treatment WHEN 'as_reported' THEN 1 WHEN 'flipped' THEN 2 ELSE 3 END;

-- ---------------------------------------------------------------------------
-- 2. Monthly and annual revenue reconciliation under the current setting
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE recon_monthly AS
WITH cube AS (SELECT month_start, sum(net_revenue) AS cube_net FROM fact_revenue_monthly GROUP BY 1)
SELECT m.month,
       m.total_revenue AS mgmt_total_revenue,
       c.cube_net,
       c.cube_net - m.total_revenue AS difference,
       round(100 * (c.cube_net - m.total_revenue) / m.total_revenue, 3) AS difference_pct,
       abs(c.cube_net - m.total_revenue) > k.flag_gbp AS flagged,
       abs(c.cube_net - m.total_revenue) > k.material_pct * m.total_revenue AS material,
       CASE WHEN abs(c.cube_net - m.total_revenue) < 0.005 THEN 'tied' ELSE 'difference' END AS status
FROM clean_management_accounts m
JOIN cube c ON c.month_start = m.month
CROSS JOIN cfg_materiality k
ORDER BY m.month;

CREATE OR REPLACE TABLE recon_annual AS
SELECT year(month) AS year,
       sum(mgmt_total_revenue) AS mgmt_total_revenue,
       sum(cube_net) AS cube_net,
       sum(difference) AS difference,
       round(100 * sum(difference) / sum(mgmt_total_revenue), 3) AS difference_pct,
       abs(sum(difference)) > any_value(k.annual_pct) * sum(mgmt_total_revenue) AS material,
       count(*) FILTER (WHERE status = 'tied') AS months_tied,
       count(*) FILTER (WHERE flagged) AS months_flagged
FROM recon_monthly CROSS JOIN cfg_materiality k
GROUP BY 1
ORDER BY 1;

-- ---------------------------------------------------------------------------
-- 3. Product-line reconciliation under the current setting
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE recon_product_line_monthly AS
WITH cube AS (SELECT month_start, product_line, sum(net_revenue) AS cube_net FROM fact_revenue_monthly GROUP BY ALL),
mgmt AS (
    UNPIVOT (SELECT month, revenue_core_platform AS "Core Platform", revenue_analytics_addon AS "Analytics Add-on",
                    revenue_payments_module AS "Payments Module",
                    revenue_implementation_services AS "Implementation Services"
             FROM clean_management_accounts)
    ON COLUMNS(* EXCLUDE (month)) INTO NAME product_line VALUE mgmt_revenue
)
SELECT m.month, m.product_line, m.mgmt_revenue, coalesce(c.cube_net, 0) AS cube_net,
       coalesce(c.cube_net, 0) - m.mgmt_revenue AS difference,
       abs(coalesce(c.cube_net, 0) - m.mgmt_revenue) > k.flag_gbp AS flagged
FROM mgmt m
LEFT JOIN cube c ON c.month_start = m.month AND c.product_line = m.product_line
CROSS JOIN cfg_materiality k
ORDER BY m.month, m.product_line;

CREATE OR REPLACE TABLE recon_product_line_annual AS
SELECT year(month) AS year, product_line,
       sum(mgmt_revenue) AS mgmt_revenue, sum(cube_net) AS cube_net, sum(difference) AS difference,
       count(*) FILTER (WHERE abs(difference) < 0.005) AS months_tied
FROM recon_product_line_monthly
GROUP BY ALL
ORDER BY 1, 2;

-- ---------------------------------------------------------------------------
-- 4. Internal consistency of the management accounts
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE recon_mgmt_internal AS
SELECT month, revenue_sum_of_lines, total_revenue, lines_less_total,
       total_revenue - cost_of_sales - gross_profit AS gp_arithmetic_diff,
       round(gross_profit / total_revenue, 4) - gross_margin_pct AS margin_pct_diff,
       lines_total_mismatch_flag
FROM clean_management_accounts
ORDER BY month;

-- ---------------------------------------------------------------------------
-- 5. Costs against management cost_of_sales
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE recon_costs_monthly AS
SELECT m.month, k.cost_of_delivery, m.cost_of_sales, k.cost_of_delivery - m.cost_of_sales AS difference
FROM clean_management_accounts m
JOIN (SELECT month, sum(total_cost_of_delivery) AS cost_of_delivery FROM clean_costs GROUP BY 1) k USING (month)
ORDER BY m.month;

-- ---------------------------------------------------------------------------
-- 6. Source-to-reported walk by year (current setting). Each line is a formula of
--    the lines above it; the notebook and the tests check that.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE recon_walk AS
WITH raw AS (
    SELECT year(invoice_date) AS year,
           sum(amount) FILTER (WHERE status <> 'credited') AS raw_gross_billings,
           sum(amount) FILTER (WHERE status = 'credited') AS raw_credit_notes
    FROM raw_invoices GROUP BY 1),
dup AS (SELECT year(invoice_date) AS year, sum(amount) AS dup FROM clean_removed_invoices GROUP BY 1),
anom AS (
    SELECT year(month_start) AS year,
           sum(invoice_amount((SELECT anomaly_treatment FROM cfg_settings), amount_as_reported, amount_flipped, amount_excluded)
               - amount) AS anomaly_adj
    FROM clean_invoices WHERE anomaly_flag GROUP BY 1),
cube AS (SELECT year(month_start) AS year, sum(net_revenue) AS cube_net FROM fact_revenue_monthly GROUP BY 1),
mgmt AS (SELECT year(month) AS year, sum(total_revenue) AS mgmt_total FROM clean_management_accounts GROUP BY 1)
SELECT raw.year,
       raw.raw_gross_billings,
       -coalesce(dup.dup, 0) AS less_duplicates,
       coalesce(anom.anomaly_adj, 0) AS anomaly_treatment,
       raw.raw_credit_notes AS credit_notes,
       cube.cube_net,
       mgmt.mgmt_total - cube.cube_net AS unreconciled_difference,
       mgmt.mgmt_total
FROM raw
LEFT JOIN dup USING (year) LEFT JOIN anom USING (year)
JOIN cube USING (year) JOIN mgmt USING (year)
ORDER BY raw.year;

-- ---------------------------------------------------------------------------
-- 7. Drill-down for every flagged month: what the data holds in that month
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE recon_drilldown AS
SELECT r.month, r.difference,
       coalesce((SELECT sum(amount) FROM clean_invoices i WHERE i.anomaly_flag AND i.month_start = r.month), 0) AS anomaly_amount_in_month,
       (SELECT count(*) FROM clean_invoices i WHERE i.anomaly_flag AND i.month_start = r.month) AS anomaly_rows_in_month,
       coalesce((SELECT sum(amount) FROM clean_removed_invoices d WHERE date_trunc('month', d.invoice_date) = r.month), 0) AS duplicates_removed_in_month,
       coalesce((SELECT sum(amount) FROM clean_invoices i WHERE i.is_credit_note AND i.month_start = r.month), 0) AS credit_notes_in_month,
       m.lines_less_total AS mgmt_lines_less_total,
       (SELECT string_agg(p.product_line || ' ' || p.difference, '; ') FROM recon_product_line_monthly p
         WHERE p.month = r.month AND abs(p.difference) > 0.005) AS product_line_differences,
       -- difference left after taking out the anomaly amount carried in the cube under
       -- the current setting and the management accounts' own line-sum gap
       r.difference
           - coalesce((SELECT sum(anomaly_amount) FROM fact_revenue_monthly f WHERE f.month_start = r.month), 0)
           - m.lines_less_total AS residual_after_anomaly_and_line_gap
FROM recon_monthly r
JOIN clean_management_accounts m USING (month)
WHERE r.flagged
ORDER BY r.month;
