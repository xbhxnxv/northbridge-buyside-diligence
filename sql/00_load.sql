-- 00_load.sql
-- Load the six data-room CSVs into raw_* tables with explicit types.
-- Nothing is inferred: dates are DATE, money is DECIMAL(14,2), rates are DECIMAL(8,4)
-- and identifiers are VARCHAR. A value that does not fit its declared type makes the
-- load fail, which is what we want: a silent cast would hide a data problem.
--
-- Before fixing these types, every money column was checked as text: none has more
-- than two decimal places, so DECIMAL(14,2) is lossless. Rates have at most four.
--
-- The only structural change is one column rename in management_accounts:
-- "revenue_analytics_add-on" becomes revenue_analytics_addon, because a hyphen in a
-- column name has to be quoted everywhere it is used. Values are untouched.
--
-- Run from the repository root (paths are relative to it).

CREATE OR REPLACE TABLE raw_customers AS
SELECT *
FROM read_csv('data/raw/customers.csv', header = true, auto_detect = false,
    columns = {
        'customer_id':         'VARCHAR',
        'customer_name':       'VARCHAR',
        'signup_date':         'DATE',
        'industry':            'VARCHAR',
        'region':              'VARCHAR',
        'company_size':        'VARCHAR',
        'acquisition_channel': 'VARCHAR',
        'account_manager':     'VARCHAR'
    },
    dateformat = '%Y-%m-%d');

CREATE OR REPLACE TABLE raw_products AS
SELECT *
FROM read_csv('data/raw/products.csv', header = true, auto_detect = false,
    columns = {
        'product_id':   'VARCHAR',
        'product_name': 'VARCHAR',
        'product_line': 'VARCHAR',
        'revenue_type': 'VARCHAR',
        'list_price':   'DECIMAL(14,2)'
    });

CREATE OR REPLACE TABLE raw_subscriptions AS
SELECT *
FROM read_csv('data/raw/subscriptions.csv', header = true, auto_detect = false,
    columns = {
        'subscription_id':      'VARCHAR',
        'customer_id':          'VARCHAR',
        'product_id':           'VARCHAR',
        'start_date':           'DATE',
        'end_date':             'DATE',
        'contract_term_months': 'INTEGER',
        'monthly_price':        'DECIMAL(14,2)',
        'discount_pct':         'DECIMAL(8,4)'
    },
    dateformat = '%Y-%m-%d');

CREATE OR REPLACE TABLE raw_invoices AS
SELECT *
FROM read_csv('data/raw/invoices.csv', header = true, auto_detect = false,
    columns = {
        'invoice_id':   'VARCHAR',
        'customer_id':  'VARCHAR',
        'product_id':   'VARCHAR',
        'invoice_date': 'DATE',
        'amount':       'DECIMAL(14,2)',
        'revenue_type': 'VARCHAR',
        'status':       'VARCHAR'
    },
    dateformat = '%Y-%m-%d');

CREATE OR REPLACE TABLE raw_costs AS
SELECT *
FROM read_csv('data/raw/costs.csv', header = true, auto_detect = false,
    columns = {
        'month':                    'DATE',
        'product_line':             'VARCHAR',
        'hosting_cost':             'DECIMAL(14,2)',
        'support_staff_cost':       'DECIMAL(14,2)',
        'third_party_licence_cost': 'DECIMAL(14,2)',
        'total_cost_of_delivery':   'DECIMAL(14,2)'
    },
    dateformat = '%Y-%m-%d');

CREATE OR REPLACE TABLE raw_management_accounts AS
SELECT
    month,
    revenue_core_platform,
    "revenue_analytics_add-on" AS revenue_analytics_addon,
    revenue_payments_module,
    revenue_implementation_services,
    total_revenue,
    cost_of_sales,
    gross_profit,
    gross_margin_pct
FROM read_csv('data/raw/management_accounts.csv', header = true, auto_detect = false,
    columns = {
        'month':                           'DATE',
        'revenue_core_platform':           'DECIMAL(14,2)',
        'revenue_analytics_add-on':        'DECIMAL(14,2)',
        'revenue_payments_module':         'DECIMAL(14,2)',
        'revenue_implementation_services': 'DECIMAL(14,2)',
        'total_revenue':                   'DECIMAL(14,2)',
        'cost_of_sales':                   'DECIMAL(14,2)',
        'gross_profit':                    'DECIMAL(14,2)',
        'gross_margin_pct':                'DECIMAL(8,4)'
    },
    dateformat = '%Y-%m-%d');
