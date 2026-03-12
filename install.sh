#!/usr/bin/env bash
# NeuraScreen — Quick Setup Script
set -e

echo ""
echo "  NeuraScreen — Setup"
echo "  ==================="
echo ""

# 1. Check Python
echo "[1/5] Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo "  Found: $PYTHON_VERSION"
else
    echo "  ERROR: Python 3 not found."
    echo "  Install it from https://python.org"
    exit 1
fi

# 2. Create virtual environment
echo "[2/5] Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "  .venv already exists, skipping."
else
    python3 -m venv .venv
    echo "  Created .venv"
fi
source .venv/bin/activate
echo "  Activated .venv"

# 3. Install Python dependencies
echo "[3/5] Installing Python dependencies..."
pip install -q -e ".[all]"
echo "  Dependencies installed."

# 4. Install Playwright Chromium
echo "[4/5] Installing Playwright Chromium..."
playwright install chromium
echo "  Chromium installed."

# 5. Check ffmpeg
echo "[5/5] Checking ffmpeg..."
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -1)
    echo "  Found: $FFMPEG_VERSION"
else
    echo "  WARNING: ffmpeg not found."
    echo "  Install it:"
    echo "    macOS:   brew install ffmpeg"
    echo "    Linux:   sudo apt install ffmpeg"
    echo "    Windows: choco install ffmpeg"
fi

# 6. Create .env if missing
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "  Edit .env with your APP_URL and TTS credentials."
fi

echo ""
echo "  Setup complete!"
echo ""
echo "  Next steps:"
echo "    1. Edit .env with your configuration"
echo "    2. neurascreen validate examples/01-simple-navigation.json"
echo "    3. neurascreen full examples/01-simple-navigation.json"
echo ""
