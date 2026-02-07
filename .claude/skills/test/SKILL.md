---
name: test
description: Run tests for backend (Python) and frontend (React)
---

# Run Tests

When the user runs /test, follow these steps:

## Determine what to test

Ask the user or detect automatically:
- `backend` - Run Python tests
- `frontend` - Run React/JavaScript tests
- `all` - Run both

## Backend Tests (Python)

```bash
cd "C:\Users\munge\Claude Projects\Family Wealth Management\backend"
.\venv\Scripts\python.exe -m pytest tests/ -v
```

If pytest isn't installed:
```bash
.\venv\Scripts\pip.exe install pytest pytest-asyncio
```

## Frontend Tests (React)

```bash
cd "C:\Users\munge\Claude Projects\Family Wealth Management\frontend"
npm test -- --watchAll=false
```

## Report Results

After running tests:
1. Show pass/fail count
2. List any failed tests with error messages
3. Suggest fixes for failures if possible

## Quick Commands

- `/test backend` - Only Python tests
- `/test frontend` - Only React tests
- `/test all` - Run everything
