-- Uniform price uplift factor k by year: the most common same-line December-to-December
-- MRR ratio, with the share of continuing lines that move by exactly that ratio.
WITH d AS (
    SELECT customer_id, product_line, month_start AS m, sum(mrr) AS mrr
    FROM fact_mrr_monthly WHERE month(month_start) = 12 GROUP BY ALL),
r AS (
    SELECT year(b.m) AS year, round(b.mrr / a.mrr, 4) AS ratio
    FROM d a JOIN d b
      ON a.customer_id = b.customer_id AND a.product_line = b.product_line AND b.m = a.m + INTERVAL 12 MONTH)
SELECT year, mode(ratio) AS k,
       round(100.0 * count(*) FILTER (WHERE ratio = (SELECT mode(r2.ratio) FROM r r2 WHERE r2.year = r.year)) / count(*), 2)
           AS share_of_lines_at_k_pct,
       count(*) AS continuing_lines
FROM r GROUP BY year ORDER BY year;
