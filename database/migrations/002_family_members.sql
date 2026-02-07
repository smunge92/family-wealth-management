-- Family Wealth Management - Family Members Migration
-- Adds family member support for filtering accounts/transactions by family member

-- Family Members table
CREATE TABLE family_members (
    family_member_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    first_name NVARCHAR(100) NOT NULL,
    last_name NVARCHAR(100) NOT NULL,
    email NVARCHAR(255),
    is_primary BIT DEFAULT 0,
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    CONSTRAINT FK_family_members_user FOREIGN KEY (user_id)
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT UQ_family_member_name UNIQUE (user_id, first_name, last_name)
);

-- Add family_member_id to accounts table
ALTER TABLE accounts ADD family_member_id INT NULL;

ALTER TABLE accounts ADD CONSTRAINT FK_accounts_family_member
    FOREIGN KEY (family_member_id) REFERENCES family_members(family_member_id);

-- Create indexes for performance
CREATE INDEX IX_family_members_user ON family_members(user_id);
CREATE INDEX IX_accounts_family_member ON accounts(family_member_id);

PRINT 'Family members migration completed successfully';
