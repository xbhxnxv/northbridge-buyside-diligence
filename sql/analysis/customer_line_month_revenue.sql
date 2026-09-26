-- Net revenue per customer x product line x month with the customer's size band, and the
-- line's cost of delivery that month, for cost allocation.
WITH r AS (
    SELECT f.customer_id, f.product_line, f.month_start, sum(f.net_revenue) AS net_revenue
    FROM fact_revenue_monthly f GROUP BY ALL)
SELECT r.*, c.company_size, k.total_cost_of_delivery AS line_cost_month,
       sum(r.net_revenue) OVER (PARTITION BY r.product_line, r.month_start) AS line_revenue_month,
       count(*) FILTER (WHERE r.net_revenue > 0) OVER (PARTITION BY r.product_line, r.month_start) AS line_customers_month
FROM r
JOIN dim_customer c USING (customer_id)
JOIN clean_costs k ON k.month = r.month_start AND k.product_line = r.product_line;
