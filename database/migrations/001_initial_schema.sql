-- Family Wealth Management - Initial Database Schema
-- Azure SQL Database Migration

-- Users table (synced from Azure Entra ID)
CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    country VARCHAR(10), -- US or CA
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    INDEX idx_email (email)
);

-- Financial Institutions
CREATE TABLE institutions (
    institution_id INT IDENTITY(1,1) PRIMARY KEY,
    plaid_institution_id VARCHAR(100) UNIQUE,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(10),
    logo_url VARCHAR(500),
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    INDEX idx_plaid_inst (plaid_institution_id)
);

-- Connected Accounts
CREATE TABLE accounts (
    account_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    institution_id INT,
    plaid_account_id VARCHAR(100),
    plaid_access_token NVARCHAR(MAX), -- Encrypted in application
    account_type VARCHAR(50), -- checking, savings, investment, credit
    account_name VARCHAR(255),
    mask VARCHAR(10), -- Last 4 digits
    currency VARCHAR(3) DEFAULT 'USD',
    is_active BIT DEFAULT 1,
    last_synced_at DATETIME2,
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (institution_id) REFERENCES institutions(institution_id),
    INDEX idx_user (user_id),
    INDEX idx_plaid_account (plaid_account_id)
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
    data_source VARCHAR(20) DEFAULT 'plaid', -- plaid, csv, manual
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE,
    INDEX idx_account_date (account_id, date DESC),
    INDEX idx_plaid_transaction (plaid_transaction_id),
    INDEX idx_date (date DESC)
);

-- Balances (historical tracking)
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
    INDEX idx_account_date (account_id, date DESC),
    UNIQUE (account_id, date)
);

-- AI Insights (stored for reference)
CREATE TABLE ai_insights (
    insight_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    insight_type VARCHAR(50), -- portfolio, retirement, house, family
    prompt NVARCHAR(MAX),
    response NVARCHAR(MAX),
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_user_type (user_id, insight_type),
    INDEX idx_created (created_at DESC)
);

-- Historical Data Import Tracking
CREATE TABLE data_imports (
    import_id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    file_name VARCHAR(255),
    file_type VARCHAR(20), -- csv, ofx, xlsx, pdf
    date_range_start DATETIME2,
    date_range_end DATETIME2,
    transactions_imported INT DEFAULT 0,
    duplicates_found INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'processing', -- processing, completed, failed
    error_message NVARCHAR(MAX),
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_user_status (user_id, status),
    INDEX idx_account (account_id)
);

-- Plaid Sync Cursors (for incremental sync)
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

-- Create indexes for performance
CREATE INDEX idx_transactions_category ON transactions(category);
CREATE INDEX idx_transactions_amount ON transactions(amount);
CREATE INDEX idx_balances_usd ON balances(usd_equivalent DESC);

-- Insert default admin users (update with actual Entra ID details)
-- IMPORTANT: Replace with your actual Azure Entra ID user IDs
-- INSERT INTO users (user_id, email, first_name, last_name, country)
-- VALUES
--   ('user1-entra-id-guid', 'user1@yourdomain.com', 'User', 'One', 'US'),
--   ('user2-entra-id-guid', 'user2@yourdomain.com', 'User', 'Two', 'CA');

PRINT 'Initial schema created successfully';
