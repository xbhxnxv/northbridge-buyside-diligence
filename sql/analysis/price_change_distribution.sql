-- Same-line % change in MRR between consecutive Decembers, for customer x product
-- line pairs held in both Decembers. The evidence for the price-increase component.
WITH d AS (
    SELECT customer_id, product_line, month_start AS m, sum(mrr) AS mrr
    FROM fact_mrr_monthly WHERE month(month_start) = 12 GROUP BY ALL),
c AS (
    SELECT year(b.m) AS year, round(100 * (b.mrr / a.mrr - 1), 2) AS pct_change, count(*) AS lines
    FROM d a JOIN d b
      ON a.customer_id = b.customer_id AND a.product_line = b.product_line AND b.m = a.m + INTERVAL 12 MONTH
    GROUP BY 1, 2)
SELECT year, pct_change, lines,
       round(100.0 * lines / sum(lines) OVER (PARTITION BY year), 2) AS share_of_lines_pct
FROM c
ORDER BY year, lines DESC;
