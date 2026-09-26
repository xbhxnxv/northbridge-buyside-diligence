-- MRR by signup cohort and tenure, for cohorts that start inside the data window.
SELECT c.signup_quarter, c.signup_year,
       datediff('month', c.signup_month, f.month_start) AS tenure,
       f.month_start, sum(f.mrr) AS mrr, count(DISTINCT f.customer_id) AS customers
FROM fact_mrr_monthly f JOIN clean_customers c USING (customer_id)
WHERE c.signup_month >= DATE '2022-01-01'
GROUP BY ALL
ORDER BY signup_quarter, tenure, month_start;
