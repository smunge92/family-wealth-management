-- Core table definitions for Family Wealth Management
-- This file contains the schema without migration commands

-- Users
CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    country VARCHAR(10),
    created_at DATETIME2 DEFAULT GETUTCDATE()
);

-- Institutions
CREATE TABLE institutions (
    institution_id INT IDENTITY(1,1) PRIMARY KEY,
    plaid_institution_id VARCHAR(100) UNIQUE,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(10),
    logo_url VARCHAR(500),
    created_at DATETIME2 DEFAULT GETUTCDATE()
);

-- Accounts
CREATE TABLE accounts (
    account_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    institution_id INT,
    plaid_account_id VARCHAR(100),
    plaid_access_token NVARCHAR(MAX),
    account_type VARCHAR(50),
    account_name VARCHAR(255),
    mask VARCHAR(10),
    currency VARCHAR(3) DEFAULT 'USD',
    is_active BIT DEFAULT 1,
    last_synced_at DATETIME2,
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (institution_id) REFERENCES institutions(institution_id)
);

-- Transactions
CREATE TABLE transactions (
    transaction_id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL,
    plaid_transaction_id VARCHAR(100),
    date DATETIME2 NOT NULL,
    amount FLOAT NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    description NVARCHAR(MAX),
    category VARCHAR(100),
    pending BIT DEFAULT 0,
    data_source VARCHAR(20) DEFAULT 'plaid',
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
);

-- Balances
CREATE TABLE balances (
    balance_id INT IDENTITY(1,1) PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL,
    date DATETIME2 NOT NULL,
    current_balance FLOAT,
    available_balance FLOAT,
    currency VARCHAR(3) DEFAULT 'USD',
    usd_equivalent FLOAT,
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE,
    UNIQUE (account_id, date)
);

-- AI Insights
CREATE TABLE ai_insights (
    insight_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    insight_type VARCHAR(50),
    prompt NVARCHAR(MAX),
    response NVARCHAR(MAX),
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Data Imports
CREATE TABLE data_imports (
    import_id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    file_name VARCHAR(255),
    file_type VARCHAR(20),
    date_range_start DATETIME2,
    date_range_end DATETIME2,
    transactions_imported INT DEFAULT 0,
    duplicates_found INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'processing',
    error_message NVARCHAR(MAX),
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Plaid Sync Cursors
CREATE TABLE plaid_sync_cursors (
    cursor_id INT IDENTITY(1,1) PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL,
    cursor_value NVARCHAR(MAX),
    last_synced_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE,
    UNIQUE (account_id)
);

-- User Preferences
CREATE TABLE user_preferences (
    user_id VARCHAR(36) PRIMARY KEY,
    default_currency VARCHAR(3) DEFAULT 'USD',
    timezone VARCHAR(50) DEFAULT 'America/New_York',
    email_notifications BIT DEFAULT 1,
    weekly_summary BIT DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
