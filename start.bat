@echo off
REM Start script for RAGAS Evaluation Project using UV
REM This script is location-aware and will work from any location

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Change to the script directory (ensures we're in the project root)
cd /d "%SCRIPT_DIR%"

REM Check if UV is installed (try direct command first)
where uv >nul 2>&1
if %errorlevel% equ 0 (
    set UV_CMD=uv
    goto :uv_found
)

REM Check if UV is installed via Python 3.12
py -3.12 -m uv --version >nul 2>&1
if %errorlevel% equ 0 (
    set UV_CMD=py -3.12 -m uv
    goto :uv_found
)

REM Check if UV is installed via default Python
python -m uv --version >nul 2>&1
if %errorlevel% equ 0 (
    set UV_CMD=python -m uv
    goto :uv_found
)

REM UV not found
echo ERROR: UV is not installed!
echo.
echo Please install UV first by running: install.bat
echo.
echo Or install manually:
echo   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
echo   Or: py -3.12 -m pip install uv
echo.
pause
exit /b 1

:uv_found

REM Check if .venv exists (created by uv sync)
if not exist ".venv" (
    echo Virtual environment not found!
    echo.
    echo Please run install.bat first to set up the project.
    echo.
    pause
    exit /b 1
)

echo ================================================
echo Starting RAGAS Evaluation Tool with UV...
echo ================================================
echo.
echo Project directory: %SCRIPT_DIR%
echo.

REM Check if the main application file exists
if not exist "streamlit_ragas_eval.py" (
    echo ERROR: streamlit_ragas_eval.py not found!
    echo.
    echo Please ensure you're running this from the project directory.
    echo.
    pause
    exit /b 1
)

REM Run the Streamlit application using UV
echo Launching Streamlit application...
echo.
%UV_CMD% run streamlit run streamlit_ragas_eval.py

REM If streamlit exits, keep the window open to see any error messages
if %errorlevel% neq 0 (
    echo.
    echo Application exited with an error.
    pause
)

