---
name: deploy
description: Deploy backend to Azure Functions and frontend to GitHub Pages
---

# Deployment Workflow

When the user runs /deploy, follow these steps:

## Determine what to deploy

Ask the user:
- `backend` - Deploy Azure Functions
- `frontend` - Deploy to GitHub Pages
- `all` - Deploy everything

## Pre-deployment Checks

1. Ensure all changes are committed (`git status`)
2. Run tests to verify nothing is broken
3. Check Azure CLI is logged in (`az account show`)

## Backend Deployment (Azure Functions)

```bash
cd backend

# Login to Azure if needed
az login

# Deploy to Azure Functions (replace YOUR_INITIALS)
func azure functionapp publish fwm-func-YOUR_INITIALS --python
```

After deployment:
- Verify functions are running: `az functionapp function list --name fwm-func-YOUR_INITIALS --resource-group family-wealth-rg`
- Check logs: `az functionapp log tail --name fwm-func-YOUR_INITIALS --resource-group family-wealth-rg`

## Frontend Deployment (GitHub Pages)

```bash
cd frontend

# Build production version
npm run build

# Deploy to GitHub Pages
npm run deploy
```

Note: Requires `gh-pages` package and GitHub repo configured.

## Post-deployment

1. Test the deployed endpoints
2. Verify frontend loads correctly
3. Check for any console errors
4. Update any environment-specific configs if needed

## Quick Commands

- `/deploy backend` - Only Azure Functions
- `/deploy frontend` - Only GitHub Pages
- `/deploy all` - Deploy everything
