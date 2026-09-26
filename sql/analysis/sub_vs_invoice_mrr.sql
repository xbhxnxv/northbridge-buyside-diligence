-- Subscription-based MRR (lines live in December x monthly_price) against invoiced MRR
-- (fact_mrr_monthly) at each year end, with a line-level match.
WITH d AS (SELECT month_start AS m FROM dim_date WHERE is_year_end),
sub AS (
    SELECT d.m, s.customer_id, s.product_id, s.monthly_price
    FROM d JOIN clean_subscriptions s
      ON s.start_month <= d.m AND (s.end_date IS NULL OR s.end_date > d.m)),
inv AS (SELECT month_start AS m, customer_id, product_id, mrr FROM fact_mrr_monthly WHERE month(month_start) = 12),
j AS (
    SELECT coalesce(sub.m, inv.m) AS year_end, sub.customer_id AS sub_cust, inv.customer_id AS inv_cust,
           sub.monthly_price, inv.mrr, round(inv.mrr / sub.monthly_price, 4) AS line_ratio
    FROM sub FULL JOIN inv ON sub.m = inv.m AND sub.customer_id = inv.customer_id AND sub.product_id = inv.product_id)
SELECT year_end,
       count(sub_cust) AS subscription_lines,
       count(inv_cust) AS invoiced_lines,
       count(*) FILTER (WHERE sub_cust IS NULL OR inv_cust IS NULL) AS unmatched_lines,
       sum(monthly_price) AS subscription_mrr,
       sum(mrr) AS invoiced_mrr,
       sum(mrr) - sum(monthly_price) AS gap,
       round(sum(mrr) / sum(monthly_price), 4) AS invoiced_over_subscription,
       mode(line_ratio) AS most_common_line_ratio,
       count(*) FILTER (WHERE line_ratio = (SELECT mode(j2.line_ratio) FROM j j2 WHERE j2.year_end = j.year_end)) AS lines_at_that_ratio
FROM j
GROUP BY 1
ORDER BY 1;
