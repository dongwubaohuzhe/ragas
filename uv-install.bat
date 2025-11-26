@echo off
REM UV installation script for RAGAS Evaluation Project
REM This script uses UV (fast Python package manager) for installation

echo ================================================
echo RAGAS Evaluation Project - UV Installation
echo ================================================
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check if UV is installed
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo UV is not installed. Attempting to install UV...
    echo.
    
    REM Try to install UV using PowerShell first
    echo Attempting to install UV via PowerShell...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex" 2>nul
    
    REM Check if PowerShell installation was successful
    where uv >nul 2>&1
    if %errorlevel% equ 0 (
        echo.
        echo UV installed successfully via PowerShell!
        goto :uv_installed
    )
    
    REM PowerShell installation failed or blocked, try pip installation
    echo.
    echo PowerShell installation failed or blocked by policy.
    echo Attempting to install UV using pip with Python 3.12...
    echo.
    
    REM Check for Python 3.12
    py -3.12 --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Found Python 3.12, installing UV via pip...
        py -3.12 -m pip install uv
        if %errorlevel% equ 0 (
            echo.
            echo UV installed successfully via pip with Python 3.12!
            echo Note: You may need to use "py -3.12 -m uv" instead of "uv" command.
            echo.
            REM Try to use uv via Python module
            py -3.12 -m uv --version >nul 2>&1
            if %errorlevel% equ 0 (
                set UV_CMD=py -3.12 -m uv
                goto :uv_installed_pip
            )
        )
    )
    
    REM Try with default Python
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo Trying with default Python...
        python -m pip install uv
        if %errorlevel% equ 0 (
            echo.
            echo UV installed successfully via pip with default Python!
            echo Note: You may need to use "python -m uv" instead of "uv" command.
            echo.
            REM Try to use uv via Python module
            python -m uv --version >nul 2>&1
            if %errorlevel% equ 0 (
                set UV_CMD=python -m uv
                goto :uv_installed_pip
            )
        )
    )
    
    REM All installation methods failed
    echo.
    echo ERROR: UV installation failed with all methods.
    echo.
    echo Please install UV manually using one of these methods:
    echo   1. Visit: https://github.com/astral-sh/uv
    echo   2. PowerShell: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo   3. Pip with Python 3.12: py -3.12 -m pip install uv
    echo   4. Pip with default Python: python -m pip install uv
    echo.
    pause
    exit /b 1
)

:uv_installed

echo UV is installed. Checking version...
uv --version
echo.

REM Sync project dependencies (creates .venv automatically if needed)
echo Installing project dependencies with UV...
echo This will automatically resolve compatible versions...
echo.
uv sync --no-install-project
goto :sync_complete

:uv_installed_pip

echo UV is installed via pip. Checking version...
%UV_CMD% --version
echo.

REM Sync project dependencies using Python module
echo Installing project dependencies with UV...
echo This will automatically resolve compatible versions...
echo.
%UV_CMD% sync --no-install-project
goto :sync_complete

:sync_complete

if %errorlevel% equ 0 (
    echo.
    echo ================================================
    echo Installation completed successfully!
    echo ================================================
    echo.
    echo Virtual environment created at: .venv
    echo.
    echo To run the application:
    echo   uv run streamlit run streamlit_ragas_eval.py
    echo.
    echo Or use start.bat
    echo.
) else (
    echo.
    echo ERROR: Installation failed.
    echo Please check the error messages above.
    pause
    exit /b 1
)

pause

