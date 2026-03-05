#!/usr/bin/env bash
# Installer script for RAGAS Evaluation Project (Mac/Unix)
# Installs UV if not present, then installs project dependencies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "RAGAS Evaluation Project - UV Installation"
echo "================================================"
echo

export PATH="${HOME}/.local/bin:${PATH}"

# Check if UV is already available
if command -v uv &>/dev/null; then
    echo "UV is already installed!"
    uv --version
    echo
    echo "Running uv sync to install project dependencies..."
    uv sync --no-install-project
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
        echo "ERROR: Neither curl nor wget found."
        echo "Please install UV manually: https://github.com/astral-sh/uv"
        echo "  Or: pip install uv   (then use: python -m uv sync --no-install-project)"
        exit 1
    fi

    if ! command -v uv &>/dev/null; then
        echo "ERROR: UV not found in PATH after install. Try: export PATH=\"\${HOME}/.local/bin:\${PATH}\""
        exit 1
    fi
    echo "UV installed successfully."
    uv --version
    echo
    echo "Installing project dependencies..."
    uv sync --no-install-project
fi

echo
echo "================================================"
echo "Setup completed!"
echo "================================================"
echo
echo "To start the application, run: ./start.sh"
echo
