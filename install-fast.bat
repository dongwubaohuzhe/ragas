@echo off
REM Fast installation script with strict dependency constraints
REM This script uses pip's resolver with no cache for faster installation

echo ================================================
echo RAGAS Evaluation Project - Fast Installation
echo ================================================
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check if .venv already exists
if exist ".venv" (
    echo Virtual environment already exists.
    echo.
    choice /C YN /M "Do you want to remove it and create a new one"
    if errorlevel 2 goto :skip_venv_creation
    if errorlevel 1 (
        echo Removing existing virtual environment...
        rmdir /s /q .venv
        echo.
    )
)

:skip_venv_creation

REM Only create venv if it doesn't exist
if not exist ".venv" (
    REM Try to use Python 3.12, fall back to default Python
    echo Checking for Python 3.12...
    py -3.12 --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Found Python 3.12!
        echo Creating virtual environment with Python 3.12...
        py -3.12 -m venv .venv
    ) else (
        echo Python 3.12 not found. Checking for default Python...
        python --version >nul 2>&1
        if %errorlevel% equ 0 (
            python --version
            echo Creating virtual environment with default Python...
            python -m venv .venv
        ) else (
            echo ERROR: Python is not installed or not in PATH.
            echo Please install Python 3.12 or later and try again.
            pause
            exit /b 1
        )
    )

    if not exist ".venv" (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo.
    echo Virtual environment created successfully!
) else (
    echo.
    echo Using existing virtual environment.
)
echo.
echo Activating virtual environment and installing dependencies...
echo Using fast installation mode (no cache, strict versions)...
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Upgrade pip and install build tools first
echo Upgrading pip and build tools...
python -m pip install --upgrade pip setuptools wheel --no-cache-dir >nul 2>&1

REM Install requirements with optimizations
echo Installing dependencies with strict version constraints...
echo This may take a few minutes...
python -m pip install -r requirements.txt --no-cache-dir --no-warn-script-location

if %errorlevel% equ 0 (
    echo.
    echo ================================================
    echo Installation completed successfully!
    echo ================================================
    echo.
    echo You can now run the application using start.bat
    echo.
) else (
    echo.
    echo ERROR: Failed to install dependencies.
    echo.
    echo Trying with legacy resolver...
    python -m pip install -r requirements.txt --no-cache-dir --use-deprecated=legacy-resolver
    if %errorlevel% equ 0 (
        echo.
        echo Installation completed with legacy resolver!
    ) else (
        echo.
        echo ERROR: Installation failed even with legacy resolver.
        echo Please check requirements.txt and try again.
        pause
        exit /b 1
    )
)

pause

