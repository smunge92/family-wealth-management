---
name: commit
description: Git commit workflow - stage changes, create commit with descriptive message
---

# Git Commit Workflow

When the user runs /commit, follow these steps:

1. **Check git status** - Run `git status` to see all modified, added, and untracked files

2. **Show diff** - Run `git diff` to show what changed (staged and unstaged)

3. **Review changes** - Summarize what was changed in plain English

4. **Stage files** - Ask user which files to stage, or stage all with `git add .`

5. **Create commit message** - Generate a descriptive commit message following conventional commits:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `refactor:` for code refactoring
   - `test:` for adding tests
   - `chore:` for maintenance tasks

6. **Commit** - Run `git commit -m "message"` with the generated message

7. **Confirm** - Show the commit hash and summary

## Example commit messages:
- `feat: add Plaid bank account connection`
- `fix: resolve CORS issue in backend API`
- `docs: update README with setup instructions`
