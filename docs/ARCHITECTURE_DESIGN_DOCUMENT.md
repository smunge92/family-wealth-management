# Family Wealth Management - Architecture Design Document

**Version:** 1.0
**Date:** February 5, 2026
**Status:** Production

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [Architecture Diagram](#3-architecture-diagram)
4. [Frontend Architecture](#4-frontend-architecture)
5. [Backend Architecture](#5-backend-architecture)
6. [Database Design](#6-database-design)
7. [Authentication & Authorization](#7-authentication--authorization)
8. [External Integrations](#8-external-integrations)
9. [Data Flows](#9-data-flows)
10. [Security Architecture](#10-security-architecture)
11. [Deployment Architecture](#11-deployment-architecture)
12. [Configuration Management](#12-configuration-management)

---

## 1. Executive Summary

Family Wealth Management is a personal finance application designed for family-only access. It enables users to:

- **Connect bank accounts** via Plaid for automated transaction sync
- **Import historical data** from CSV/Excel/OFX files
- **Track net worth** across all accounts with daily snapshots
- **Analyze spending patterns** with category breakdowns
- **Plan for retirement** using Monte Carlo simulations
- **Receive AI-powered insights** from Claude for financial decisions

### Technology Stack Summary

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, TypeScript, MSAL, Recharts |
| **Backend** | Azure Functions (Python 3.11+) |
| **Database** | Azure SQL Server |
| **Authentication** | Azure Entra ID (Azure AD) |
| **Bank Data** | Plaid API |
| **AI Analysis** | Anthropic Claude API |
| **Infrastructure** | Azure (Functions, SQL, Key Vault, Storage) |

---

## 2. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER BROWSER                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     React SPA (TypeScript)                           │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │Dashboard │ │ Accounts │ │  Trans.  │ │ Insights │ │ Planning │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  │                              │                                       │   │
│  │  ┌────────────────┐  ┌──────┴───────┐  ┌─────────────────────────┐ │   │
│  │  │  MSAL Auth     │  │  API Service │  │  FamilyMemberContext    │ │   │
│  │  └────────────────┘  └──────────────┘  └─────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTPS (Bearer Token)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AZURE FUNCTIONS (Python)                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        function_app.py                               │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │   │
│  │  │    Plaid     │ │   Claude     │ │     API      │ │  Scheduled │ │   │
│  │  │ Integration  │ │ Integration  │ │  Endpoints   │ │    Jobs    │ │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │   │
│  │                              │                                       │   │
│  │  ┌───────────────────────────┴────────────────────────────────────┐ │   │
│  │  │                     SHARED MODULES                              │ │   │
│  │  │  ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────┐ ┌────────────┐ │ │   │
│  │  │  │  auth  │ │database│ │encryption│ │validate│ │rate_limiter│ │ │   │
│  │  │  └────────┘ └────────┘ └──────────┘ └────────┘ └────────────┘ │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
          │                    │                           │
          ▼                    ▼                           ▼
   ┌────────────┐      ┌────────────┐              ┌────────────┐
   │  Plaid API │      │ Claude API │              │ Azure SQL  │
   │  (Banking) │      │    (AI)    │              │ (Database) │
   └────────────┘      └────────────┘              └────────────┘
```

---

## 3. Architecture Diagram

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Dashboard    Accounts    Transactions    Insights    Planning          │
│      │            │             │             │           │              │
│      └────────────┴─────────────┴─────────────┴───────────┘              │
│                              │                                           │
│                    ┌─────────┴─────────┐                                │
│                    │  Common Components │                                │
│                    │  - Toast           │                                │
│                    │  - Dialogs         │                                │
│                    │  - Filters         │                                │
│                    │  - ConnectAccount  │                                │
│                    └───────────────────┘                                │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                           SERVICE LAYER                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│     ┌────────────────┐    ┌────────────────┐    ┌──────────────────┐   │
│     │  auth.ts       │    │  api.ts        │    │ FamilyMember     │   │
│     │  - MSAL config │    │  - Axios       │    │ Context.tsx      │   │
│     │  - Token mgmt  │    │  - Interceptors│    │  - State mgmt    │   │
│     └────────────────┘    └────────────────┘    └──────────────────┘   │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                           API GATEWAY                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌─────────────┐  │
│   │ /accounts   │  │ /transactions│  │ /insights   │  │ /plaid/*    │  │
│   └─────────────┘  └──────────────┘  └─────────────┘  └─────────────┘  │
│   ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌─────────────┐  │
│   │ /family-    │  │ /networth    │  │ /csv/import │  │ /balances   │  │
│   │  members    │  │              │  │             │  │             │  │
│   └─────────────┘  └──────────────┘  └─────────────┘  └─────────────┘  │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                           BUSINESS LOGIC LAYER                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐ │
│   │ Plaid Integration│  │ Claude Analysis  │  │ Data Aggregation     │ │
│   │ - Link tokens    │  │ - Portfolio      │  │ - Net worth calc     │ │
│   │ - Token exchange │  │ - Retirement     │  │ - Balance aggregation│ │
│   │ - Transaction    │  │ - House afford.  │  │ - Tax integration    │ │
│   │   sync           │  │ - Family plan    │  │                      │ │
│   │ - Webhooks       │  │                  │  │                      │ │
│   └──────────────────┘  └──────────────────┘  └──────────────────────┘ │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                           DATA ACCESS LAYER                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐   │
│   │ database.py│  │encryption  │  │validation  │  │ rate_limiter   │   │
│   │ - CRUD ops │  │ - AES-256  │  │ - Input    │  │ - Request      │   │
│   │ - Queries  │  │ - Token    │  │   sanitize │  │   throttling   │   │
│   │ - Pooling  │  │   storage  │  │            │  │                │   │
│   └────────────┘  └────────────┘  └────────────┘  └────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA STORAGE LAYER                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │                        AZURE SQL SERVER                          │  │
│   │  ┌──────┐ ┌────────────┐ ┌────────┐ ┌────────────┐ ┌─────────┐  │  │
│   │  │users │ │family_     │ │accounts│ │transactions│ │balances │  │  │
│   │  │      │ │members     │ │        │ │            │ │         │  │  │
│   │  └──────┘ └────────────┘ └────────┘ └────────────┘ └─────────┘  │  │
│   │  ┌───────────┐ ┌───────────┐ ┌──────────────┐ ┌──────────────┐  │  │
│   │  │institutions│ │ai_insights│ │data_imports  │ │plaid_sync_   │  │  │
│   │  │           │ │           │ │              │ │cursors       │  │  │
│   │  └───────────┘ └───────────┘ └──────────────┘ └──────────────┘  │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Frontend Architecture

### 4.1 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | React | 18.2.0 |
| Language | TypeScript | 4.9.5 |
| Routing | React Router DOM | 6.21.1 |
| State | React Context API | - |
| Auth | MSAL React | 2.0.11 |
| HTTP | Axios | 1.6.5 |
| Charts | Recharts | 2.15.4 |
| Plaid | React Plaid Link | 3.5.1 |
| BI | Power BI Client React | 1.4.0 |

### 4.2 Directory Structure

```
frontend/src/
├── components/
│   ├── Dashboard/
│   │   ├── Dashboard.tsx          # Main dashboard with widgets
│   │   └── Dashboard.css
│   ├── Accounts/
│   │   ├── Accounts.tsx           # Account list & management
│   │   ├── ConnectAccount.tsx     # Plaid Link integration
│   │   └── Accounts.css
│   ├── Transactions/
│   │   ├── Transactions.tsx       # Transaction history
│   │   └── Transactions.css
│   ├── Insights/
│   │   └── FinancialInsights.tsx  # AI-powered insights
│   ├── Planning/
│   │   ├── RetirementPlanning.tsx # Retirement calculator
│   │   └── HouseAffordability.tsx # Home purchase planning
│   ├── Auth/
│   │   └── Login.tsx              # Login component
│   └── common/
│       ├── Toast.tsx              # Notification component
│       ├── FamilyMemberFilter.tsx # Family member dropdown
│       └── LoadingSpinner.tsx
├── services/
│   ├── auth.ts                    # MSAL configuration
│   └── api.ts                     # Axios instance
├── context/
│   └── FamilyMemberContext.tsx    # Family member state
├── hooks/
│   └── useApi.ts                  # API hooks
├── App.tsx                        # Main app with routing
└── index.tsx                      # Entry point with MSAL
```

### 4.3 Component Hierarchy

```
<MsalProvider>
  └── <App>
      ├── <AuthenticatedTemplate>
      │   ├── <Header>
      │   │   ├── <Navigation>
      │   │   └── <FamilyMemberFilter>
      │   └── <FamilyMemberProvider>
      │       └── <Routes>
      │           ├── <Dashboard />
      │           ├── <Accounts />
      │           ├── <Transactions />
      │           ├── <FinancialInsights />
      │           └── <Planning />
      └── <UnauthenticatedTemplate>
          └── <Login />
```

### 4.4 State Management

**FamilyMemberContext** provides:

```typescript
interface FamilyMemberContextType {
  familyMembers: FamilyMember[];
  selectedMemberId: number | null;  // null = all family
  setSelectedMemberId: (id: number | null) => void;
  addFamilyMember: (member: NewFamilyMember) => Promise<void>;
  deleteFamilyMember: (id: number) => Promise<void>;
  refreshFamilyMembers: () => Promise<void>;
}
```

---

## 5. Backend Architecture

### 5.1 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Runtime | Azure Functions | v2 |
| Language | Python | 3.11+ |
| Database | pymssql / SQLAlchemy | Latest |
| Auth | MSAL | 1.24+ |
| Encryption | cryptography | Latest |

### 5.2 Directory Structure

```
backend/
├── function_app.py              # Entry point (Blueprint registration)
├── functions/
│   ├── plaid_integration/
│   │   ├── connect_account.py   # POST /plaid/link-token, /plaid/exchange-token
│   │   ├── sync_transactions.py # POST /transactions/sync
│   │   ├── historical_data.py   # GET historical transactions
│   │   ├── csv_import.py        # POST /csv/import
│   │   └── webhooks.py          # POST /plaid/webhook
│   ├── claude_integration/
│   │   ├── portfolio_analysis.py    # POST /insights/portfolio
│   │   ├── retirement_planning.py   # POST /insights/retirement
│   │   ├── house_affordability.py   # POST /insights/house
│   │   └── spending_analysis.py     # POST /insights/spending
│   ├── data_aggregation/
│   │   ├── aggregate_balances.py    # Balance aggregation
│   │   ├── calculate_networth.py    # GET /networth
│   │   └── tax_integration.py       # Tax insights
│   ├── api/
│   │   ├── accounts.py          # GET/DELETE /accounts
│   │   ├── transactions.py      # GET /transactions
│   │   ├── family_members.py    # GET/POST/DELETE /family-members
│   │   └── insights.py          # GET /insights (cached)
│   └── scheduled_jobs/
│       ├── daily_sync.py        # Timer: daily transaction sync
│       └── weekly_analysis.py   # Timer: weekly AI insights
├── shared/
│   ├── auth.py                  # Authentication & authorization
│   ├── database.py              # Database connection manager
│   ├── plaid_client.py          # Plaid API wrapper
│   ├── claude_client.py         # Anthropic Claude wrapper
│   ├── encryption.py            # AES-256-GCM encryption
│   ├── validation.py            # Input validation
│   ├── rate_limiter.py          # Request throttling
│   ├── audit.py                 # Audit logging
│   ├── monte_carlo.py           # Retirement simulations
│   ├── deduplication.py         # Transaction deduplication
│   └── data_retention.py        # GDPR compliance
├── tests/
│   ├── test_auth.py
│   ├── test_database.py
│   ├── test_validation.py
│   └── security/
│       └── owasp_pentest.py
├── requirements.txt
├── host.json
└── local.settings.json
```

### 5.3 API Endpoints

| Endpoint | Method | Function | Rate Limit | Auth |
|----------|--------|----------|------------|------|
| `/plaid/link-token` | POST | Create Plaid Link token | 5/min | Yes |
| `/plaid/exchange-token` | POST | Exchange public token | - | Yes |
| `/plaid/webhook` | POST | Receive Plaid webhooks | - | Signature |
| `/transactions/sync` | POST | Sync transactions | 2/min | Yes |
| `/csv/import` | POST | Import CSV data | 5/min | Yes |
| `/accounts` | GET | List accounts | 60/min | Yes |
| `/accounts/{id}` | DELETE | Delete account | 10/min | Yes |
| `/accounts/{id}/family-member` | PUT | Assign family member | 60/min | Yes |
| `/transactions` | GET | Query transactions | 60/min | Yes |
| `/family-members` | GET/POST | List/Create members | 60/min | Yes |
| `/family-members/{id}` | DELETE | Delete member | 10/min | Yes |
| `/networth` | GET | Get net worth | 60/min | Yes |
| `/insights/portfolio` | POST | AI portfolio analysis | 10/min | Yes |
| `/insights/retirement` | POST | Retirement planning | 10/min | Yes |
| `/insights/house` | POST | House affordability | 10/min | Yes |
| `/insights/spending` | POST | Spending analysis | 10/min | Yes |

### 5.4 Shared Modules

| Module | Purpose |
|--------|---------|
| `auth.py` | JWT validation, user isolation, CORS headers |
| `database.py` | SQL connection, CRUD operations, transactions |
| `encryption.py` | AES-256-GCM encrypt/decrypt for Plaid tokens |
| `validation.py` | Input sanitization, type validation |
| `rate_limiter.py` | In-memory/Redis request throttling |
| `audit.py` | Security event logging |
| `plaid_client.py` | Plaid API wrapper (link, exchange, sync) |
| `claude_client.py` | Claude API wrapper (analysis prompts) |
| `monte_carlo.py` | Retirement projection simulations |

---

## 6. Database Design

### 6.1 Entity Relationship Diagram

```
┌──────────────┐       ┌─────────────────┐       ┌──────────────┐
│    users     │       │  family_members │       │ institutions │
├──────────────┤       ├─────────────────┤       ├──────────────┤
│ user_id (PK) │◄──────┤ user_id (FK)    │       │ institution_ │
│ email        │       │ family_member_  │       │   id (PK)    │
│ first_name   │       │   id (PK)       │       │ plaid_inst_id│
│ last_name    │       │ first_name      │       │ name         │
│ country      │       │ last_name       │       │ logo_url     │
│ created_at   │       │ email           │       │ country      │
└──────────────┘       │ is_primary      │       └──────────────┘
        │              │ created_at      │              │
        │              └─────────────────┘              │
        │                      │                        │
        │                      │                        │
        ▼                      ▼                        ▼
┌───────────────────────────────────────────────────────────────┐
│                          accounts                              │
├───────────────────────────────────────────────────────────────┤
│ account_id (PK)         │ user_id (FK)                        │
│ family_member_id (FK)   │ institution_id (FK)                 │
│ plaid_account_id        │ plaid_access_token (ENCRYPTED)      │
│ account_type            │ account_name                        │
│ mask                    │ currency                            │
│ is_active               │ last_synced_at                      │
└───────────────────────────────────────────────────────────────┘
        │                                      │
        │                                      │
        ▼                                      ▼
┌──────────────────┐              ┌──────────────────────────────┐
│   transactions   │              │          balances            │
├──────────────────┤              ├──────────────────────────────┤
│ transaction_id   │              │ balance_id (PK)              │
│   (PK)           │              │ account_id (FK)              │
│ account_id (FK)  │              │ date                         │
│ plaid_txn_id     │              │ current_balance              │
│ date             │              │ available_balance            │
│ amount           │              │ currency                     │
│ description      │              │ usd_equivalent               │
│ category         │              │ UNIQUE(account_id, date)     │
│ pending          │              └──────────────────────────────┘
│ data_source      │
│ created_at       │
└──────────────────┘

┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   ai_insights    │    │   data_imports   │    │ plaid_sync_      │
├──────────────────┤    ├──────────────────┤    │   cursors        │
│ insight_id (PK)  │    │ import_id (PK)   │    ├──────────────────┤
│ user_id (FK)     │    │ account_id (FK)  │    │ cursor_id (PK)   │
│ insight_type     │    │ user_id (FK)     │    │ account_id (FK)  │
│ prompt           │    │ file_name        │    │   UNIQUE         │
│ response         │    │ file_type        │    │ cursor_value     │
│ created_at       │    │ status           │    │ last_synced_at   │
└──────────────────┘    │ txns_imported    │    └──────────────────┘
                        │ duplicates_found │
                        │ error_message    │
                        │ created_at       │
                        └──────────────────┘
```

### 6.2 Table Definitions

| Table | Primary Key | Foreign Keys | Indexes |
|-------|-------------|--------------|---------|
| users | user_id (UUID) | - | email (UNIQUE) |
| family_members | family_member_id (INT) | user_id | (user_id, first_name, last_name) UNIQUE |
| institutions | institution_id (INT) | - | plaid_institution_id (UNIQUE) |
| accounts | account_id (UUID) | user_id, family_member_id, institution_id | user_id, plaid_account_id |
| transactions | transaction_id (UUID) | account_id (CASCADE) | account_id, date, category |
| balances | balance_id (INT) | account_id (CASCADE) | (account_id, date) UNIQUE |
| ai_insights | insight_id (UUID) | user_id | user_id, insight_type, created_at |
| data_imports | import_id (UUID) | account_id, user_id | account_id, status |
| plaid_sync_cursors | cursor_id (INT) | account_id (CASCADE UNIQUE) | - |

### 6.3 Database Views

| View | Purpose |
|------|---------|
| `vw_current_balances` | Latest balance per account with user info |
| `vw_net_worth` | User net worth aggregation |
| `vw_monthly_spending` | Spending by category per month |
| `vw_account_summary` | Account details with transaction counts |
| `vw_transaction_history` | Transactions with account/institution context |
| `vw_net_worth_history` | Daily net worth time-series |
| `vw_monthly_cashflow` | Income vs expenses by month |

---

## 7. Authentication & Authorization

### 7.1 Authentication Flow

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
│  React   │────►│  Azure Entra │────►│   Microsoft  │────►│   React  │
│   App    │     │   ID Login   │     │    Login     │     │   App    │
└──────────┘     └──────────────┘     └──────────────┘     └──────────┘
     │                                                            │
     │  1. User clicks "Sign In"                                  │
     │  2. MSAL redirects to Azure login                          │
     │  3. User authenticates with Microsoft                      │
     │  4. Azure returns tokens (access, id, refresh)             │
     │  5. MSAL stores tokens in sessionStorage                   │
     │                                                            │
     ▼                                                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        API Request with Token                         │
│  GET /api/accounts                                                    │
│  Authorization: Bearer {id_token}                                     │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       Backend Token Validation                        │
│  1. Extract Bearer token from Authorization header                    │
│  2. Decode JWT header to get 'kid' (key ID)                          │
│  3. Fetch JWKS from Microsoft: /discovery/v2.0/keys                  │
│  4. Verify JWT signature with RSA public key                         │
│  5. Validate: audience, issuer, expiration                           │
│  6. Extract user_id (oid) and email from claims                      │
│  7. Check email in ALLOWED_USERS list                                │
│  8. Validate user can access requested resource                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 7.2 Authorization Layers

| Layer | Check | Failure Response |
|-------|-------|------------------|
| **Token Validation** | JWT signature, expiry, audience, issuer | 401 Unauthorized |
| **User Allowlist** | Email in ALLOWED_USERS env var | 403 Forbidden |
| **User Isolation** | Token user_id matches requested user_id | 403 Forbidden |

### 7.3 Security Headers

```python
{
    "Access-Control-Allow-Origin": "<configured_origin>",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
    "Cache-Control": "no-store, no-cache, must-revalidate"
}
```

---

## 8. External Integrations

### 8.1 Plaid API

**Purpose:** Bank account connection and transaction sync

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────►│   Backend   │────►│  Plaid API  │
│ (Plaid Link)│     │  (Exchange) │     │             │
└─────────────┘     └─────────────┘     └─────────────┘

Endpoints Used:
- POST /link/token/create     → Create link token for frontend
- POST /item/public_token/exchange → Exchange public token for access token
- POST /transactions/sync     → Incremental transaction sync
- GET  /accounts/get          → List accounts for an item
- POST /institutions/get_by_id → Get institution metadata
- POST /item/remove           → Disconnect an item
```

**Data Flow:**
1. Frontend requests link token from backend
2. Backend calls Plaid to create link token
3. Frontend displays Plaid Link modal
4. User authenticates with their bank
5. Plaid returns public token to frontend
6. Frontend sends public token to backend
7. Backend exchanges for access token (encrypted and stored)
8. Backend syncs transactions and balances

### 8.2 Anthropic Claude API

**Purpose:** AI-powered financial analysis and insights

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────►│   Backend   │────►│ Claude API  │
│ (Request)   │     │  (Prompt)   │     │ (Analysis)  │
└─────────────┘     └─────────────┘     └─────────────┘

Analysis Types:
- Portfolio Analysis  → Asset allocation, risk profile, diversification
- Retirement Planning → Monte Carlo projections, savings rate
- House Affordability → Purchase feasibility, timeline
- Spending Analysis   → Category breakdown, optimization tips
```

### 8.3 Azure Services

| Service | Purpose |
|---------|---------|
| **Entra ID** | User authentication (OAuth 2.0 / OIDC) |
| **SQL Database** | Primary data store |
| **Key Vault** | Secrets management |
| **Functions** | Serverless API hosting |
| **Application Insights** | Monitoring and logging |
| **Storage** | Frontend static hosting (optional) |

---

## 9. Data Flows

### 9.1 Account Connection Flow

```
User → Connect Account → Plaid Link → Bank Auth → Public Token
                                                        ↓
                            Backend ← Exchange Token ← Public Token
                               ↓
                         Get Accounts → Plaid API
                               ↓
                     Encrypt Access Token (AES-256-GCM)
                               ↓
                         Store in DB:
                         - accounts
                         - balances
                         - institutions
                         - plaid_sync_cursors
                               ↓
                         Sync Initial Transactions
                               ↓
                         Return Account List → Frontend
```

### 9.2 Transaction Sync Flow

```
Timer (Daily 2 AM) OR User Request
                ↓
        For Each Active Account:
                ↓
        Get cursor from plaid_sync_cursors
                ↓
        Call Plaid /transactions/sync
                ↓
        Process Response:
        - added: INSERT new transactions
        - modified: UPDATE existing
        - removed: DELETE transactions
                ↓
        Update cursor value
                ↓
        Aggregate daily balance
                ↓
        Update net worth views
```

### 9.3 AI Analysis Flow

```
User → Request Portfolio Analysis → Backend
                                       ↓
                              Check Cache (24h TTL)
                              ┌─────────┴─────────┐
                         Cache Hit          Cache Miss
                              ↓                   ↓
                         Return Cached    Fetch Financial Data:
                                          - accounts
                                          - transactions (90 days)
                                          - balances
                                                  ↓
                                          Build Claude Prompt
                                                  ↓
                                          Call Claude API
                                                  ↓
                                          Store in ai_insights
                                                  ↓
                                          Return Analysis
```

---

## 10. Security Architecture

### 10.1 Security Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SECURITY LAYERS                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Layer 1: TRANSPORT SECURITY                                   │ │
│  │  - TLS 1.2+ for all connections                               │ │
│  │  - HSTS header enforces HTTPS                                 │ │
│  │  - Certificate validation                                      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Layer 2: AUTHENTICATION                                       │ │
│  │  - Azure Entra ID (OAuth 2.0 + OIDC)                          │ │
│  │  - JWT token validation (signature, expiry, claims)           │ │
│  │  - JWKS key rotation support                                   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Layer 3: AUTHORIZATION                                        │ │
│  │  - Email allowlist (ALLOWED_USERS)                             │ │
│  │  - User isolation (can only access own data)                   │ │
│  │  - Rate limiting per endpoint                                   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Layer 4: DATA PROTECTION                                      │ │
│  │  - AES-256-GCM encryption for Plaid tokens                     │ │
│  │  - Parameterized SQL queries (no injection)                    │ │
│  │  - Input validation and sanitization                           │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Layer 5: AUDIT & MONITORING                                   │ │
│  │  - All requests logged to Application Insights                 │ │
│  │  - Security events (auth failures, access violations)          │ │
│  │  - No sensitive data in logs                                   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 10.2 Encryption

| Data | Encryption | Algorithm |
|------|------------|-----------|
| Plaid Access Tokens | At rest | AES-256-GCM (Fernet) |
| Database Connection | In transit | TLS 1.2+ |
| API Requests | In transit | HTTPS |
| User Passwords | Not stored | Azure Entra ID handles |

### 10.3 Rate Limiting

| Endpoint Category | Limit | Window |
|-------------------|-------|--------|
| Read operations | 60 | 1 minute |
| Write operations | 30 | 1 minute |
| Delete operations | 10 | 1 minute |
| Plaid link | 5 | 1 minute |
| AI insights | 10 | 1 minute |
| Transaction sync | 2 | 1 minute |

---

## 11. Deployment Architecture

### 11.1 Azure Resources

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AZURE SUBSCRIPTION                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    RESOURCE GROUP                             │   │
│  │                                                               │   │
│  │  ┌────────────────┐    ┌────────────────┐                    │   │
│  │  │ Azure Function │    │  Azure SQL     │                    │   │
│  │  │ App (Python)   │───►│  Database      │                    │   │
│  │  │ - API hosting  │    │  - Data store  │                    │   │
│  │  │ - Timer jobs   │    │                │                    │   │
│  │  └────────────────┘    └────────────────┘                    │   │
│  │          │                                                    │   │
│  │          ▼                                                    │   │
│  │  ┌────────────────┐    ┌────────────────┐                    │   │
│  │  │ Azure Key      │    │ Application    │                    │   │
│  │  │ Vault          │    │ Insights       │                    │   │
│  │  │ - Secrets      │    │ - Monitoring   │                    │   │
│  │  │ - Keys         │    │ - Logging      │                    │   │
│  │  └────────────────┘    └────────────────┘                    │   │
│  │                                                               │   │
│  │  ┌────────────────┐    ┌────────────────┐                    │   │
│  │  │ Azure Entra ID │    │ Azure Storage  │                    │   │
│  │  │ (Azure AD)     │    │ (Frontend)     │                    │   │
│  │  │ - Auth         │    │ - Static site  │                    │   │
│  │  │ - Users        │    │ - CDN          │                    │   │
│  │  └────────────────┘    └────────────────┘                    │   │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 11.2 Environment Configuration

| Environment | Frontend URL | Backend URL | Database |
|-------------|--------------|-------------|----------|
| **Local Dev** | localhost:3000 | localhost:7071 | Azure SQL (remote) |
| **Production** | https://app.domain.com | https://api.domain.com | Azure SQL |

---

## 12. Configuration Management

### 12.1 Frontend Environment Variables

```bash
# Azure Authentication
REACT_APP_AZURE_CLIENT_ID=<app-registration-client-id>
REACT_APP_AZURE_TENANT_ID=<azure-tenant-id>
REACT_APP_AZURE_REDIRECT_URI=http://localhost:3000
REACT_APP_AZURE_AUTHORITY=https://login.microsoftonline.com/<tenant>

# API Configuration
REACT_APP_API_BASE_URL=http://localhost:7071/api

# Plaid
REACT_APP_PLAID_ENV=sandbox

# Power BI (optional)
REACT_APP_POWERBI_WORKSPACE_ID=<workspace-id>
```

### 12.2 Backend Environment Variables

```bash
# Azure Authentication
AZURE_TENANT_ID=<tenant-id>
AZURE_CLIENT_ID=<client-id>
AZURE_CLIENT_SECRET=<from-key-vault>

# Database
SQL_SERVER=<server>.database.windows.net
SQL_DATABASE=<database-name>
SQL_USERNAME=<admin-user>
SQL_PASSWORD=<from-key-vault>

# Plaid
PLAID_CLIENT_ID=<plaid-client-id>
PLAID_SECRET=<from-key-vault>
PLAID_ENV=sandbox|development|production

# Claude AI
ANTHROPIC_API_KEY=<from-key-vault>

# Security
REQUIRE_AUTH=true
ALLOWED_USERS=user1@domain.com,user2@domain.com
ENCRYPTION_KEY=<from-key-vault>
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Monitoring
APPLICATIONINSIGHTS_CONNECTION_STRING=<connection-string>
```

---

## Appendix A: API Reference

See the API endpoints table in Section 5.3 for complete endpoint documentation.

## Appendix B: Database Schema SQL

See the database/ directory for complete schema definitions.

## Appendix C: Security Audit Report

See `backend/tests/security/SECURITY_AUDIT_REPORT.md` for the OWASP Top 10 compliance report.

---

*Document generated: February 5, 2026*
