#!/usr/bin/env bash
# UV installation script for RAGAS Evaluation Project (Mac/Unix)
# Uses the official UV installer, then syncs project dependencies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "RAGAS Evaluation Project - UV Installation"
echo "================================================"
echo

# Ensure we have a usable PATH (installer may add ~/.local/bin)
export PATH="${HOME}/.local/bin:${PATH}"

# Check if UV is already installed
if command -v uv &>/dev/null; then
    echo "UV is already installed."
    uv --version
    echo
else
    echo "UV is not installed. Installing UV..."
    echo
    if command -v curl &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="${HOME}/.local/bin:${PATH}"
    elif command -v wget &>/dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh
        export PATH="${HOME}/.local/bin:${PATH}"
    else
        echo "ERROR: Neither curl nor wget found. Please install UV manually:"
        echo "  https://github.com/astral-sh/uv"
        echo "  Or: pip install uv"
        exit 1
    fi

    if ! command -v uv &>/dev/null; then
        echo "ERROR: UV install may have completed but 'uv' is not in PATH."
        echo "Add to your PATH: export PATH=\"\${HOME}/.local/bin:\${PATH}\""
        echo "Then run this script again."
        exit 1
    fi
    echo "UV installed successfully."
    uv --version
    echo
fi

echo "Installing project dependencies with UV..."
echo "This will automatically resolve compatible versions..."
echo
uv sync --no-install-project

echo
echo "================================================"
echo "Installation completed successfully!"
echo "================================================"
echo
echo "Virtual environment created at: .venv"
echo
echo "To run the application:"
echo "  ./start.sh"
echo "  Or: source .venv/bin/activate && streamlit run streamlit_ragas_eval.py"
echo
