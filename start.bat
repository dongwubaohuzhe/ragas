@echo off
REM Start script for RAGAS Evaluation Project
REM This script is location-aware and will work from any location (e.g., desktop shortcut)

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Change to the script directory (ensures we're in the project root)
cd /d "%SCRIPT_DIR%"

REM Check if virtual environment exists
if not exist ".venv" (
    echo ERROR: Virtual environment not found!
    echo.
    echo Please run install.bat first to set up the project.
    echo.
    pause
    exit /b 1
)

REM Check if .venv\Scripts\activate.bat exists
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment appears to be corrupted!
    echo.
    echo Please run install.bat again to recreate it.
    echo.
    pause
    exit /b 1
)

echo ================================================
echo Starting RAGAS Evaluation Tool...
echo ================================================
echo.
echo Project directory: %SCRIPT_DIR%
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check if streamlit is installed
python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Streamlit is not installed!
    echo.
    echo Please run install.bat first to install dependencies.
    echo.
    pause
    exit /b 1
)

REM Check if the main application file exists
if not exist "streamlit_ragas_eval.py" (
    echo ERROR: streamlit_ragas_eval.py not found!
    echo.
    echo Please ensure you're running this from the project directory.
    echo.
    pause
    exit /b 1
)

REM Run the Streamlit application
echo Launching Streamlit application...
echo.
streamlit run streamlit_ragas_eval.py

REM If streamlit exits, keep the window open to see any error messages
if %errorlevel% neq 0 (
    echo.
    echo Application exited with an error.
    pause
)

