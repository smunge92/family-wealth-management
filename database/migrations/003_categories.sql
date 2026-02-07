-- Migration: 003_categories.sql
-- Description: Add transaction categorization system with predefined categories and user rules
-- Created: 2026-02-06

-- =============================================
-- CATEGORIES TABLE
-- Stores both system-wide and user-specific categories
-- =============================================
CREATE TABLE categories (
    category_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id VARCHAR(128) NULL,           -- NULL = system category, available to all users
    name VARCHAR(100) NOT NULL,
    icon NVARCHAR(10) NULL,              -- Emoji icon
    color VARCHAR(7) NULL,               -- Hex color code (e.g., #800020)
    is_system BIT NOT NULL DEFAULT 0,    -- 1 = system category (cannot be modified by users)
    display_order INT NOT NULL DEFAULT 0,
    created_at DATETIME2 DEFAULT GETUTCDATE(),

    -- Ensure unique category names per user (NULL user_id = system categories)
    CONSTRAINT UQ_category_name_user UNIQUE (user_id, name)
);

-- Index for efficient category lookups
CREATE INDEX idx_categories_user ON categories(user_id);
CREATE INDEX idx_categories_system ON categories(is_system);

-- =============================================
-- CATEGORY RULES TABLE
-- Auto-categorization rules (system-wide and user-specific)
-- =============================================
CREATE TABLE category_rules (
    rule_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id VARCHAR(128) NULL,           -- NULL = system rule
    category_id INT NOT NULL,
    match_type VARCHAR(20) NOT NULL,     -- 'merchant_contains', 'description_contains'
    match_value VARCHAR(200) NOT NULL,   -- Pattern to match (case-insensitive)
    priority INT NOT NULL DEFAULT 100,   -- Lower number = higher priority
    is_system BIT NOT NULL DEFAULT 0,    -- 1 = system rule (cannot be modified by users)
    created_at DATETIME2 DEFAULT GETUTCDATE(),

    CONSTRAINT FK_category_rules_category
        FOREIGN KEY (category_id) REFERENCES categories(category_id),

    -- Prevent duplicate rules for same user/type/value combination
    CONSTRAINT UQ_rule_user_match UNIQUE (user_id, match_type, match_value)
);

-- Indexes for efficient rule matching
CREATE INDEX idx_category_rules_user ON category_rules(user_id);
CREATE INDEX idx_category_rules_category ON category_rules(category_id);
CREATE INDEX idx_category_rules_priority ON category_rules(priority);
CREATE INDEX idx_category_rules_match ON category_rules(match_type, match_value);

-- =============================================
-- ALTER TRANSACTIONS TABLE
-- Add category tracking columns
-- =============================================
ALTER TABLE transactions ADD
    user_category_id INT NULL,
    category_source VARCHAR(20) DEFAULT 'plaid';  -- 'plaid', 'rule', 'manual'

-- Add foreign key constraint
ALTER TABLE transactions ADD CONSTRAINT FK_transactions_user_category
    FOREIGN KEY (user_category_id) REFERENCES categories(category_id);

-- Index for category-based queries
CREATE INDEX idx_transactions_user_category ON transactions(user_category_id);
CREATE INDEX idx_transactions_category_source ON transactions(category_source);

-- =============================================
-- SEED DATA: PREDEFINED SYSTEM CATEGORIES (22)
-- =============================================
INSERT INTO categories (user_id, name, icon, color, is_system, display_order) VALUES
(NULL, 'Food & Dining', N'🍽️', '#e74c3c', 1, 1),
(NULL, 'Groceries', N'🛒', '#27ae60', 1, 2),
(NULL, 'Transportation', N'🚗', '#3498db', 1, 3),
(NULL, 'Gas & Fuel', N'⛽', '#f39c12', 1, 4),
(NULL, 'Shopping', N'🛍️', '#9b59b6', 1, 5),
(NULL, 'Entertainment', N'🎬', '#e91e63', 1, 6),
(NULL, 'Travel', N'✈️', '#00bcd4', 1, 7),
(NULL, 'Health & Medical', N'🏥', '#ff5722', 1, 8),
(NULL, 'Utilities', N'💡', '#607d8b', 1, 9),
(NULL, 'Subscriptions', N'📱', '#795548', 1, 10),
(NULL, 'Income', N'💰', '#4caf50', 1, 11),
(NULL, 'Transfer', N'💸', '#9e9e9e', 1, 12),
(NULL, 'Fees & Charges', N'🏦', '#f44336', 1, 13),
(NULL, 'Education', N'📚', '#2196f3', 1, 14),
(NULL, 'Personal Care', N'💇', '#ff9800', 1, 15),
(NULL, 'Home', N'🏠', '#8bc34a', 1, 16),
(NULL, 'Gifts & Donations', N'🎁', '#e91e63', 1, 17),
(NULL, 'Insurance', N'🛡️', '#00bcd4', 1, 18),
(NULL, 'Taxes', N'📋', '#673ab7', 1, 19),
(NULL, 'Savings', N'💵', '#00897b', 1, 20),
(NULL, 'Investments', N'📈', '#1565c0', 1, 21),
(NULL, 'Other', N'💳', '#800020', 1, 22),
(NULL, 'Rent', N'🏢', '#795548', 1, 23),
(NULL, 'Mortgage', N'🏡', '#4e342e', 1, 24);

-- =============================================
-- SEED DATA: SYSTEM CATEGORIZATION RULES
-- Priority: 1-50 = high confidence, 51-100 = medium, 101+ = low
-- =============================================

-- Food & Dining (category_id = 1)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 1, 'merchant_contains', 'STARBUCKS', 10, 1),
(NULL, 1, 'merchant_contains', 'MCDONALDS', 10, 1),
(NULL, 1, 'merchant_contains', 'MCDONALD''S', 10, 1),
(NULL, 1, 'merchant_contains', 'CHIPOTLE', 10, 1),
(NULL, 1, 'merchant_contains', 'TACO BELL', 10, 1),
(NULL, 1, 'merchant_contains', 'SUBWAY', 20, 1),
(NULL, 1, 'merchant_contains', 'DOMINO''S', 10, 1),
(NULL, 1, 'merchant_contains', 'PIZZA HUT', 10, 1),
(NULL, 1, 'merchant_contains', 'PANERA', 10, 1),
(NULL, 1, 'merchant_contains', 'CHICK-FIL-A', 10, 1),
(NULL, 1, 'merchant_contains', 'DUNKIN', 10, 1),
(NULL, 1, 'merchant_contains', 'WENDY''S', 10, 1),
(NULL, 1, 'merchant_contains', 'BURGER KING', 10, 1),
(NULL, 1, 'merchant_contains', 'KFC', 20, 1),
(NULL, 1, 'merchant_contains', 'PANDA EXPRESS', 10, 1),
(NULL, 1, 'merchant_contains', 'DOORDASH', 15, 1),
(NULL, 1, 'merchant_contains', 'UBER EATS', 15, 1),
(NULL, 1, 'merchant_contains', 'GRUBHUB', 15, 1),
(NULL, 1, 'merchant_contains', 'POSTMATES', 15, 1);

-- Groceries (category_id = 2)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 2, 'merchant_contains', 'WALMART', 20, 1),
(NULL, 2, 'merchant_contains', 'KROGER', 10, 1),
(NULL, 2, 'merchant_contains', 'COSTCO', 15, 1),
(NULL, 2, 'merchant_contains', 'SAFEWAY', 10, 1),
(NULL, 2, 'merchant_contains', 'PUBLIX', 10, 1),
(NULL, 2, 'merchant_contains', 'TRADER JOE', 10, 1),
(NULL, 2, 'merchant_contains', 'WHOLE FOODS', 10, 1),
(NULL, 2, 'merchant_contains', 'ALDI', 10, 1),
(NULL, 2, 'merchant_contains', 'TARGET', 25, 1),
(NULL, 2, 'merchant_contains', 'HEB', 10, 1),
(NULL, 2, 'merchant_contains', 'ALBERTSONS', 10, 1),
(NULL, 2, 'merchant_contains', 'GIANT', 20, 1),
(NULL, 2, 'merchant_contains', 'FOOD LION', 10, 1),
(NULL, 2, 'merchant_contains', 'WEGMANS', 10, 1),
(NULL, 2, 'merchant_contains', 'SPROUTS', 10, 1),
(NULL, 2, 'merchant_contains', 'SAM''S CLUB', 15, 1),
(NULL, 2, 'merchant_contains', 'INSTACART', 10, 1);

-- Transportation (category_id = 3)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 3, 'merchant_contains', 'UBER', 10, 1),
(NULL, 3, 'merchant_contains', 'LYFT', 10, 1),
(NULL, 3, 'merchant_contains', 'TAXI', 15, 1),
(NULL, 3, 'merchant_contains', 'PARKING', 20, 1),
(NULL, 3, 'merchant_contains', 'METRO', 20, 1),
(NULL, 3, 'merchant_contains', 'TRANSIT', 20, 1),
(NULL, 3, 'merchant_contains', 'TOLL', 15, 1),
(NULL, 3, 'merchant_contains', 'DMV', 10, 1);

-- Gas & Fuel (category_id = 4)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 4, 'merchant_contains', 'SHELL', 10, 1),
(NULL, 4, 'merchant_contains', 'EXXON', 10, 1),
(NULL, 4, 'merchant_contains', 'CHEVRON', 10, 1),
(NULL, 4, 'merchant_contains', 'BP', 15, 1),
(NULL, 4, 'merchant_contains', 'MOBIL', 10, 1),
(NULL, 4, 'merchant_contains', 'TEXACO', 10, 1),
(NULL, 4, 'merchant_contains', 'SPEEDWAY', 10, 1),
(NULL, 4, 'merchant_contains', 'CIRCLE K', 15, 1),
(NULL, 4, 'merchant_contains', 'WAWA', 15, 1),
(NULL, 4, 'merchant_contains', 'QUIKTRIP', 10, 1),
(NULL, 4, 'merchant_contains', 'SHEETZ', 10, 1),
(NULL, 4, 'merchant_contains', 'RACETRAC', 10, 1),
(NULL, 4, 'merchant_contains', 'MARATHON', 15, 1),
(NULL, 4, 'merchant_contains', 'SUNOCO', 10, 1),
(NULL, 4, 'merchant_contains', 'FUEL', 30, 1),
(NULL, 4, 'merchant_contains', 'GAS STATION', 10, 1);

-- Shopping (category_id = 5)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 5, 'merchant_contains', 'AMAZON', 15, 1),
(NULL, 5, 'merchant_contains', 'AMZN', 15, 1),
(NULL, 5, 'merchant_contains', 'BEST BUY', 10, 1),
(NULL, 5, 'merchant_contains', 'APPLE STORE', 10, 1),
(NULL, 5, 'merchant_contains', 'APPLE.COM', 15, 1),
(NULL, 5, 'merchant_contains', 'NORDSTROM', 10, 1),
(NULL, 5, 'merchant_contains', 'MACY''S', 10, 1),
(NULL, 5, 'merchant_contains', 'KOHLS', 10, 1),
(NULL, 5, 'merchant_contains', 'KOHL''S', 10, 1),
(NULL, 5, 'merchant_contains', 'TJ MAXX', 10, 1),
(NULL, 5, 'merchant_contains', 'ROSS', 15, 1),
(NULL, 5, 'merchant_contains', 'MARSHALL', 15, 1),
(NULL, 5, 'merchant_contains', 'HOME DEPOT', 10, 1),
(NULL, 5, 'merchant_contains', 'LOWES', 10, 1),
(NULL, 5, 'merchant_contains', 'LOWE''S', 10, 1),
(NULL, 5, 'merchant_contains', 'IKEA', 10, 1),
(NULL, 5, 'merchant_contains', 'BED BATH', 10, 1),
(NULL, 5, 'merchant_contains', 'OLD NAVY', 10, 1),
(NULL, 5, 'merchant_contains', 'GAP', 25, 1),
(NULL, 5, 'merchant_contains', 'ZARA', 15, 1),
(NULL, 5, 'merchant_contains', 'H&M', 15, 1),
(NULL, 5, 'merchant_contains', 'NIKE', 15, 1),
(NULL, 5, 'merchant_contains', 'ETSY', 10, 1),
(NULL, 5, 'merchant_contains', 'EBAY', 15, 1);

-- Entertainment (category_id = 6)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 6, 'merchant_contains', 'AMC', 20, 1),
(NULL, 6, 'merchant_contains', 'REGAL', 15, 1),
(NULL, 6, 'merchant_contains', 'CINEMA', 15, 1),
(NULL, 6, 'merchant_contains', 'MOVIE', 20, 1),
(NULL, 6, 'merchant_contains', 'TICKETMASTER', 10, 1),
(NULL, 6, 'merchant_contains', 'STUBHUB', 10, 1),
(NULL, 6, 'merchant_contains', 'LIVE NATION', 10, 1),
(NULL, 6, 'merchant_contains', 'CONCERT', 15, 1),
(NULL, 6, 'merchant_contains', 'ARCADE', 15, 1),
(NULL, 6, 'merchant_contains', 'DAVE & BUSTER', 10, 1),
(NULL, 6, 'merchant_contains', 'BOWLING', 15, 1),
(NULL, 6, 'merchant_contains', 'MINIATURE GOLF', 10, 1),
(NULL, 6, 'merchant_contains', 'MUSEUM', 20, 1),
(NULL, 6, 'merchant_contains', 'ZOO', 25, 1),
(NULL, 6, 'merchant_contains', 'THEME PARK', 10, 1),
(NULL, 6, 'merchant_contains', 'DISNEYLAND', 10, 1),
(NULL, 6, 'merchant_contains', 'DISNEY WORLD', 10, 1),
(NULL, 6, 'merchant_contains', 'UNIVERSAL STUDIOS', 10, 1),
(NULL, 6, 'merchant_contains', 'SIX FLAGS', 10, 1),
(NULL, 6, 'merchant_contains', 'PLAYSTATION', 10, 1),
(NULL, 6, 'merchant_contains', 'XBOX', 15, 1),
(NULL, 6, 'merchant_contains', 'NINTENDO', 10, 1),
(NULL, 6, 'merchant_contains', 'STEAM', 20, 1);

-- Travel (category_id = 7)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 7, 'merchant_contains', 'AIRLINE', 15, 1),
(NULL, 7, 'merchant_contains', 'UNITED AIR', 10, 1),
(NULL, 7, 'merchant_contains', 'DELTA', 15, 1),
(NULL, 7, 'merchant_contains', 'AMERICAN AIR', 10, 1),
(NULL, 7, 'merchant_contains', 'SOUTHWEST', 15, 1),
(NULL, 7, 'merchant_contains', 'JETBLUE', 10, 1),
(NULL, 7, 'merchant_contains', 'SPIRIT AIR', 10, 1),
(NULL, 7, 'merchant_contains', 'FRONTIER', 20, 1),
(NULL, 7, 'merchant_contains', 'HOTEL', 20, 1),
(NULL, 7, 'merchant_contains', 'MARRIOTT', 10, 1),
(NULL, 7, 'merchant_contains', 'HILTON', 10, 1),
(NULL, 7, 'merchant_contains', 'HYATT', 10, 1),
(NULL, 7, 'merchant_contains', 'IHG', 15, 1),
(NULL, 7, 'merchant_contains', 'AIRBNB', 10, 1),
(NULL, 7, 'merchant_contains', 'VRBO', 10, 1),
(NULL, 7, 'merchant_contains', 'EXPEDIA', 10, 1),
(NULL, 7, 'merchant_contains', 'BOOKING.COM', 10, 1),
(NULL, 7, 'merchant_contains', 'KAYAK', 15, 1),
(NULL, 7, 'merchant_contains', 'HERTZ', 10, 1),
(NULL, 7, 'merchant_contains', 'ENTERPRISE', 15, 1),
(NULL, 7, 'merchant_contains', 'NATIONAL CAR', 10, 1),
(NULL, 7, 'merchant_contains', 'BUDGET CAR', 10, 1),
(NULL, 7, 'merchant_contains', 'AVIS', 15, 1);

-- Health & Medical (category_id = 8)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 8, 'merchant_contains', 'CVS', 15, 1),
(NULL, 8, 'merchant_contains', 'WALGREENS', 15, 1),
(NULL, 8, 'merchant_contains', 'RITE AID', 10, 1),
(NULL, 8, 'merchant_contains', 'PHARMACY', 15, 1),
(NULL, 8, 'merchant_contains', 'HOSPITAL', 15, 1),
(NULL, 8, 'merchant_contains', 'CLINIC', 20, 1),
(NULL, 8, 'merchant_contains', 'URGENT CARE', 10, 1),
(NULL, 8, 'merchant_contains', 'DOCTOR', 20, 1),
(NULL, 8, 'merchant_contains', 'DENTAL', 15, 1),
(NULL, 8, 'merchant_contains', 'DENTIST', 15, 1),
(NULL, 8, 'merchant_contains', 'OPTOM', 15, 1),
(NULL, 8, 'merchant_contains', 'VISION', 25, 1),
(NULL, 8, 'merchant_contains', 'LENSCRAFTERS', 10, 1),
(NULL, 8, 'merchant_contains', 'MEDICAL', 20, 1),
(NULL, 8, 'merchant_contains', 'LABCORP', 10, 1),
(NULL, 8, 'merchant_contains', 'QUEST DIAG', 10, 1);

-- Utilities (category_id = 9)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 9, 'merchant_contains', 'ELECTRIC', 20, 1),
(NULL, 9, 'merchant_contains', 'POWER', 30, 1),
(NULL, 9, 'merchant_contains', 'GAS COMPANY', 15, 1),
(NULL, 9, 'merchant_contains', 'WATER', 30, 1),
(NULL, 9, 'merchant_contains', 'SEWER', 20, 1),
(NULL, 9, 'merchant_contains', 'UTILITY', 15, 1),
(NULL, 9, 'merchant_contains', 'COMCAST', 10, 1),
(NULL, 9, 'merchant_contains', 'XFINITY', 10, 1),
(NULL, 9, 'merchant_contains', 'VERIZON', 15, 1),
(NULL, 9, 'merchant_contains', 'AT&T', 15, 1),
(NULL, 9, 'merchant_contains', 'T-MOBILE', 15, 1),
(NULL, 9, 'merchant_contains', 'SPRINT', 15, 1),
(NULL, 9, 'merchant_contains', 'SPECTRUM', 10, 1),
(NULL, 9, 'merchant_contains', 'COX COMM', 10, 1),
(NULL, 9, 'merchant_contains', 'FRONTIER COMM', 10, 1);

-- Subscriptions (category_id = 10)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 10, 'merchant_contains', 'NETFLIX', 10, 1),
(NULL, 10, 'merchant_contains', 'SPOTIFY', 10, 1),
(NULL, 10, 'merchant_contains', 'HULU', 10, 1),
(NULL, 10, 'merchant_contains', 'DISNEY+', 10, 1),
(NULL, 10, 'merchant_contains', 'DISNEY PLUS', 10, 1),
(NULL, 10, 'merchant_contains', 'HBO', 15, 1),
(NULL, 10, 'merchant_contains', 'AMAZON PRIME', 10, 1),
(NULL, 10, 'merchant_contains', 'PRIME VIDEO', 10, 1),
(NULL, 10, 'merchant_contains', 'APPLE MUSIC', 10, 1),
(NULL, 10, 'merchant_contains', 'YOUTUBE PREMIUM', 10, 1),
(NULL, 10, 'merchant_contains', 'PARAMOUNT+', 10, 1),
(NULL, 10, 'merchant_contains', 'PEACOCK', 15, 1),
(NULL, 10, 'merchant_contains', 'AUDIBLE', 10, 1),
(NULL, 10, 'merchant_contains', 'KINDLE UNLIMITED', 10, 1),
(NULL, 10, 'merchant_contains', 'DROPBOX', 10, 1),
(NULL, 10, 'merchant_contains', 'GOOGLE ONE', 10, 1),
(NULL, 10, 'merchant_contains', 'ICLOUD', 15, 1),
(NULL, 10, 'merchant_contains', 'MICROSOFT 365', 10, 1),
(NULL, 10, 'merchant_contains', 'ADOBE', 15, 1),
(NULL, 10, 'merchant_contains', 'GYM', 25, 1),
(NULL, 10, 'merchant_contains', 'FITNESS', 25, 1),
(NULL, 10, 'merchant_contains', 'PLANET FITNESS', 10, 1),
(NULL, 10, 'merchant_contains', 'LA FITNESS', 10, 1),
(NULL, 10, 'merchant_contains', 'EQUINOX', 10, 1),
(NULL, 10, 'merchant_contains', 'PELOTON', 10, 1),
(NULL, 10, 'merchant_contains', 'CRUNCH', 15, 1);

-- Income (category_id = 11)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 11, 'description_contains', 'PAYROLL', 10, 1),
(NULL, 11, 'description_contains', 'DIRECT DEPOSIT', 10, 1),
(NULL, 11, 'description_contains', 'SALARY', 10, 1),
(NULL, 11, 'description_contains', 'PAYCHECK', 10, 1),
(NULL, 11, 'merchant_contains', 'GUSTO', 15, 1),
(NULL, 11, 'merchant_contains', 'ADP', 15, 1),
(NULL, 11, 'merchant_contains', 'PAYCHEX', 15, 1),
(NULL, 11, 'description_contains', 'TAX REFUND', 10, 1),
(NULL, 11, 'description_contains', 'IRS TREAS', 15, 1);

-- Transfer (category_id = 12)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 12, 'description_contains', 'TRANSFER', 15, 1),
(NULL, 12, 'merchant_contains', 'VENMO', 15, 1),
(NULL, 12, 'merchant_contains', 'PAYPAL', 20, 1),
(NULL, 12, 'merchant_contains', 'ZELLE', 15, 1),
(NULL, 12, 'merchant_contains', 'CASH APP', 15, 1),
(NULL, 12, 'description_contains', 'ACH', 25, 1),
(NULL, 12, 'description_contains', 'WIRE', 25, 1);

-- Fees & Charges (category_id = 13)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 13, 'description_contains', 'FEE', 25, 1),
(NULL, 13, 'description_contains', 'OVERDRAFT', 10, 1),
(NULL, 13, 'description_contains', 'NSF', 10, 1),
(NULL, 13, 'description_contains', 'SERVICE CHARGE', 10, 1),
(NULL, 13, 'description_contains', 'MONTHLY FEE', 10, 1),
(NULL, 13, 'description_contains', 'ATM FEE', 10, 1),
(NULL, 13, 'description_contains', 'LATE FEE', 10, 1),
(NULL, 13, 'description_contains', 'INTEREST CHARGE', 10, 1),
(NULL, 13, 'description_contains', 'FINANCE CHARGE', 10, 1);

-- Education (category_id = 14)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 14, 'merchant_contains', 'UNIVERSITY', 15, 1),
(NULL, 14, 'merchant_contains', 'COLLEGE', 15, 1),
(NULL, 14, 'merchant_contains', 'SCHOOL', 25, 1),
(NULL, 14, 'merchant_contains', 'TUITION', 10, 1),
(NULL, 14, 'merchant_contains', 'COURSERA', 10, 1),
(NULL, 14, 'merchant_contains', 'UDEMY', 10, 1),
(NULL, 14, 'merchant_contains', 'LINKEDIN LEARNING', 10, 1),
(NULL, 14, 'merchant_contains', 'SKILLSHARE', 10, 1),
(NULL, 14, 'merchant_contains', 'MASTERCLASS', 10, 1),
(NULL, 14, 'merchant_contains', 'CHEGG', 10, 1),
(NULL, 14, 'merchant_contains', 'TEXTBOOK', 15, 1),
(NULL, 14, 'merchant_contains', 'STUDENT LOAN', 10, 1);

-- Personal Care (category_id = 15)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 15, 'merchant_contains', 'SALON', 15, 1),
(NULL, 15, 'merchant_contains', 'BARBER', 15, 1),
(NULL, 15, 'merchant_contains', 'SPA', 20, 1),
(NULL, 15, 'merchant_contains', 'NAIL', 25, 1),
(NULL, 15, 'merchant_contains', 'ULTA', 10, 1),
(NULL, 15, 'merchant_contains', 'SEPHORA', 10, 1),
(NULL, 15, 'merchant_contains', 'SUPERCUTS', 10, 1),
(NULL, 15, 'merchant_contains', 'GREAT CLIPS', 10, 1),
(NULL, 15, 'merchant_contains', 'MASSAGE', 15, 1);

-- Home (category_id = 16)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 16, 'merchant_contains', 'HOA', 15, 1),
(NULL, 16, 'merchant_contains', 'PROPERTY TAX', 10, 1),
(NULL, 16, 'merchant_contains', 'FURNITURE', 20, 1),
(NULL, 16, 'merchant_contains', 'WAYFAIR', 10, 1),
(NULL, 16, 'merchant_contains', 'POTTERY BARN', 10, 1),
(NULL, 16, 'merchant_contains', 'WILLIAMS SONOMA', 10, 1),
(NULL, 16, 'merchant_contains', 'CRATE & BARREL', 10, 1),
(NULL, 16, 'merchant_contains', 'RESTORATION HARDWARE', 10, 1),
(NULL, 16, 'merchant_contains', 'ACE HARDWARE', 10, 1),
(NULL, 16, 'merchant_contains', 'TRUE VALUE', 10, 1);

-- Gifts & Donations (category_id = 17)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 17, 'merchant_contains', 'CHARITY', 15, 1),
(NULL, 17, 'merchant_contains', 'DONATION', 15, 1),
(NULL, 17, 'merchant_contains', 'RED CROSS', 10, 1),
(NULL, 17, 'merchant_contains', 'UNITED WAY', 10, 1),
(NULL, 17, 'merchant_contains', 'SALVATION ARMY', 10, 1),
(NULL, 17, 'merchant_contains', 'GOODWILL', 15, 1),
(NULL, 17, 'merchant_contains', 'GOFUNDME', 10, 1),
(NULL, 17, 'merchant_contains', 'CHURCH', 25, 1),
(NULL, 17, 'merchant_contains', 'TITHE', 15, 1),
(NULL, 17, 'description_contains', 'CONTRIBUTION', 25, 1);

-- Insurance (category_id = 18)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 18, 'merchant_contains', 'INSURANCE', 20, 1),
(NULL, 18, 'merchant_contains', 'GEICO', 10, 1),
(NULL, 18, 'merchant_contains', 'STATE FARM', 10, 1),
(NULL, 18, 'merchant_contains', 'ALLSTATE', 10, 1),
(NULL, 18, 'merchant_contains', 'PROGRESSIVE', 15, 1),
(NULL, 18, 'merchant_contains', 'LIBERTY MUTUAL', 10, 1),
(NULL, 18, 'merchant_contains', 'FARMERS INS', 10, 1),
(NULL, 18, 'merchant_contains', 'USAA', 15, 1),
(NULL, 18, 'merchant_contains', 'NATIONWIDE', 15, 1),
(NULL, 18, 'merchant_contains', 'METLIFE', 15, 1),
(NULL, 18, 'merchant_contains', 'AETNA', 15, 1),
(NULL, 18, 'merchant_contains', 'CIGNA', 15, 1),
(NULL, 18, 'merchant_contains', 'BLUE CROSS', 10, 1),
(NULL, 18, 'merchant_contains', 'UNITED HEALTH', 10, 1),
(NULL, 18, 'merchant_contains', 'KAISER', 15, 1);

-- Taxes (category_id = 19)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 19, 'description_contains', 'TAX PAYMENT', 10, 1),
(NULL, 19, 'merchant_contains', 'IRS', 10, 1),
(NULL, 19, 'merchant_contains', 'TURBOTAX', 10, 1),
(NULL, 19, 'merchant_contains', 'H&R BLOCK', 10, 1),
(NULL, 19, 'merchant_contains', 'JACKSON HEWITT', 10, 1),
(NULL, 19, 'description_contains', 'ESTIMATED TAX', 10, 1),
(NULL, 19, 'description_contains', 'PROPERTY TAX', 10, 1),
(NULL, 19, 'description_contains', 'STATE TAX', 15, 1),
(NULL, 19, 'description_contains', 'FEDERAL TAX', 15, 1);

-- Savings (category_id = 20)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 20, 'description_contains', 'SAVINGS TRANSFER', 10, 1),
(NULL, 20, 'description_contains', 'TO SAVINGS', 10, 1),
(NULL, 20, 'merchant_contains', 'MARCUS', 20, 1),
(NULL, 20, 'merchant_contains', 'ALLY BANK', 15, 1),
(NULL, 20, 'merchant_contains', 'HIGH YIELD', 15, 1),
(NULL, 20, 'description_contains', 'EMERGENCY FUND', 10, 1);

-- Investments (category_id = 21)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 21, 'merchant_contains', 'FIDELITY', 15, 1),
(NULL, 21, 'merchant_contains', 'VANGUARD', 15, 1),
(NULL, 21, 'merchant_contains', 'CHARLES SCHWAB', 10, 1),
(NULL, 21, 'merchant_contains', 'SCHWAB', 15, 1),
(NULL, 21, 'merchant_contains', 'TD AMERITRADE', 10, 1),
(NULL, 21, 'merchant_contains', 'E*TRADE', 10, 1),
(NULL, 21, 'merchant_contains', 'ETRADE', 10, 1),
(NULL, 21, 'merchant_contains', 'ROBINHOOD', 10, 1),
(NULL, 21, 'merchant_contains', 'WEBULL', 10, 1),
(NULL, 21, 'merchant_contains', 'MERRILL', 15, 1),
(NULL, 21, 'merchant_contains', 'MORGAN STANLEY', 10, 1),
(NULL, 21, 'description_contains', '401K', 10, 1),
(NULL, 21, 'description_contains', '401(K)', 10, 1),
(NULL, 21, 'description_contains', 'IRA', 15, 1),
(NULL, 21, 'description_contains', 'ROTH', 15, 1),
(NULL, 21, 'merchant_contains', 'BETTERMENT', 10, 1),
(NULL, 21, 'merchant_contains', 'WEALTHFRONT', 10, 1),
(NULL, 21, 'merchant_contains', 'ACORNS', 10, 1),
(NULL, 21, 'merchant_contains', 'COINBASE', 10, 1),
(NULL, 21, 'merchant_contains', 'CRYPTO', 20, 1);

-- Rent (category_id = 23)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 23, 'merchant_contains', 'RENT', 10, 1),
(NULL, 23, 'description_contains', 'RENT PAYMENT', 10, 1),
(NULL, 23, 'description_contains', 'MONTHLY RENT', 10, 1),
(NULL, 23, 'merchant_contains', 'AVALON', 15, 1),
(NULL, 23, 'merchant_contains', 'EQUITY RESIDENTIAL', 10, 1);

-- Mortgage (category_id = 24)
INSERT INTO category_rules (user_id, category_id, match_type, match_value, priority, is_system) VALUES
(NULL, 24, 'merchant_contains', 'MORTGAGE', 10, 1),
(NULL, 24, 'description_contains', 'MORTGAGE PAYMENT', 10, 1),
(NULL, 24, 'description_contains', 'HOME LOAN', 10, 1),
(NULL, 24, 'merchant_contains', 'ROCKET MORTGAGE', 10, 1),
(NULL, 24, 'merchant_contains', 'QUICKEN LOANS', 10, 1);

-- =============================================
-- VERIFICATION QUERIES (commented out for production)
-- =============================================
-- SELECT COUNT(*) AS category_count FROM categories;
-- SELECT COUNT(*) AS rule_count FROM category_rules;
-- SELECT name, icon, color FROM categories WHERE is_system = 1 ORDER BY display_order;
-- SELECT c.name, cr.match_type, cr.match_value, cr.priority
--   FROM category_rules cr
--   JOIN categories c ON cr.category_id = c.category_id
--   WHERE cr.is_system = 1 ORDER BY c.display_order, cr.priority;

PRINT 'Migration 003_categories.sql completed successfully';
PRINT 'Created categories table with 22 system categories';
PRINT 'Created category_rules table with system categorization rules';
PRINT 'Added user_category_id and category_source columns to transactions table';
