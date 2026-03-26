#!/usr/bin/env bash
# setup.sh — macOS/Linux environment setup for FX Lot Master
set -euo pipefail

PYTHON=${PYTHON:-python3}
VENV_DIR="venv"

echo "==> Checking Python version..."
$PYTHON --version

echo "==> Creating virtual environment in ./$VENV_DIR ..."
$PYTHON -m venv "$VENV_DIR"

echo "==> Activating virtual environment..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Upgrading pip..."
pip install --upgrade pip

echo "==> Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅  Setup complete!"
echo ""
echo "To run the app:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "To build a macOS .app bundle:"
echo "  source venv/bin/activate"
echo "  pyinstaller fx_lot_master.spec"
echo "  open dist/"
