-- 02_clean.sql
-- Build clean_* tables from raw_*. Principle: cleaning fixes data errors only.
-- Judgements about revenue quality belong in the analysis, so genuine revenue stays
-- in the data with flags. The one removal is the 40 exact duplicate invoice copies.
--
-- Also builds:
--   cleaning_rules    one row per adjustment: rule, rationale, alternative considered
--   cleaning_actions  one row per affected record; docs/cleaning_log.md is generated from it
--   qa_log            questions for management raised by the data (Q01, Q02, ...)
--
-- Depends on the customer_name_key() macro defined in 01_profile.sql.

-- ---------------------------------------------------------------------------
-- Settings
-- anomaly_treatment chooses how the 15 negative amounts on invoices marked paid (P06)
-- enter the cube: as_reported, flipped or excluded. Settled in Step 3 as 'excluded':
-- it is the only option under which the cube ties to the management accounts'
-- product lines in all 48 months (docs/decisions_log.md, D01).
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE cfg_settings AS
SELECT 'excluded' AS anomaly_treatment;

CREATE OR REPLACE MACRO invoice_amount(t, as_reported, flipped, excluded) AS
    CASE t WHEN 'as_reported' THEN as_reported
           WHEN 'flipped' THEN flipped
           WHEN 'excluded' THEN excluded
           ELSE error('unknown anomaly_treatment: ' || t) END;

-- ---------------------------------------------------------------------------
-- Customers
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE clean_customers AS
WITH base AS (
    SELECT c.*,
           -- customer_name_std: trim, collapse spaces, strip trailing punctuation, then
           -- canonical legal forms (Limited -> Ltd, Grp -> Group, "and" -> "&").
           -- Source names are already in title case, so case is left as supplied.
           trim(regexp_replace(regexp_replace(regexp_replace(regexp_replace(
               regexp_replace(regexp_replace(trim(c.customer_name), '\s+', ' ', 'g'), '[.,;:]+$', ''),
               '\bLimited$', 'Ltd'),
               '\bGrp\b', 'Group', 'g'),
               '\band\b', '&', 'g'),
               '\s+', ' ', 'g')) AS customer_name_std,
           customer_name_key(c.customer_name) AS name_key
    FROM raw_customers c
),
keys AS (SELECT name_key, count(*) AS ids_with_key FROM base GROUP BY 1),
subs AS (
    SELECT customer_id,
           min(start_date) AS first_subscription_start,
           max(end_date) FILTER (WHERE end_date IS NOT NULL) AS last_subscription_end,
           bool_or(end_date IS NULL) AS has_active_subscription,
           -- Large account rule: any subscription line priced at 10x list price or more.
           -- Every other line in the data room is priced at no more than 1.07x list.
           bool_or(s.monthly_price >= 10 * p.list_price) AS is_large_account
    FROM raw_subscriptions s JOIN raw_products p USING (product_id)
    GROUP BY 1
)
SELECT b.customer_id,
       b.customer_name,
       b.customer_name_std,
       b.name_key,
       k.ids_with_key > 1 AS name_collision_flag,
       b.signup_date,
       date_trunc('month', b.signup_date)::DATE AS signup_month,
       year(b.signup_date) AS signup_year,
       year(b.signup_date) || 'Q' || quarter(b.signup_date) AS signup_quarter,
       b.signup_date < DATE '2022-01-01' AS is_pre_window,
       datediff('month', date_trunc('month', b.signup_date), DATE '2025-12-01') AS tenure_months_at_dec_2025,
       coalesce(b.industry, 'Unknown') AS industry,
       b.industry IS NULL AS industry_missing_flag,
       b.region,
       CASE WHEN b.region LIKE '%(EU)' THEN 'EU' ELSE 'UK' END AS region_group,
       b.company_size,
       b.acquisition_channel,
       b.account_manager,
       s.first_subscription_start,
       s.last_subscription_end,
       s.has_active_subscription,
       s.is_large_account
FROM base b
JOIN keys k USING (name_key)
JOIN subs s USING (customer_id)
ORDER BY b.customer_id;

-- ---------------------------------------------------------------------------
-- Products and subscriptions: no changes; flags only
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE clean_products AS
SELECT * FROM raw_products ORDER BY product_id;

CREATE OR REPLACE TABLE clean_subscriptions AS
SELECT s.*,
       s.end_date IS NULL AS is_active,
       date_trunc('month', s.start_date)::DATE AS start_month,
       s.monthly_price >= 10 * p.list_price AS is_large_line
FROM raw_subscriptions s JOIN raw_products p USING (product_id)
ORDER BY s.subscription_id;

-- ---------------------------------------------------------------------------
-- Invoices
-- ---------------------------------------------------------------------------

-- P04: exact duplicates. Key = every business field except invoice_id. Keep the lowest
-- invoice_id (the original, inside the normal numbering); drop the later copy, which
-- in all 40 cases sits in the block at the end of the INV sequence.
CREATE OR REPLACE TABLE clean_removed_invoices AS
SELECT i.*, 'P04' AS issue_id, 'A01' AS action_id, d.kept_invoice_id
FROM (
    SELECT *,
           row_number() OVER w AS copy_no,
           first_value(invoice_id) OVER w AS kept_invoice_id
    FROM raw_invoices
    WINDOW w AS (PARTITION BY customer_id, product_id, invoice_date, amount, revenue_type, status
                 ORDER BY invoice_id)
) d
JOIN raw_invoices i USING (invoice_id)
WHERE d.copy_no > 1
ORDER BY i.invoice_id;

CREATE OR REPLACE TABLE clean_invoices AS
WITH kept AS (
    SELECT i.* FROM raw_invoices i
    WHERE NOT EXISTS (SELECT 1 FROM clean_removed_invoices r WHERE r.invoice_id = i.invoice_id)
),
-- P03: link each credit note to the original it reverses (same customer, product,
-- date and absolute amount). The profile shows every credit note has exactly one match.
cn_link AS (
    SELECT cn.invoice_id, min(o.invoice_id) AS original_invoice_id
    FROM kept cn
    JOIN kept o ON o.status <> 'credited' AND o.customer_id = cn.customer_id
               AND o.product_id = cn.product_id AND o.invoice_date = cn.invoice_date
               AND o.amount = -cn.amount
    WHERE cn.status = 'credited'
    GROUP BY 1
)
SELECT k.invoice_id,
       k.customer_id,
       k.product_id,
       p.product_line,
       k.invoice_date,
       date_trunc('month', k.invoice_date)::DATE AS month_start,
       k.revenue_type,
       k.status,
       k.amount,
       k.status = 'credited' AS is_credit_note,
       l.original_invoice_id AS credit_note_original_id,
       (SELECT min(l2.invoice_id) FROM cn_link l2 WHERE l2.original_invoice_id = k.invoice_id) AS credited_by_id,
       -- P06: negative amount on an invoice that is not a credit note
       (k.amount < 0 AND k.status <> 'credited') AS anomaly_flag,
       -- Three candidate amounts for P06, identical to amount on every other row.
       -- Step 3 chooses between them against the management accounts.
       k.amount AS amount_as_reported,
       CASE WHEN k.amount < 0 AND k.status <> 'credited' THEN -k.amount ELSE k.amount END AS amount_flipped,
       CASE WHEN k.amount < 0 AND k.status <> 'credited' THEN 0 ELSE k.amount END AS amount_excluded,
       -- P02: one-off revenue category. Every implementation invoice billed in the
       -- customer's signup month is onboarding; the rest are other_implementation.
       CASE WHEN k.revenue_type <> 'one-off' THEN NULL
            WHEN date_trunc('month', k.invoice_date) = date_trunc('month', c.signup_date) THEN 'signup_implementation'
            ELSE 'other_implementation' END AS oneoff_category,
       -- P10: invoice dated before the customer's signup_date (always the same month)
       k.invoice_date < c.signup_date AS before_signup_flag,
       k.status = 'overdue' AS is_overdue
FROM kept k
JOIN raw_products p USING (product_id)
JOIN raw_customers c USING (customer_id)
LEFT JOIN cn_link l ON l.invoice_id = k.invoice_id
ORDER BY k.invoice_id;

-- ---------------------------------------------------------------------------
-- Costs and management accounts: no changes; checks carried as columns
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE clean_costs AS
SELECT *,
       hosting_cost + support_staff_cost + third_party_licence_cost - total_cost_of_delivery AS component_difference
FROM raw_costs
ORDER BY month, product_line;

-- P05: keep the reported total and the sum of the lines side by side. Step 3 tests
-- which of the two the invoice data supports.
CREATE OR REPLACE TABLE clean_management_accounts AS
SELECT *,
       revenue_core_platform + revenue_analytics_addon + revenue_payments_module
           + revenue_implementation_services AS revenue_sum_of_lines,
       revenue_core_platform + revenue_analytics_addon + revenue_payments_module
           + revenue_implementation_services - total_revenue AS lines_less_total,
       abs(revenue_core_platform + revenue_analytics_addon + revenue_payments_module
           + revenue_implementation_services - total_revenue) > 0.005 AS lines_total_mismatch_flag
FROM raw_management_accounts
ORDER BY month;

-- ---------------------------------------------------------------------------
-- Cleaning rules and one row per affected record
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE cleaning_rules AS
SELECT * FROM (VALUES
    ('A01', 'P04', 'clean_invoices', 'removed',
     'Remove exact duplicate invoices. Duplicate key: customer_id, product_id, invoice_date, amount, revenue_type, status. Keep the lowest invoice_id; remove the later copy.',
     'Each pair is identical on every business field, the same customer, product and month has no other billing, and every second copy sits in a separate block at the end of the INV numbering. A second billing for the same service in the same month is an error.',
     'Keep both and treat the copy as a separate billing (rejected: nothing distinguishes the two rows except the id). Remove by customer x product x month instead of exact key (rejected: would catch legitimate same-month billings if any existed; none do, so the result is the same).'),
    ('A02', 'P06', 'clean_invoices', 'flagged',
     'Flag negative amounts on invoices marked paid or overdue (anomaly_flag) and carry amount_as_reported, amount_flipped and amount_excluded. Settled in Step 3: the cube uses amount_excluded (cfg_settings.anomaly_treatment = excluded), so these rows contribute zero to revenue and MRR.',
     'Excluded is the only treatment under which the cube ties to the management accounts'' product lines in all 48 months with no residual, so management left these invoices out of reported revenue. The months either side of each one carry the same amount as a positive, so they look like sign-entry errors and reported revenue is probably understated by their absolute value (Q11).',
     'As reported (rejected: leaves a gap to the management accounts in every month concerned and creates 15 negative MRR rows). Flipped (rejected: also leaves a gap, twice the size; it may be the economically correct figure, which is recorded as a probable understatement and raised with management instead of booked).'),
    ('A03', 'P03', 'clean_invoices', 'linked',
     'Keep credit notes as negative revenue in the month they are dated. Link each to the original invoice with the same customer, product, date and absolute amount (credit_note_original_id, credited_by_id).',
     'Credit notes are real reversals of billed revenue. Every one matches exactly one original.',
     'Net each credit note against its original and drop both (rejected: hides the concession and the gross billing).'),
    ('A04', 'P08', 'clean_customers', 'filled',
     'Set missing industry to Unknown and set industry_missing_flag.',
     'Customers are never dropped for a missing attribute; Unknown is reported as its own segment.',
     'Infer industry from the customer name (rejected: guesswork presented as data).'),
    ('A05', 'P07', 'clean_customers', 'flagged',
     'Set name_collision_flag where another customer_id shares the normalised name key. No ids are merged.',
     'The data does not show the pairs are the same entity: their attributes agree no more often than random pairs and most run concurrent contracts. Management has to confirm.',
     'Merge ids that share a key (rejected: would change customer counts, churn and concentration on an unproven assumption).'),
    ('A06', 'P11', 'clean_customers', 'standardised',
     'Build customer_name_std: trim, collapse spaces, strip trailing punctuation, Limited to Ltd, Grp to Group, "and" to "&". The raw customer_name is kept.',
     'A consistent display name for reporting and matching. customer_id stays the key.',
     'Upper-case the display name (rejected: harder to read; the upper-case form is kept as name_key for matching).'),
    ('A07', 'P02', 'clean_invoices', 'categorised',
     'Set oneoff_category on one-off invoices: signup_implementation when billed in the customer''s signup month, other_implementation otherwise.',
     'The 45 other_implementation invoices differ in timing and size from every other implementation invoice. They stay in revenue; the category lets the analysis show them separately.',
     'Exclude them from revenue (rejected: a revenue-quality judgement, not a data error; left to the analysis and management Q&A).'),
    ('A08', 'P05', 'clean_management_accounts', 'flagged',
     'Carry revenue_sum_of_lines, lines_less_total and lines_total_mismatch_flag alongside the reported total_revenue.',
     'In four months the product lines do not add up to the reported total. The data cannot say which is wrong until Step 3 compares both with the invoices.',
     'Overwrite total_revenue with the sum of lines (rejected: changes the reported figure before the evidence is in).'),
    ('A09', 'P10', 'clean_invoices', 'flagged',
     'Set before_signup_flag where invoice_date is earlier than the customer''s signup_date. No change to dates.',
     'Every case falls in the same calendar month as the signup, so monthly revenue is unaffected. Cohort month 0 is the signup month (see metric_definitions.md).',
     'Move the invoice date to the signup date (rejected: alters source data with no effect at monthly grain).'),
    ('A10', 'P01', 'clean_customers', 'flagged',
     'Set is_large_account where any subscription line is priced at 10x list price or more.',
     'Six customers are billed far above list on every invoice, in line with their contracted subscription price. They are genuine contracts; the flag supports the concentration analysis.',
     'Treat as outliers and cap or exclude (rejected: invoices match the subscription price in 2022 and 2023 and move with the same uplift as every other customer afterwards).')
) AS t(action_id, issue_id, table_name, action_type, rule, rationale, alternative_considered);

-- revenue_impact: change to net revenue in the cube under the current setting
-- (cfg_settings). impact_if_flipped / impact_if_excluded apply to A02 only and are
-- measured against the amount as reported.
CREATE OR REPLACE TABLE cleaning_actions AS
SELECT * FROM (
SELECT 'A01' AS action_id, 'P04' AS issue_id, 'invoices' AS table_name, invoice_id AS record_id, customer_id,
       invoice_date AS record_date, 'removed; kept ' || kept_invoice_id AS detail,
       -amount AS revenue_impact, 0::DECIMAL(14,2) AS impact_if_flipped, 0::DECIMAL(14,2) AS impact_if_excluded
FROM clean_removed_invoices
UNION ALL
SELECT 'A02', 'P06', 'invoices', invoice_id, customer_id, invoice_date,
       'negative amount on ' || status || ' invoice',
       invoice_amount((SELECT anomaly_treatment FROM cfg_settings), amount_as_reported, amount_flipped, amount_excluded)
           - amount_as_reported,
       amount_flipped - amount_as_reported, amount_excluded - amount_as_reported
FROM clean_invoices WHERE anomaly_flag
UNION ALL
SELECT 'A03', 'P03', 'invoices', invoice_id, customer_id, invoice_date,
       'credit note linked to ' || coalesce(credit_note_original_id, 'NO MATCH'), 0, 0, 0
FROM clean_invoices WHERE is_credit_note
UNION ALL
SELECT 'A04', 'P08', 'customers', customer_id, customer_id, signup_date, 'industry null -> Unknown', 0, 0, 0
FROM clean_customers WHERE industry_missing_flag
UNION ALL
SELECT 'A05', 'P07', 'customers', customer_id, customer_id, signup_date, 'shares name key ' || name_key, 0, 0, 0
FROM clean_customers WHERE name_collision_flag
UNION ALL
SELECT 'A06', 'P11', 'customers', customer_id, customer_id, signup_date,
       customer_name || ' -> ' || customer_name_std, 0, 0, 0
FROM clean_customers WHERE customer_name_std <> customer_name
UNION ALL
SELECT 'A07', 'P02', 'invoices', invoice_id, customer_id, invoice_date, 'oneoff_category = other_implementation', 0, 0, 0
FROM clean_invoices WHERE oneoff_category = 'other_implementation'
UNION ALL
SELECT 'A08', 'P05', 'management_accounts', strftime(month, '%Y-%m'), NULL, month,
       'lines less total = ' || lines_less_total, 0, 0, 0
FROM clean_management_accounts WHERE lines_total_mismatch_flag
UNION ALL
SELECT 'A09', 'P10', 'invoices', invoice_id, customer_id, invoice_date, 'dated before signup_date', 0, 0, 0
FROM clean_invoices WHERE before_signup_flag
UNION ALL
SELECT 'A10', 'P01', 'customers', customer_id, customer_id, signup_date, 'is_large_account', 0, 0, 0
FROM clean_customers WHERE is_large_account
) ORDER BY action_id, record_id;

-- ---------------------------------------------------------------------------
-- Q&A log for management. Evidence strings are built from the data so the numbers
-- cannot drift from the tables. Later steps append to this table.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE qa_log (
    qa_id VARCHAR, step VARCHAR, issue_ref VARCHAR, topic VARCHAR,
    question VARCHAR, evidence VARCHAR, status VARCHAR
);

INSERT INTO qa_log
WITH
dup AS (SELECT count(*) AS n, sum(amount) AS amt FROM clean_removed_invoices),
imp AS (SELECT count(*) AS n, sum(amount) AS amt, min(amount) AS lo, max(amount) AS hi,
               count(*) FILTER (WHERE status = 'overdue') AS n_overdue,
               sum(amount) FILTER (WHERE status = 'overdue') AS amt_overdue
        FROM clean_invoices WHERE oneoff_category = 'other_implementation'),
sig AS (SELECT median(amount) AS med FROM clean_invoices WHERE oneoff_category = 'signup_implementation'),
neg AS (SELECT count(*) AS n, sum(amount) AS amt FROM clean_invoices WHERE anomaly_flag),
mgt AS (SELECT string_agg(strftime(month, '%b %Y') || ' ' || CASE WHEN lines_less_total > 0 THEN '+' ELSE '-' END || format('£{:,.0f}', abs(lines_less_total)), ', ' ORDER BY month) AS s,
               count(*) AS n
        FROM clean_management_accounts WHERE lines_total_mismatch_flag),
nm AS (SELECT count(*) AS n_ids, count(DISTINCT name_key) AS n_keys FROM clean_customers WHERE name_collision_flag),
bs AS (SELECT count(*) AS n, count(DISTINCT customer_id) AS n_cust FROM clean_invoices WHERE before_signup_flag),
ind AS (SELECT count(*) AS n FROM clean_customers WHERE industry_missing_flag)
SELECT * FROM (
    SELECT 'Q01', 'Step 2', 'P07', 'Customer identity',
           'For each pair of customer_ids whose names differ only in "Ltd" against "Limited", are the two ids the same legal entity? If so, which id should revenue and contract history sit under?',
           format('{} pairs ({} customer_ids) share a normalised name. Within a pair, region, size, industry and account manager agree no more often than for random pairs, and most pairs run contracts at the same time. List in docs/data_profile.md section 12.', nm.n_keys, nm.n_ids),
           'open' FROM nm
    UNION ALL
    SELECT 'Q02', 'Step 2', 'P02', 'Other implementation revenue',
           'What work do the 2025 implementation invoices billed outside the customer''s signup month relate to? Please provide the statement of work or contract for each.',
           format('{} invoices, £{:,.0f} in total, ranging £{:,.0f} to £{:,.0f}, all dated 2025, all for existing customers. Implementation invoices billed at signup have a median of £{:,.0f}.', imp.n, imp.amt, imp.lo, imp.hi, sig.med),
           'open' FROM imp, sig
    UNION ALL
    SELECT 'Q03', 'Step 2', 'P02', 'Other implementation revenue',
           'What is the delivery and customer-acceptance status of each of these projects at December 2025?',
           format('{} of the {} invoices (£{:,.0f}) are overdue.', imp.n_overdue, imp.n, imp.amt_overdue),
           'open' FROM imp
    UNION ALL
    SELECT 'Q04', 'Step 2', 'P02', 'Other implementation revenue',
           'On what basis is this revenue recognised: on invoice, on milestone, or on completion and acceptance? Is any of it deferred in the management accounts?',
           format('£{:,.0f} billed in 2025 on {} invoices.', imp.amt, imp.n),
           'open' FROM imp
    UNION ALL
    SELECT 'Q05', 'Step 2', 'P02', 'Other implementation revenue',
           'Are further projects of this kind contracted or expected in 2026? Please provide the pipeline with values and expected dates.',
           'None were billed in 2022 to 2024; all fall in 2025.',
           'open'
    UNION ALL
    SELECT 'Q06', 'Step 2', 'P04', 'Duplicate invoices',
           'Were the duplicate invoice copies issued to customers, and are they included in the receivables ledger and the overdue balance?',
           format('{} exact duplicates removed, £{:,.2f}. Original and copy are both marked overdue in every case.', dup.n, dup.amt),
           'open' FROM dup
    UNION ALL
    SELECT 'Q07', 'Step 2', 'P05', 'Management accounts',
           'In the months listed, the four product-line revenue figures do not add up to total revenue. Which figure is correct, and what caused the difference?',
           format('{} months: {}.', mgt.n, mgt.s),
           'open' FROM mgt
    UNION ALL
    SELECT 'Q08', 'Step 2', 'P06', 'Negative invoices',
           'What are the negative amounts on invoices marked paid? Are they credit notes recorded without the credit-note status, or sign errors?',
           format('{} invoices, -£{:,.2f} in total. Each is the only billing for its customer, product and month; the months either side carry the same amount as a positive.', neg.n, abs(neg.amt)),
           'open' FROM neg
    UNION ALL
    SELECT 'Q09', 'Step 2', 'P10', 'Contract dates',
           'What event does customers.signup_date record (contract signature, go-live or account creation)? Why are some first invoices dated before it?',
           format('{:,} invoices for {} customers are dated 1 to 26 days before signup_date, always in the same calendar month.', bs.n, bs.n_cust),
           'open' FROM bs
    UNION ALL
    SELECT 'Q10', 'Step 2', 'P08', 'Customer attributes',
           'Can management supply the industry for customers where it is blank?',
           format('{} customers have no industry; they are reported as Unknown.', ind.n),
           'open' FROM ind
);

-- ---------------------------------------------------------------------------
-- Column descriptions (docs/data_dictionary.md is generated from these)
-- ---------------------------------------------------------------------------

COMMENT ON COLUMN clean_customers.customer_id IS 'Customer key from the data room.';
COMMENT ON COLUMN clean_customers.customer_name IS 'Customer name exactly as supplied.';
COMMENT ON COLUMN clean_customers.customer_name_std IS 'Tidied display name: spaces collapsed, trailing punctuation removed, Limited to Ltd, Grp to Group, "and" to "&".';
COMMENT ON COLUMN clean_customers.name_key IS 'Upper-case matching key from customer_name_key(); used to find ids that share a name.';
COMMENT ON COLUMN clean_customers.name_collision_flag IS 'TRUE if another customer_id has the same name_key (Q01). Ids are not merged.';
COMMENT ON COLUMN clean_customers.signup_date IS 'Signup date as supplied.';
COMMENT ON COLUMN clean_customers.signup_month IS 'First day of the signup month; cohort month 0.';
COMMENT ON COLUMN clean_customers.signup_year IS 'Calendar year of signup_date.';
COMMENT ON COLUMN clean_customers.signup_quarter IS 'Signup quarter label, e.g. 2023Q2; the cohort key.';
COMMENT ON COLUMN clean_customers.is_pre_window IS 'TRUE if the customer signed up before January 2022 (left-censored in the invoice data).';
COMMENT ON COLUMN clean_customers.tenure_months_at_dec_2025 IS 'Whole months from signup_month to December 2025.';
COMMENT ON COLUMN clean_customers.industry IS 'Industry; Unknown where the source is blank.';
COMMENT ON COLUMN clean_customers.industry_missing_flag IS 'TRUE if industry was blank in the source.';
COMMENT ON COLUMN clean_customers.region IS 'Region as supplied (ten UK regions, three EU countries).';
COMMENT ON COLUMN clean_customers.region_group IS 'UK or EU (EU where region ends "(EU)").';
COMMENT ON COLUMN clean_customers.company_size IS 'Size band as supplied.';
COMMENT ON COLUMN clean_customers.acquisition_channel IS 'Acquisition channel as supplied.';
COMMENT ON COLUMN clean_customers.account_manager IS 'Account manager as supplied.';
COMMENT ON COLUMN clean_customers.first_subscription_start IS 'Earliest subscription start_date for the customer.';
COMMENT ON COLUMN clean_customers.last_subscription_end IS 'Latest non-blank subscription end_date (NULL if no line has ended).';
COMMENT ON COLUMN clean_customers.has_active_subscription IS 'TRUE if any subscription line has a blank end_date.';
COMMENT ON COLUMN clean_customers.is_large_account IS 'TRUE if any subscription line is priced at 10x list price or more.';

COMMENT ON COLUMN clean_products.product_id IS 'Product key.';
COMMENT ON COLUMN clean_products.product_name IS 'Product name.';
COMMENT ON COLUMN clean_products.product_line IS 'Product line: Core Platform, Analytics Add-on, Payments Module, Implementation Services.';
COMMENT ON COLUMN clean_products.revenue_type IS 'recurring or one-off.';
COMMENT ON COLUMN clean_products.list_price IS 'List monthly price in £ (0 for Implementation Services).';

COMMENT ON COLUMN clean_subscriptions.subscription_id IS 'Contract line key.';
COMMENT ON COLUMN clean_subscriptions.customer_id IS 'Customer key.';
COMMENT ON COLUMN clean_subscriptions.product_id IS 'Product key.';
COMMENT ON COLUMN clean_subscriptions.start_date IS 'Contract line start date.';
COMMENT ON COLUMN clean_subscriptions.end_date IS 'Contract line end date; NULL while active.';
COMMENT ON COLUMN clean_subscriptions.contract_term_months IS 'Contract term in months (12, 24 or 36).';
COMMENT ON COLUMN clean_subscriptions.monthly_price IS 'Contracted monthly price in £ at the start of the line.';
COMMENT ON COLUMN clean_subscriptions.discount_pct IS 'Discount to list price, as a fraction.';
COMMENT ON COLUMN clean_subscriptions.is_active IS 'TRUE if end_date is blank.';
COMMENT ON COLUMN clean_subscriptions.start_month IS 'First day of the start month.';
COMMENT ON COLUMN clean_subscriptions.is_large_line IS 'TRUE if monthly_price is 10x list price or more.';

COMMENT ON COLUMN clean_invoices.invoice_id IS 'Invoice or credit-note key (INV or CN prefix).';
COMMENT ON COLUMN clean_invoices.customer_id IS 'Customer key.';
COMMENT ON COLUMN clean_invoices.product_id IS 'Product key.';
COMMENT ON COLUMN clean_invoices.product_line IS 'Product line from clean_products.';
COMMENT ON COLUMN clean_invoices.invoice_date IS 'Invoice date as supplied.';
COMMENT ON COLUMN clean_invoices.month_start IS 'First day of the invoice month; the revenue month.';
COMMENT ON COLUMN clean_invoices.revenue_type IS 'recurring or one-off (matches the product on every row).';
COMMENT ON COLUMN clean_invoices.status IS 'paid, overdue or credited.';
COMMENT ON COLUMN clean_invoices.amount IS 'Amount in £ as supplied; credit notes are negative.';
COMMENT ON COLUMN clean_invoices.is_credit_note IS 'TRUE for status credited.';
COMMENT ON COLUMN clean_invoices.credit_note_original_id IS 'For a credit note, the invoice it reverses (same customer, product, date and absolute amount).';
COMMENT ON COLUMN clean_invoices.credited_by_id IS 'For an invoice that has been reversed, the credit note that reverses it.';
COMMENT ON COLUMN clean_invoices.anomaly_flag IS 'TRUE for a negative amount on an invoice marked paid or overdue (P06).';
COMMENT ON COLUMN clean_invoices.amount_as_reported IS 'P06 candidate: amount as supplied.';
COMMENT ON COLUMN clean_invoices.amount_flipped IS 'P06 candidate: sign reversed on anomaly rows, otherwise amount.';
COMMENT ON COLUMN clean_invoices.amount_excluded IS 'P06 candidate: zero on anomaly rows, otherwise amount.';
COMMENT ON COLUMN clean_invoices.oneoff_category IS 'For one-off invoices: signup_implementation (billed in the signup month) or other_implementation. NULL for recurring.';
COMMENT ON COLUMN clean_invoices.before_signup_flag IS 'TRUE if invoice_date is before the customer signup_date (always the same calendar month).';
COMMENT ON COLUMN clean_invoices.is_overdue IS 'TRUE for status overdue. Kept in revenue; reported separately for working capital.';

COMMENT ON COLUMN clean_removed_invoices.kept_invoice_id IS 'The original invoice kept in clean_invoices.';
COMMENT ON COLUMN clean_removed_invoices.issue_id IS 'Profile issue id (P04).';
COMMENT ON COLUMN clean_removed_invoices.action_id IS 'Cleaning action id (A01).';

COMMENT ON COLUMN clean_costs.month IS 'First day of the month.';
COMMENT ON COLUMN clean_costs.product_line IS 'Product line.';
COMMENT ON COLUMN clean_costs.hosting_cost IS 'Hosting cost in £.';
COMMENT ON COLUMN clean_costs.support_staff_cost IS 'Support staff cost in £.';
COMMENT ON COLUMN clean_costs.third_party_licence_cost IS 'Third-party licence cost in £.';
COMMENT ON COLUMN clean_costs.total_cost_of_delivery IS 'Total cost of delivery in £ as supplied.';
COMMENT ON COLUMN clean_costs.component_difference IS 'Sum of the three components less total_cost_of_delivery (rounding only).';

COMMENT ON COLUMN clean_management_accounts.month IS 'First day of the month.';
COMMENT ON COLUMN clean_management_accounts.revenue_core_platform IS 'Reported Core Platform revenue.';
COMMENT ON COLUMN clean_management_accounts.revenue_analytics_addon IS 'Reported Analytics Add-on revenue (source column revenue_analytics_add-on).';
COMMENT ON COLUMN clean_management_accounts.revenue_payments_module IS 'Reported Payments Module revenue.';
COMMENT ON COLUMN clean_management_accounts.revenue_implementation_services IS 'Reported Implementation Services revenue.';
COMMENT ON COLUMN clean_management_accounts.total_revenue IS 'Reported total revenue.';
COMMENT ON COLUMN clean_management_accounts.cost_of_sales IS 'Reported cost of sales.';
COMMENT ON COLUMN clean_management_accounts.gross_profit IS 'Reported gross profit.';
COMMENT ON COLUMN clean_management_accounts.gross_margin_pct IS 'Reported gross margin as a fraction.';
COMMENT ON COLUMN clean_management_accounts.revenue_sum_of_lines IS 'Sum of the four product-line revenue columns.';
COMMENT ON COLUMN clean_management_accounts.lines_less_total IS 'revenue_sum_of_lines less total_revenue.';
COMMENT ON COLUMN clean_management_accounts.lines_total_mismatch_flag IS 'TRUE where the lines do not add up to total_revenue (P05, Q07).';

COMMENT ON COLUMN cleaning_actions.action_id IS 'Cleaning rule id (see cleaning_rules).';
COMMENT ON COLUMN cleaning_actions.issue_id IS 'Profile issue id (see docs/data_profile.md).';
COMMENT ON COLUMN cleaning_actions.table_name IS 'Source table of the affected record.';
COMMENT ON COLUMN cleaning_actions.record_id IS 'Key of the affected record.';
COMMENT ON COLUMN cleaning_actions.customer_id IS 'Customer of the affected record, where there is one.';
COMMENT ON COLUMN cleaning_actions.record_date IS 'Date used to assign the action to a year.';
COMMENT ON COLUMN cleaning_actions.detail IS 'What was done to the record.';
COMMENT ON COLUMN cleaning_actions.revenue_impact IS 'Change to net revenue under the current anomaly setting (cfg_settings).';
COMMENT ON COLUMN cleaning_actions.impact_if_flipped IS 'A02 only: change to net revenue if the anomaly sign is flipped.';
COMMENT ON COLUMN cleaning_actions.impact_if_excluded IS 'A02 only: change to net revenue if anomaly rows are excluded.';
