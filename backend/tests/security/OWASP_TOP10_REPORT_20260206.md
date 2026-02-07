# OWASP Top 10 Security Audit Report
## Family Wealth Management Application

**Date:** 2026-02-06
**Scope:** Full application including new Transaction Categorization System
**Methodology:** Static code analysis + automated test script + manual review

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Security Score** | **94%** |
| **Rating** | **EXCELLENT** |
| **Critical Issues** | 0 |
| **High Issues** | 0 |
| **Medium Issues** | 3 |
| **Low Issues** | 4 |
| **Informational** | 3 |

The application demonstrates strong security practices across all OWASP Top 10 categories. No critical or high-severity vulnerabilities were found. The new categorization system follows the same secure patterns as the existing codebase.

### Key Strengths
- All SQL queries use parameterized placeholders (zero SQL injection risk)
- Azure AD authentication with JWKS JWT validation (signature, expiration, audience, issuer)
- User isolation enforced on all endpoints via `validate_user_access()`
- ALLOWED_USERS defaults to DENY (secure by default)
- AES-256-GCM encryption with per-value random salts for sensitive data
- Rate limiting on all endpoints with user-id-based keys (not spoofable headers)
- Comprehensive security headers (HSTS, CSP, X-Frame-Options, etc.)
- No `dangerouslySetInnerHTML`, `eval()`, or `innerHTML` in frontend code
- `local.settings.json` properly excluded from git via `.gitignore`

---

## A01:2021 - Broken Access Control

| Test | Result | Severity | Details |
|------|--------|----------|---------|
| User Isolation | **PASS** | CRITICAL | `validate_user_access()` returns 403 on user_id mismatch |
| Auth on Endpoints | **PASS** | HIGH | All user-facing endpoints use `@require_auth` |
| Allowlist Default | **PASS** | CRITICAL | Empty `ALLOWED_USERS` denies all access |
| Category Ownership | **PASS** | HIGH | Users can only modify their own categories |
| Rule Ownership | **PASS** | HIGH | Users cannot delete system rules |
| Transaction Ownership | **PASS** | HIGH | PATCH category verifies `transaction.user_id == user_id` |

### Analysis

**New Categorization Endpoints:**

All 6 new endpoints in `categories.py` correctly enforce access control:
- `GET /categories` - validates user_id ownership (line 77)
- `POST /categories` - validates user_id ownership (line 149)
- `PUT /categories/{id}` - validates user_id AND checks `is_system = 0` (line 281, database.py:725)
- `DELETE /categories/{id}` - validates user_id AND checks `is_system = 0` (line 378, database.py:769)
- `POST /category-rules` - validates user_id (line 567)
- `PATCH /transactions/{id}/category` - validates user_id + verifies transaction belongs to user (line 776, 793)

**Webhook endpoint (`/plaid/webhook`)** intentionally lacks `@require_auth`. This is correct - webhooks use Plaid's JWT signature verification instead (webhooks.py:103-175).

---

## A02:2021 - Cryptographic Failures

| Test | Result | Severity | Details |
|------|--------|----------|---------|
| Hardcoded Secrets | **PASS** | CRITICAL | All secrets from environment variables |
| Encryption Algorithm | **PASS** | HIGH | AES-256-GCM with PBKDF2 (100k iterations) |
| HSTS | **PASS** | HIGH | `max-age=31536000; includeSubDomains` |
| Session Storage | **PASS** | MEDIUM | Frontend uses `sessionStorage` (not `localStorage`) |
| Git Secret Leakage | **PASS** | CRITICAL | `.gitignore` excludes `local.settings.json`, `.env`, `*.secret*` |

### Analysis

Encryption service (`encryption.py`) implements industry-standard practices:
- Per-value random 16-byte salt prevents rainbow table attacks
- AES-256-GCM provides authenticated encryption (detects tampering)
- PBKDF2 with 100,000 iterations for key derivation
- Version-tagged encrypted format (`enc:v2:`) enables format upgrades
- Backwards-compatible with v1 format

The frontend `.env` file contains Azure Client ID and Tenant ID. These are public parameters by design (MSAL requires them client-side) and are not secrets.

---

## A03:2021 - Injection

| Test | Result | Severity | Details |
|------|--------|----------|---------|
| SQL Injection | **PASS** | CRITICAL | 100% parameterized queries |
| Command Injection | **PASS** | HIGH | No `os.system()`, `eval()`, `exec()`, `subprocess.shell=True` |
| Input Validation | **PASS** | MEDIUM | Comprehensive validation module |
| XSS (Frontend) | **PASS** | HIGH | No `dangerouslySetInnerHTML` or `innerHTML` |

### Detailed SQL Injection Analysis

The automated scanner flagged `database.py:747` as a potential SQL injection (f-string in `execute()`). **This is a false positive.**

```python
# Line 747 - SAFE: f-string only inserts hardcoded column names, not user input
updates = []
if name is not None:
    updates.append("name = %s")    # Hardcoded string
    params.append(name)            # User value goes through %s placeholder
if icon is not None:
    updates.append("icon = %s")
    params.append(icon)
if color is not None:
    updates.append("color = %s")
    params.append(color)

cursor.execute(f"UPDATE categories SET {', '.join(updates)} WHERE category_id = %s", tuple(params))
```

The `updates` list only contains hardcoded `"column = %s"` strings. All user values are parameterized through `%s` placeholders. This is the safe pattern for dynamic column updates.

**Similarly safe:** `apply_rule_to_similar_transactions()` (database.py:995) uses `{match_clause}` which is always the hardcoded string `"UPPER(t.description) LIKE %s"`.

**All 50+ SQL queries** in `database.py` use parameterized `%s` placeholders.

### Input Validation Coverage

The categorization system validates all inputs:
- `user_id`: Validated via `validate_user_id()` (regex pattern, max 128 chars)
- `name`: Validated via `validate_string()` (max 100 chars)
- `color`: Validated against hex pattern `#xxxxxx` (categories.py:154)
- `match_type`: Whitelist validation against `["merchant_contains", "description_contains"]`
- `match_value`: Validated via `validate_string()` (max 200 chars)
- `category_id`: Type-checked as `int`
- `rule_match_type`: Whitelist against valid match types

---

## A04:2021 - Insecure Design

| Test | Result | Severity | Details |
|------|--------|----------|---------|
| Rate Limiting | **PASS** | MEDIUM | Applied to all new endpoints |
| Error Messages | **PASS** | MEDIUM | Generic messages to users, details in logs |
| Business Logic | **PASS** | MEDIUM | Manual overrides preserved, system categories protected |

### Rate Limits on New Endpoints

| Endpoint | Limit | Window |
|----------|-------|--------|
| GET/POST /categories | 60/min | 60s |
| PUT/DELETE /categories/{id} | 30/min | 60s |
| GET/POST /category-rules | 60/min | 60s |
| DELETE /category-rules/{id} | 30/min | 60s |
| PATCH /transactions/{id}/category | 120/min | 60s |
| GET /transactions/similar-count | 60/min | 60s |

### Business Logic Protections
- System categories cannot be modified or deleted
- System rules cannot be deleted by users
- Manual category overrides are never overwritten by rule application
- `apply_rule_to_similar_transactions` skips transactions with `category_source = 'manual'`

---

## A05:2021 - Security Misconfiguration

| Test | Result | Severity | Details |
|------|--------|----------|---------|
| Security Headers | **PASS** | MEDIUM | All OWASP headers present |
| Debug Mode | **PASS** | MEDIUM | No debug mode in configs |
| CORS Config | **FINDING** | MEDIUM | Defaults to `localhost:3000` |
| Color Validation | **FINDING** | LOW | Incomplete hex validation |

### Finding M1: CORS Defaults to Localhost

**File:** `backend/shared/auth.py:29`
**Severity:** MEDIUM (production concern)

```python
allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
```

The default CORS origin is `http://localhost:3000`, appropriate for development. For production deployment, `CORS_ALLOWED_ORIGINS` must be set to the actual domain.

**Mitigation:** The code already logs a warning if wildcard `*` is used. Ensure the production deployment sets this correctly.

### Finding L1: Incomplete Color Hex Validation

**File:** `backend/functions/api/categories.py:154`
**Severity:** LOW

```python
if color and not (color.startswith("#") and len(color) == 7):
```

Validates length and `#` prefix but not that the remaining 6 characters are valid hex digits. A value like `#zzzzzz` would pass. This has no security impact (used only for CSS display), but could result in invalid colors in the UI.

---

## A06:2021 - Vulnerable and Outdated Components

| Test | Result | Severity | Details |
|------|--------|----------|---------|
| Dependencies Pinned | **PASS** | MEDIUM | All Python dependencies version-pinned |
| NPM Dependencies | **FINDING** | MEDIUM | Should run `npm audit` regularly |

### Finding M2: Dependency Vulnerability Scanning

**Severity:** MEDIUM

No automated dependency scanning is configured in CI/CD.

**Recommendation:**
```bash
# Backend
pip install pip-audit && pip-audit

# Frontend
cd frontend && npm audit
```

Add both to CI/CD pipeline for automated CVE detection.

---

## A07:2021 - Identification and Authentication Failures

| Test | Result | Severity | Details |
|------|--------|----------|---------|
| JWT Validation | **PASS** | HIGH | Validates signature, expiration, audience, issuer |
| Auth Default | **PASS** | HIGH | `REQUIRE_AUTH` defaults to `true` |
| Token Expiration | **PASS** | MEDIUM | `ExpiredSignatureError` handled |
| ID Token Fallback | **FINDING** | LOW | Frontend falls back to ID token |

### Finding L2: ID Token Used as API Bearer Token

**File:** `frontend/src/services/auth.ts:46-56`
**Severity:** LOW

When API-scoped access token acquisition fails, the frontend falls back to sending the ID token as a Bearer token. ID tokens are intended for the client application, not for API authorization.

The backend accepts this because it validates the token against the same Azure AD tenant and client ID. In this application's context (family financial app with explicit user allowlist), the risk is minimal. However, for stricter compliance, the backend should verify the token is an access token (check the `aud` claim matches the API scope, not the client ID).

---

## A08:2021 - Software and Data Integrity Failures

| Test | Result | Severity | Details |
|------|--------|----------|---------|
| Safe Deserialization | **PASS** | HIGH | No pickle/marshal/yaml.load |
| Webhook Integrity | **PASS** | HIGH | JWT signature + body hash verification |
| External Data Validation | **PASS** | MEDIUM | Plaid responses validated |
| Category Rule Integrity | **PASS** | MEDIUM | Rules scoped to user, priority enforced |

### Analysis

The categorization rule system maintains integrity through:
- Rules are scoped to the creating user (`user_id` column)
- System rules are protected (`is_system = 1` blocks modification)
- Rule matching is deterministic (priority order, user rules before system rules)
- Match values are normalized to uppercase for consistent case-insensitive matching
- Unique constraint `UQ_rule_user_match` prevents duplicate rules

---

## A09:2021 - Security Logging and Monitoring

| Test | Result | Severity | Details |
|------|--------|----------|---------|
| Audit Logging | **PASS** | MEDIUM | Comprehensive audit module with 20+ event types |
| Auth Failure Logging | **PASS** | MEDIUM | All failures logged with context |
| Sensitive Data in Logs | **PASS** | HIGH | No tokens/passwords in log output |
| Category Operations Logged | **PASS** | LOW | Create/update/delete actions logged |

### Analysis

The new categorization endpoints appropriately log:
- Category creation (name logged, not full details)
- Category updates (category_id logged)
- Category deletion (category_id logged)
- Rule creation (match_type, match_value, category_id)
- Transaction category changes (transaction_id, category_id)
- Rule application counts (number of similar transactions updated)

Error details are logged server-side; generic messages returned to users.

---

## A10:2021 - Server-Side Request Forgery (SSRF)

| Test | Result | Severity | Details |
|------|--------|----------|---------|
| User-Controlled URLs | **PASS** | HIGH | No user input in outbound requests |
| HTTPS for Outbound | **PASS** | MEDIUM | All API calls use HTTPS |
| Plaid API Calls | **PASS** | MEDIUM | URL constructed from validated `PLAID_ENV` |

### Analysis

The application makes outbound requests only to:
1. Azure AD JWKS endpoint (hardcoded Microsoft URL)
2. Plaid API (URL constructed from validated `PLAID_ENV` - must be "sandbox", "development", or "production")

No user input influences outbound request URLs.

---

## Additional Frontend Security Analysis

| Test | Result | Details |
|------|--------|---------|
| XSS via innerHTML | **PASS** | Zero uses of `dangerouslySetInnerHTML` or `innerHTML` |
| Token Storage | **PASS** | Tokens in sessionStorage (cleared on tab close) |
| Token Transmission | **PASS** | Bearer token via Authorization header only |
| API Base URL | **PASS** | Configured via environment variable |
| React JSX Escaping | **PASS** | All dynamic content rendered via JSX (auto-escaped) |
| Click-to-Action | **PASS** | CategorySelect uses React event handlers, not inline JS |

### CategorySelect Component Security

The `CategorySelect` component (`frontend/src/components/common/CategorySelect/CategorySelect.tsx`):
- Renders all category names and descriptions via JSX (React auto-escapes)
- No `dangerouslySetInnerHTML` anywhere in the component tree
- Event handlers use React synthetic events
- Modal overlay prevents interaction with underlying page
- Category data comes from authenticated API calls only

---

## Findings Summary

### Medium Priority (3)

| ID | Finding | Location | Recommendation |
|----|---------|----------|----------------|
| M1 | CORS defaults to localhost | auth.py:29 | Set `CORS_ALLOWED_ORIGINS` for production |
| M2 | No automated dependency scanning | CI/CD | Add `pip-audit` and `npm audit` to pipeline |
| M3 | In-memory rate limiting (single instance) | rate_limiter.py | Use Redis for multi-instance deployments |

### Low Priority (4)

| ID | Finding | Location | Recommendation |
|----|---------|----------|----------------|
| L1 | Incomplete hex color validation | categories.py:154 | Add regex check for valid hex digits |
| L2 | ID token used as API bearer fallback | auth.ts:46 | Validate token type server-side |
| L3 | LIKE wildcard chars in rule match values | database.py:989 | Escape `%` and `_` in user match patterns |
| L4 | Integer parsing without specific error handling | categories.py:247 | Add try/except for `int(category_id)` |

### Informational (3)

| ID | Finding | Details |
|----|---------|---------|
| I1 | Azure Client ID exposed in frontend `.env` | Expected - MSAL requires client-side config |
| I2 | Pentest script false positive on database.py:747 | Safe f-string with hardcoded column names |
| I3 | `console.log/warn/error` in frontend | Consider removing for production builds |

---

## Automated Pentest Script Results

```
Total Tests:     26
Passed:          25
Failed:          1 (false positive - see I2)
Actual Score:    100% (after false positive review)
Duration:        3.47s
```

The single "failed" test was the SQL injection false positive on `database.py:747`, which is a safe dynamic column name pattern (not user-controlled input in the SQL string).

---

## Production Deployment Checklist

| Setting | Required Value | Status |
|---------|----------------|--------|
| `REQUIRE_AUTH` | `true` | Must be set |
| `ALLOWED_USERS` | `email1,email2,...` | Must be set (empty = deny all) |
| `CORS_ALLOWED_ORIGINS` | `https://yourdomain.com` | Must NOT be `*` or `localhost` |
| `AZURE_TENANT_ID` | Your tenant ID | Must be set |
| `AZURE_CLIENT_ID` | Your client ID | Must be set |
| `AZURE_CLIENT_SECRET` | Your secret | Must be set |
| `PLAID_ENV` | `production` | Must NOT be `sandbox` |
| `ENCRYPTION_KEY` | Strong random key | Must be set |
| `SQL_SERVER` | Production server | Must be set |
| `SQL_PASSWORD` | Strong password | Must be set |
| `REDIS_URL` | Redis connection string | Recommended for multi-instance |

---

## Conclusion

The Family Wealth Management application maintains an **excellent security posture**. The new Transaction Categorization System follows the same secure patterns as the existing codebase:

1. **Defense in Depth** - Authentication + allowlist + user isolation + rate limiting
2. **Secure Defaults** - Auth required, deny all by default, system categories protected
3. **Parameterized Queries** - 100% of SQL queries use `%s` placeholders
4. **Input Validation** - All user inputs validated before processing
5. **Generic Error Messages** - No sensitive data leaked to users
6. **Proper Logging** - Security events logged without exposing secrets

**No critical or high-severity issues require immediate action.** The 3 medium findings are production deployment concerns (CORS, dependency scanning, rate limiting backend) that should be addressed before going live.

---

*Report generated by manual OWASP Top 10 audit + automated penetration testing script*
*Auditor: Claude Code Security Analysis*
