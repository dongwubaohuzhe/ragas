#!/usr/bin/env bash
# Start script for RAGAS Evaluation Project (Mac/Unix)
# Location-aware; loads .env then runs Streamlit in the project venv

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Only require .venv (we run streamlit from it); UV in PATH is not required
if [[ ! -d .venv ]]; then
    echo "Virtual environment not found!"
    echo
    echo "Please run ./install.sh first to set up the project."
    echo
    exit 1
fi

if [[ ! -f streamlit_ragas_eval.py ]]; then
    echo "ERROR: streamlit_ragas_eval.py not found!"
    echo "Please ensure you're running this from the project directory."
    exit 1
fi

echo "================================================"
echo "Starting RAGAS Evaluation Tool..."
echo "================================================"
echo
echo "Project directory: $SCRIPT_DIR"
echo

# Activate virtual environment
# shellcheck source=/dev/null
source .venv/bin/activate

# Load optional environment variables from .env (e.g. AWS_PROFILE, AWS_DEFAULT_PROFILE)
if [[ -f .env ]]; then
    echo "Loading environment from .env..."
    set -a
    # shellcheck source=/dev/null
    source ./.env
    set +a
    echo
fi

echo "Launching Streamlit application..."
echo

exec streamlit run streamlit_ragas_eval.py "$@"
