# Family Wealth Management

A personal financial tracking app that connects to your actual bank accounts, syncs transactions automatically, categorizes everything with AI, and gives you charts that actually make sense. Built for families who want to see where their money goes without spreadsheet nightmares.

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## What Does It Do?

- **Auto-syncs your bank accounts** - Chase, Vanguard, Fidelity, Scotia Bank, you name it. Plaid handles the heavy lifting so you don't have to export CSVs like it's 2005.
- **Smart transaction categorization** - A hybrid system that uses rule-based matching AND AI (Claude) to categorize your transactions. It learns your patterns. Yes, it knows about the 3am pizza orders.
- **Interactive dashboards** - Net worth, spending by category, income vs expenses over time, account distribution, monthly trends. All with actual colors and tooltips, not just numbers in a table.
- **AI financial insights** - Flags when a category is eating too much of your budget, tracks your savings rate, spots outlier transactions, and gives month-over-month comparisons. It's like a financial advisor that doesn't charge $200/hour.
- **Family member profiles** - Filter everything by family member. See who's spending what, where.
- **10-year history import** - Upload old bank statements (CSV/Excel) to build out your full financial picture.
- **Secure by default** - Azure AD authentication, Key Vault for secrets, HTTPS-only, CORS lockdown. Only your family gets in.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, TypeScript, Recharts, MSAL.js |
| **Backend** | Python 3.11, Azure Functions v2 (Blueprint pattern) |
| **Database** | Azure SQL (transactions, accounts, categories), Cosmos DB (AI conversations, raw data) |
| **Auth** | Azure AD / Entra ID with MSAL |
| **Bank Sync** | Plaid API (cursor-based incremental sync) |
| **AI** | Anthropic Claude API (categorization + financial insights) |
| **Hosting** | Azure Functions (backend), GitHub Pages (frontend) |
| **Secrets** | Azure Key Vault with managed identity |

---

## Project Structure

```
Family Wealth Management/
├── backend/                    # Azure Functions (Python)
│   ├── functions/              # API endpoints (Blueprints)
│   │   ├── accounts.py         # Account CRUD + Plaid link
│   │   ├── transactions.py     # Transaction sync + query
│   │   ├── categories.py       # Category management
│   │   ├── insights.py         # AI-powered financial insights
│   │   ├── family_members.py   # Family member profiles
│   │   └── ...
│   ├── shared/                 # Shared utilities
│   │   ├── database.py         # SQL connection + parameterized queries
│   │   ├── plaid_client.py     # Plaid API wrapper
│   │   ├── cosmos_client.py    # Cosmos DB operations
│   │   └── auth.py             # Azure AD token validation
│   ├── tests/                  # Backend tests (194 passing)
│   ├── function_app.py         # App entry point
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # React app (TypeScript)
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard/      # Main dashboard with charts
│   │   │   ├── Accounts/       # Account management + Plaid Link
│   │   │   ├── Transactions/   # Transaction list + category editing
│   │   │   ├── Insights/       # AI financial planning
│   │   │   ├── About/          # App info page
│   │   │   └── common/         # Shared components (filters, etc.)
│   │   ├── services/           # API client + auth config
│   │   └── types/              # TypeScript interfaces
│   └── package.json
│
├── database/                   # SQL migrations + schema
│   ├── migrations/             # Sequential migration scripts
│   └── schema/                 # Views + stored procedures
│
├── infrastructure/             # Azure Bicep templates
├── docs/                       # Additional documentation
├── PRODUCTION_DEPLOYMENT_GUIDE.md  # Step-by-step production deployment
├── SECURITY_SETUP.md           # Security configuration reference
└── LICENSE                     # MIT
```

---

## Features In Detail

### Dashboard
Four summary cards (income, expenses, net change, savings rate), account overview, recent transactions, pie charts for spending and account distribution, monthly trend lines, spending-by-category bar charts, income vs expenses over time, and an AI-generated financial insights card. It's a lot. In a good way.

### Transaction Categorization
Uses a three-tier system:
1. **User overrides** - You manually set a category? That wins. Always.
2. **Category rules** - Pattern-based rules that auto-match (e.g., "STARBUCKS" -> Coffee & Tea).
3. **AI fallback** - Claude analyzes the merchant name and picks the best category.

Each category has a custom icon, color, and name. The system tracks where the categorization came from so you always know why something was tagged the way it was.

### Bank Sync
Plaid's cursor-based incremental sync means we only pull new/changed transactions, not the whole history every time. Supports checking, savings, credit cards, investments, loans - basically anything Plaid can connect to.

### Security
- Azure AD enforces who can even log in
- Backend double-checks with an `ALLOWED_USERS` whitelist
- All secrets live in Azure Key Vault (not environment variables, not config files)
- SQL queries are parameterized (no injection here)
- CORS is locked to your frontend domain
- HTTPS-only with TLS 1.2 minimum
- Passed an OWASP Top 10 security audit (94% score, 0 critical/high findings)

---

## Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Azure account** (for Functions, SQL, Cosmos DB, Key Vault, AD)
- **Plaid account** (free for development/sandbox)
- **Anthropic API key** (for AI categorization and insights)
- **Azure CLI** + **Azure Functions Core Tools v4**

### Local Development Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/YOUR_USERNAME/family-wealth-management.git
   cd family-wealth-management
   ```

2. **Backend setup**
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate          # Windows
   # source venv/bin/activate     # Mac/Linux
   pip install -r requirements.txt
   ```

3. **Configure backend secrets**
   ```bash
   cp local.settings.json.example local.settings.json
   ```
   Edit `local.settings.json` with your Azure, Plaid, and Anthropic credentials. This file is gitignored - your secrets never leave your machine.

4. **Frontend setup**
   ```bash
   cd ../frontend
   npm install
   ```

5. **Configure frontend**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your Azure AD client/tenant IDs. Also gitignored.

6. **Run it**
   ```bash
   # Terminal 1 - Backend
   cd backend && func start

   # Terminal 2 - Frontend
   cd frontend && npm start
   ```

   Frontend opens at `http://localhost:3000`. Sign in with your Microsoft account and you're in.

### Azure Resource Setup

You'll need to create these Azure resources:
- **Azure SQL Server + Database** - stores accounts, transactions, categories
- **Cosmos DB** - stores AI conversation history
- **Key Vault** - stores all secrets securely
- **Function App** (Python, Linux, Consumption plan) - runs the backend
- **Azure AD App Registrations** - one for backend API, one for frontend SPA
- **Storage Account** - required by Azure Functions

See [PRODUCTION_DEPLOYMENT_GUIDE.md](PRODUCTION_DEPLOYMENT_GUIDE.md) for detailed step-by-step instructions.

---

## Running Tests

```bash
# Backend tests (194 tests)
cd backend
venv\Scripts\activate
python -m pytest tests/ -v

# Frontend tests
cd frontend
npm test
```

---

## Deployment

- **Backend** deploys to Azure Functions via `func azure functionapp publish`
- **Frontend** deploys to GitHub Pages via `npm run deploy` (uses the `gh-pages` package)

Full deployment guide with checklists: [PRODUCTION_DEPLOYMENT_GUIDE.md](PRODUCTION_DEPLOYMENT_GUIDE.md)

---

## Security Notes

This app handles real financial data. A few things to keep in mind:

- **Never commit secrets.** The `.gitignore` is configured to block `local.settings.json`, `.env` files, credential files, and anything matching `*secret*` or `*apikey*` patterns. Don't fight it.
- **Use Key Vault in production.** Function App settings should reference Key Vault secrets, not contain raw values.
- **Rotate keys regularly.** Especially after any suspected exposure. The deployment guide covers rotation.
- **Restrict access.** Enable "Assignment required" in Azure AD Enterprise Applications so only your family members can sign in.

---

## Cost Estimate

Running this in Azure on a modest setup:

| Resource | Approximate Monthly Cost |
|----------|--------------------------|
| Azure Functions (Consumption) | $0-5 |
| Azure SQL (Basic tier) | $5 |
| Cosmos DB (Serverless) | $1-5 |
| Key Vault | ~$0.03 per 10K operations |
| Storage Account | ~$1 |
| Plaid (Production) | $5-30 depending on linked accounts |
| Anthropic API | Varies by usage |
| **Total** | **~$15-50/month** |

---

## Contributing

This is a personal family project, but if you find it useful and want to contribute, feel free to open an issue or PR. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License - see [LICENSE](LICENSE) for details. Do whatever you want with it.

---

*Built with React, Python, Azure, Plaid, and an unreasonable amount of coffee.*
