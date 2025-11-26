@echo off
REM Git commit and push script for RAGAS Evaluation Project
REM This script commits all changes and pushes to GitHub

echo ================================================
echo Committing and Pushing to GitHub
echo ================================================
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check if git is initialized
if not exist ".git" (
    echo Initializing git repository...
    git init
    echo.
)

REM Add all files
echo Adding all files to git...
git add .

REM Show status
echo.
echo Files to be committed:
git status --short
echo.

REM Commit changes
echo Committing changes...
git commit -m "Add RAGAS evaluation tool with UV setup and connection testing

- Migrated to UV package manager for conflict-free installation
- Added pyproject.toml with automatic dependency resolution
- Implemented connection testing for API and Bedrock
- Added comprehensive error handling and logging
- Included example test plan and configuration files
- Updated all documentation and setup scripts
- Removed venv/requirements.txt in favor of UV"

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Commit failed.
    echo Please check git status and try again.
    pause
    exit /b 1
)

echo.
echo Commit completed successfully!
echo.

REM Check if remote exists
git remote get-url origin >nul 2>&1
if %errorlevel% neq 0 (
    echo Adding remote repository...
    git remote add origin https://github.com/dongwubaohuzhe/ragas.git
) else (
    echo Remote repository already configured.
    git remote set-url origin https://github.com/dongwubaohuzhe/ragas.git
)

echo.
echo Pushing to GitHub...
echo.

REM Try to push to main branch first
git push -u origin main 2>nul
if %errorlevel% equ 0 (
    echo.
    echo ================================================
    echo Successfully pushed to GitHub!
    echo ================================================
    echo.
    echo Repository: https://github.com/dongwubaohuzhe/ragas
    echo.
    goto :end
)

REM Try master branch if main failed
git push -u origin master 2>nul
if %errorlevel% equ 0 (
    echo.
    echo ================================================
    echo Successfully pushed to GitHub!
    echo ================================================
    echo.
    echo Repository: https://github.com/dongwubaohuzhe/ragas
    echo.
    goto :end
)

REM Push failed
echo.
echo ERROR: Push failed.
echo.
echo This might be because:
echo   1. You need to authenticate (use Personal Access Token)
echo   2. The remote branch doesn't exist yet
echo   3. You need to pull first
echo.
echo To push manually, run:
echo   git push -u origin main
echo.
echo Or if using master:
echo   git push -u origin master
echo.

:end
pause

