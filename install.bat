@echo off
REM UV installer script for RAGAS Evaluation Project
REM Installs UV if not present, then installs project dependencies

echo ================================================
echo RAGAS Evaluation Project - UV Installation
echo ================================================
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check if UV is installed (try direct command first)
where uv >nul 2>&1
if %errorlevel% equ 0 (
    echo UV is already installed!
    uv --version
    echo.
    echo Running uv sync to install project dependencies...
    uv sync
    goto :end
)

REM Check if UV is installed via Python 3.12
py -3.12 -m uv --version >nul 2>&1
if %errorlevel% equ 0 (
    echo UV is already installed via Python 3.12!
    py -3.12 -m uv --version
    echo.
    echo Running uv sync to install project dependencies...
    py -3.12 -m uv sync
    goto :end
)

REM Check if UV is installed via default Python
python -m uv --version >nul 2>&1
if %errorlevel% equ 0 (
    echo UV is already installed via Python!
    python -m uv --version
    echo.
    echo Running uv sync to install project dependencies...
    python -m uv sync
    goto :end
)

echo UV is not installed. Installing UV...
echo.

REM Try to install UV using PowerShell first
echo Attempting to install UV via PowerShell...
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex" 2>nul

REM Check if PowerShell installation was successful
where uv >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo UV installed successfully via PowerShell!
    uv --version
    echo.
    echo Installing project dependencies...
    uv sync
    if %errorlevel% equ 0 (
        goto :end
    ) else (
        echo ERROR: Failed to sync dependencies.
        pause
        exit /b 1
    )
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
        echo Installing project dependencies...
        py -3.12 -m uv sync
        if %errorlevel% equ 0 (
            goto :end
        ) else (
            echo ERROR: Failed to sync dependencies.
            pause
            exit /b 1
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
        echo Installing project dependencies...
        python -m uv sync
        if %errorlevel% equ 0 (
            goto :end
        ) else (
            echo ERROR: Failed to sync dependencies.
            pause
            exit /b 1
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
echo   5. Then run: install.bat again
echo.
pause
exit /b 1

:end
echo.
echo ================================================
echo Setup completed!
echo ================================================
echo.
echo To start the application, run: start.bat
echo.
pause

