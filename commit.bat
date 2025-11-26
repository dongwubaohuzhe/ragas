@echo off
REM Git commit script for RAGAS Evaluation Project
REM This script adds all files and commits them

echo ================================================
echo Committing changes to Git
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
echo Current git status:
git status --short
echo.

REM Commit changes
echo Committing changes...
git commit -m "Add RAGAS evaluation tool with connection testing and strict dependencies

- Added RAGAS evaluation tool with Streamlit UI
- Implemented connection testing for API and Bedrock
- Added strict dependency constraints for faster installation
- Included comprehensive documentation and setup scripts
- Added example test plan and configuration files"

if %errorlevel% equ 0 (
    echo.
    echo ================================================
    echo Commit completed successfully!
    echo ================================================
    echo.
    echo To push to GitHub, run:
    echo   git remote add origin https://github.com/dongwubaohuzhe/ragas.git
    echo   git push -u origin main
    echo.
) else (
    echo.
    echo ERROR: Commit failed.
    echo Please check git status and try again.
    pause
    exit /b 1
)

pause

