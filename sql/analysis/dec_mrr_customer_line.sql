-- December MRR per customer and product line, for the ARR bridge and NRR/GRR.
SELECT customer_id, product_line, year(month_start) AS year, sum(mrr) AS dec_mrr
FROM fact_mrr_monthly
WHERE month(month_start) = 12
GROUP BY ALL
ORDER BY year, customer_id, product_line;
