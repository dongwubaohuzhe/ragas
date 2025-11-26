@echo off
echo Setting up Python 3.12 virtual environment...

REM Check if Python 3.12 is available
py -3.12 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python 3.12 not found. Trying default Python...
    python --version
    python -m venv .venv
) else (
    echo Creating virtual environment with Python 3.12...
    py -3.12 -m venv .venv
)

if %errorlevel% equ 0 (
    echo.
    echo Virtual environment created successfully!
    echo.
    echo To activate the virtual environment, run:
    echo   .venv\Scripts\activate.bat
    echo.
    echo Then install dependencies with:
    echo   pip install -r requirements.txt
) else (
    echo Failed to create virtual environment.
    exit /b 1
)

