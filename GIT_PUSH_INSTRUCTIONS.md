# How to Push Code to GitHub

Follow these steps to push your code to: https://github.com/dongwubaohuzhe/ragas

## Option 1: If Git is Already Initialized

Open Command Prompt or PowerShell in the project directory (`D:\ws\ragas`) and run:

```bash
# Check current status
git status

# Add all files
git add .

# Commit changes
git commit -m "Initial commit: RAGAS evaluation tool with connection testing"

# Add remote (if not already added)
git remote add origin https://github.com/dongwubaohuzhe/ragas.git

# Or if remote exists, update it
git remote set-url origin https://github.com/dongwubaohuzhe/ragas.git

# Push to GitHub
git push -u origin main
```

If your default branch is `master` instead of `main`:
```bash
git push -u origin master
```

## Option 2: First Time Setup (Git Not Initialized)

```bash
# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: RAGAS evaluation tool with connection testing"

# Add remote repository
git remote add origin https://github.com/dongwubaohuzhe/ragas.git

# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

## Option 3: Using GitHub CLI (gh)

If you have GitHub CLI installed:

```bash
gh repo create dongwubaohuzhe/ragas --public --source=. --remote=origin --push
```

## Authentication

If you're prompted for credentials:

1. **Personal Access Token**: Use a GitHub Personal Access Token instead of password
   - Go to: https://github.com/settings/tokens
   - Generate new token with `repo` scope
   - Use token as password when prompted

2. **SSH Key**: Set up SSH keys for passwordless authentication
   ```bash
   git remote set-url origin git@github.com:dongwubaohuzhe/ragas.git
   ```

## Files to Push

The following files will be pushed:
- ✅ All Python files (.py)
- ✅ Configuration files (requirements.txt, .gitignore, etc.)
- ✅ Batch files (.bat)
- ✅ Documentation (README.md)
- ✅ Example files (example_test_plan.csv)
- ✅ .env.example (template file)

The following will be ignored (as per .gitignore):
- ❌ .venv/ (virtual environment)
- ❌ .env (environment variables - contains secrets)
- ❌ __pycache__/ (Python cache)
- ❌ *.log (log files)
- ❌ ragasv1.zip (if you want to exclude it, add to .gitignore)

## Troubleshooting

### Error: "remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/dongwubaohuzhe/ragas.git
```

### Error: "failed to push some refs"
```bash
# Pull first, then push
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### Error: "authentication failed"
- Use Personal Access Token instead of password
- Or set up SSH keys

### Check if .env.example exists
If you want to include .env.example, make sure it exists:
```bash
# If it doesn't exist, create it from the template mentioned in README
```

