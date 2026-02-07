---
name: gitsync
description: Safely sync code to GitHub - runs tests, scans for secrets, and commits with user approval
---

# Git Sync Skill

When the user runs `/gitsync`, follow these steps in order. **Always ask for user confirmation before committing.**

---

## Step 1: Run All Tests

First, ensure all tests pass before considering a commit.

### Backend Tests (Python)
```bash
cd "C:\Users\munge\Claude Projects\Family Wealth Management\backend"
python -m pytest tests/ -v
```

### Frontend Tests (React)
```bash
cd "C:\Users\munge\Claude Projects\Family Wealth Management\frontend"
npm test -- --watchAll=false
```

### Report Test Results

Display a summary table:
```
## Test Results

| Component | Result | Details |
|-----------|--------|---------|
| Backend   | ✅ PASSED / ❌ FAILED | X passed, Y failed |
| Frontend  | ✅ PASSED / ❌ FAILED | X passed, Y failed |
```

**If any tests fail:** Stop here and report the failures. Do NOT proceed to Step 2.

---

## Step 2: Scan for Secrets

Scan the entire codebase for potential secrets that should not be committed.

### Patterns to Search For

Run these searches and collect results:

```bash
cd "C:\Users\munge\Claude Projects\Family Wealth Management"

# Search for API keys
grep -r --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" --include="*.md" \
  -E "sk-ant-api|sk-[a-zA-Z0-9]{20,}" . 2>/dev/null | grep -v node_modules | grep -v venv | grep -v ".example"

# Search for Plaid secrets (actual values, not env var references)
grep -r --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" --include="*.md" \
  -E "['\"][a-f0-9]{30,}['\"]" . 2>/dev/null | grep -v node_modules | grep -v venv | grep -v ".example" | grep -i -E "plaid|secret"

# Search for hardcoded passwords
grep -r --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" --include="*.md" \
  -E "password\s*[:=]\s*['\"][^'\"]{8,}['\"]" . 2>/dev/null | grep -v node_modules | grep -v venv | grep -v ".example" | grep -v "test" | grep -v "YOUR_"

# Search for Azure/AWS keys
grep -r --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" --include="*.md" \
  -E "AKIA[0-9A-Z]{16}|[a-zA-Z0-9+/]{40,}==" . 2>/dev/null | grep -v node_modules | grep -v venv | grep -v ".example"

# Search for personal identifiers that should be generic
grep -r --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" --include="*.md" \
  -E "fwm-(func|sql|cosmos|keyvault|storage)-[a-z]+" . 2>/dev/null | grep -v node_modules | grep -v venv | grep -v "YOUR_INITIALS" | grep -v ".example"
```

### Check .gitignore Protection

Verify sensitive files are protected:

```bash
cd "C:\Users\munge\Claude Projects\Family Wealth Management"

# These should return the filename (meaning they ARE ignored)
git check-ignore backend/local.settings.json
git check-ignore frontend/.env
git check-ignore .claude/settings.local.json
```

### Report Security Scan Results

Display results in this format:

```
## Security Scan Results

### Potential Secrets Found
| File | Issue | Line |
|------|-------|------|
| (list any findings or "None found") |

### Protected Files Status
| File | Status |
|------|--------|
| backend/local.settings.json | ✅ Protected by .gitignore / ⚠️ NOT PROTECTED |
| frontend/.env | ✅ Protected by .gitignore / ⚠️ NOT PROTECTED |
| .claude/settings.local.json | ✅ Protected by .gitignore / ⚠️ NOT PROTECTED |

### Scan Summary
- [ ] No API keys found in code
- [ ] No hardcoded passwords found
- [ ] No personal resource names found
- [ ] All sensitive files protected by .gitignore
```

**If any secrets are found:** Stop here and report. Do NOT proceed to Step 3.

---

## Step 3: Show Git Status

Show what will be committed:

```bash
cd "C:\Users\munge\Claude Projects\Family Wealth Management"
git status
```

Display the results:

```
## Files to be Committed

### New Files
- file1.py
- file2.ts

### Modified Files
- file3.py
- file4.tsx

### Deleted Files
- file5.js
```

**Verify:** None of these files should be:
- `local.settings.json`
- `.env`
- `settings.local.json`
- Any file containing secrets

---

## Step 4: Ask for User Confirmation

**Always ask the user before committing.** Display this summary and question:

```
## Pre-Commit Summary

| Check | Status |
|-------|--------|
| Backend Tests | ✅ Passed (X tests) |
| Frontend Tests | ✅ Passed (X tests) |
| Secret Scan | ✅ Clean |
| Sensitive Files | ✅ Protected |

### Files to Commit
- List of files...

---

**Ready to commit and push to GitHub?**

Please provide a commit message, or type "cancel" to abort.
```

---

## Step 5: Commit and Push (Only After User Approval)

Only proceed if the user provides a commit message.

```bash
cd "C:\Users\munge\Claude Projects\Family Wealth Management"

# Stage all changes
git add .

# Commit with user's message
git commit -m "USER_PROVIDED_MESSAGE"

# Push to GitHub
git push origin main
```

### Report Final Status

```
## Git Sync Complete

✅ Committed: "USER_PROVIDED_MESSAGE"
✅ Pushed to: origin/main

View on GitHub: https://github.com/smunge92/family-wealth-management
```

---

## Error Handling

### If Tests Fail
```
❌ Git Sync Aborted

Tests failed. Please fix the following issues before syncing:

[Show failed test details]
```

### If Secrets Found
```
❌ Git Sync Aborted

Potential secrets detected in the following files:

[Show files with secrets]

Please remove these secrets before syncing. Remember:
- Use environment variables for secrets
- Add sensitive files to .gitignore
- Use placeholders like YOUR_API_KEY in documentation
```

### If User Cancels
```
Git Sync cancelled. No changes were committed.
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `/gitsync` | Run full sync (tests → scan → commit) |
| `/test` | Run tests only |
| `git status` | See pending changes |
| `git diff` | See detailed changes |
