-- Database views for reporting and Power BI

-- View: Current account balances with user info
CREATE OR ALTER VIEW vw_current_balances AS
SELECT
    u.user_id,
    u.email,
    u.first_name,
    u.last_name,
    a.account_id,
    a.account_name,
    a.account_type,
    a.currency,
    i.name as institution_name,
    b.current_balance,
    b.available_balance,
    b.usd_equivalent,
    b.date as balance_date
FROM users u
JOIN accounts a ON u.user_id = a.user_id
LEFT JOIN institutions i ON a.institution_id = i.institution_id
LEFT JOIN balances b ON a.account_id = b.account_id
WHERE a.is_active = 1
    AND b.date = (
        SELECT MAX(date)
        FROM balances
        WHERE account_id = a.account_id
    );
GO

-- View: Net worth by user
CREATE OR ALTER VIEW vw_net_worth AS
SELECT
    user_id,
    SUM(usd_equivalent) as total_net_worth_usd,
    MAX(balance_date) as as_of_date,
    COUNT(DISTINCT account_id) as active_accounts
FROM vw_current_balances
GROUP BY user_id;
GO

-- View: Monthly spending by category
CREATE OR ALTER VIEW vw_monthly_spending AS
SELECT
    a.user_id,
    YEAR(t.date) as year,
    MONTH(t.date) as month,
    t.category,
    SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) as total_spent,
    COUNT(*) as transaction_count
FROM transactions t
JOIN accounts a ON t.account_id = a.account_id
WHERE t.pending = 0
GROUP BY
    a.user_id,
    YEAR(t.date),
    MONTH(t.date),
    t.category;
GO

-- View: Account summary with latest sync
CREATE OR ALTER VIEW vw_account_summary AS
SELECT
    u.user_id,
    u.email,
    a.account_id,
    a.account_name,
    a.account_type,
    i.name as institution_name,
    i.country as institution_country,
    a.currency,
    a.is_active,
    a.last_synced_at,
    (SELECT COUNT(*) FROM transactions WHERE account_id = a.account_id) as total_transactions,
    (SELECT MIN(date) FROM transactions WHERE account_id = a.account_id) as earliest_transaction,
    (SELECT MAX(date) FROM transactions WHERE account_id = a.account_id) as latest_transaction,
    b.current_balance,
    b.usd_equivalent
FROM users u
JOIN accounts a ON u.user_id = a.user_id
LEFT JOIN institutions i ON a.institution_id = i.institution_id
LEFT JOIN (
        SELECT account_id, current_balance, usd_equivalent
        FROM (
            SELECT
                account_id,
                current_balance,
                usd_equivalent,
                ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY date DESC) AS rn
            FROM balances
        ) ranked
        WHERE rn = 1
    ) b ON a.account_id = b.account_id;
GO

-- View: Transaction history with account details
CREATE OR ALTER VIEW vw_transaction_history AS
SELECT
    t.transaction_id,
    t.date,
    t.amount,
    t.currency,
    t.description,
    t.category,
    t.pending,
    t.data_source,
    a.account_id,
    a.account_name,
    a.account_type,
    i.name as institution_name,
    u.user_id,
    u.email as user_email
FROM transactions t
JOIN accounts a ON t.account_id = a.account_id
LEFT JOIN institutions i ON a.institution_id = i.institution_id
JOIN users u ON a.user_id = u.user_id;
GO

-- View: Historical net worth (daily)
CREATE OR ALTER VIEW vw_net_worth_history AS
SELECT
    a.user_id,
    b.date,
    SUM(b.usd_equivalent) as total_net_worth_usd,
    COUNT(DISTINCT a.account_id) as accounts_included
FROM balances b
JOIN accounts a ON b.account_id = a.account_id
WHERE a.is_active = 1
GROUP BY a.user_id, b.date;
GO

-- View: Data import status
CREATE OR ALTER VIEW vw_import_status AS
SELECT
    di.import_id,
    di.file_name,
    di.file_type,
    di.date_range_start,
    di.date_range_end,
    di.transactions_imported,
    di.duplicates_found,
    di.status,
    di.created_at,
    a.account_name,
    a.account_type,
    u.email as user_email
FROM data_imports di
JOIN accounts a ON di.account_id = a.account_id
JOIN users u ON di.user_id = u.user_id;
GO

-- View: Account data completeness
CREATE OR ALTER VIEW vw_data_completeness AS
SELECT
    a.user_id,
    a.account_id,
    a.account_name,
    a.account_type,
    MIN(t.date) as earliest_transaction,
    MAX(t.date) as latest_transaction,
    DATEDIFF(DAY, MIN(t.date), MAX(t.date)) as days_of_history,
    COUNT(DISTINCT CAST(t.date AS DATE)) as days_with_transactions,
    COUNT(*) as total_transactions,
    SUM(CASE WHEN t.data_source = 'plaid' THEN 1 ELSE 0 END) as plaid_transactions,
    SUM(CASE WHEN t.data_source = 'csv' THEN 1 ELSE 0 END) as csv_transactions,
    SUM(CASE WHEN t.data_source = 'manual' THEN 1 ELSE 0 END) as manual_transactions
FROM accounts a
LEFT JOIN transactions t ON a.account_id = t.account_id
WHERE a.is_active = 1
GROUP BY
    a.user_id,
    a.account_id,
    a.account_name,
    a.account_type;
GO

-- View: Monthly income vs expenses
CREATE OR ALTER VIEW vw_monthly_cashflow AS
SELECT
    a.user_id,
    YEAR(t.date) as year,
    MONTH(t.date) as month,
    SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE 0 END) as total_income,
    SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) as total_expenses,
    SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE 0 END) -
    SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) as net_cashflow
FROM transactions t
JOIN accounts a ON t.account_id = a.account_id
WHERE t.pending = 0
GROUP BY
    a.user_id,
    YEAR(t.date),
    MONTH(t.date);
GO

PRINT 'Database views created successfully';
