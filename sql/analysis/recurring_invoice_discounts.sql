-- Each recurring invoice (not a credit note) with the discount_pct of the contract line it
-- bills, grossed up to a list-equivalent amount.
SELECT i.invoice_id, i.customer_id, i.product_id, i.product_line, i.month_start, year(i.month_start) AS year,
       c.company_size,
       invoice_amount((SELECT anomaly_treatment FROM cfg_settings), i.amount_as_reported, i.amount_flipped, i.amount_excluded) AS amount,
       s.discount_pct,
       invoice_amount((SELECT anomaly_treatment FROM cfg_settings), i.amount_as_reported, i.amount_flipped, i.amount_excluded)
           / (1 - s.discount_pct) AS list_equivalent
FROM clean_invoices i
JOIN dim_customer c USING (customer_id)
JOIN clean_subscriptions s
  ON s.customer_id = i.customer_id AND s.product_id = i.product_id
 AND s.start_month <= i.month_start AND (s.end_date IS NULL OR s.end_date > i.month_start)
WHERE i.revenue_type = 'recurring' AND NOT i.is_credit_note
ORDER BY i.invoice_id, s.subscription_id;
