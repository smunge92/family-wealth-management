"""
Data models for Family Wealth Management application using SQLAlchemy
"""

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Text, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class DataSource(enum.Enum):
    PLAID = "plaid"
    CSV = "csv"
    MANUAL = "manual"


class FileType(enum.Enum):
    CSV = "csv"
    OFX = "ofx"
    XLSX = "xlsx"
    PDF = "pdf"


class ImportStatus(enum.Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    country = Column(String(10))  # US or CA
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    accounts = relationship("Account", back_populates="user")
    insights = relationship("AIInsight", back_populates="user")
    imports = relationship("DataImport", back_populates="user")
    family_members = relationship("FamilyMember", back_populates="user")


class FamilyMember(Base):
    __tablename__ = "family_members"

    family_member_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255))
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="family_members")
    accounts = relationship("Account", back_populates="family_member")


class Institution(Base):
    __tablename__ = "institutions"

    institution_id = Column(Integer, primary_key=True, autoincrement=True)
    plaid_institution_id = Column(String(100), unique=True)
    name = Column(String(255), nullable=False)
    country = Column(String(10))
    logo_url = Column(String(500))

    # Relationships
    accounts = relationship("Account", back_populates="institution")


class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.institution_id"))
    family_member_id = Column(Integer, ForeignKey("family_members.family_member_id"))
    plaid_account_id = Column(String(100))
    plaid_access_token = Column(Text)  # Encrypted
    account_type = Column(String(50))  # checking, savings, investment, credit
    account_name = Column(String(255))
    mask = Column(String(10))  # Last 4 digits
    currency = Column(String(3), default="USD")
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="accounts")
    institution = relationship("Institution", back_populates="accounts")
    family_member = relationship("FamilyMember", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")
    balances = relationship("Balance", back_populates="account")
    imports = relationship("DataImport", back_populates="account")


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String(36), primary_key=True)
    account_id = Column(String(36), ForeignKey("accounts.account_id"), nullable=False)
    plaid_transaction_id = Column(String(100))
    date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    description = Column(Text)
    category = Column(String(100))
    pending = Column(Boolean, default=False)
    data_source = Column(Enum(DataSource), default=DataSource.PLAID)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="transactions")


class Balance(Base):
    __tablename__ = "balances"

    balance_id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String(36), ForeignKey("accounts.account_id"), nullable=False)
    date = Column(DateTime, nullable=False)
    current_balance = Column(Float)
    available_balance = Column(Float)
    currency = Column(String(3), default="USD")
    usd_equivalent = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="balances")


class AIInsight(Base):
    __tablename__ = "ai_insights"

    insight_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    insight_type = Column(String(50))  # portfolio, retirement, house, family
    prompt = Column(Text)
    response = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="insights")


class DataImport(Base):
    __tablename__ = "data_imports"

    import_id = Column(String(36), primary_key=True)
    account_id = Column(String(36), ForeignKey("accounts.account_id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    file_name = Column(String(255))
    file_type = Column(Enum(FileType))
    date_range_start = Column(DateTime)
    date_range_end = Column(DateTime)
    transactions_imported = Column(Integer, default=0)
    duplicates_found = Column(Integer, default=0)
    status = Column(Enum(ImportStatus), default=ImportStatus.PROCESSING)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="imports")
    user = relationship("User", back_populates="imports")
