-- Annual recurring billings (before credit notes) and months billed per customer x
-- product line, with whether the line and the customer are live in December.
SELECT r.customer_id, r.product_line, year(r.month_start) AS year,
       sum(r.gross_billings) AS billings,
       count(*) FILTER (WHERE r.gross_billings > 0) AS months_billed,
       bool_or(month(r.month_start) = 12 AND r.gross_billings > 0) AS line_live_in_december,
       EXISTS (SELECT 1 FROM fact_mrr_monthly m WHERE m.customer_id = r.customer_id
               AND m.month_start = make_date(year(r.month_start), 12, 1)) AS customer_live_in_december
FROM fact_revenue_monthly r
WHERE r.revenue_type = 'recurring'
GROUP BY ALL;
