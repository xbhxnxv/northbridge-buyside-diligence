-- Net and recurring revenue per customer and year, with December ARR, for concentration work.
SELECT r.customer_id, year(r.month_start) AS year,
       sum(r.net_revenue) AS net_revenue,
       sum(r.recurring_net) AS recurring_net,
       sum(r.oneoff_other_net) AS other_implementation,
       12 * coalesce((SELECT sum(m.mrr) FROM fact_mrr_monthly m
                      WHERE m.customer_id = r.customer_id AND m.month_start = make_date(year(r.month_start), 12, 1)), 0) AS dec_arr
FROM fact_revenue_monthly r
GROUP BY ALL
ORDER BY year, net_revenue DESC;
