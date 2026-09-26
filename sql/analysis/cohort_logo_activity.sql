-- For every customer and every month from signup to December 2025: tenure in months
-- and whether any subscription line is live (logo retention across the whole life).
WITH months AS (
    SELECT c.customer_id, c.signup_quarter, c.signup_year, c.signup_month,
           unnest(generate_series(c.signup_month, DATE '2025-12-01', INTERVAL 1 MONTH))::DATE AS month
    FROM clean_customers c
)
SELECT m.customer_id, m.signup_quarter, m.signup_year, m.signup_month, m.month,
       datediff('month', m.signup_month, m.month) AS tenure,
       EXISTS (SELECT 1 FROM clean_subscriptions s
               WHERE s.customer_id = m.customer_id AND s.start_month <= m.month
                 AND (s.end_date IS NULL OR s.end_date > m.month)) AS active
FROM months m
ORDER BY m.customer_id, m.month;
