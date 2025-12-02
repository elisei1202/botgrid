#!/bin/bash

# Bybit Grid Trading Bot - Start Script

echo "=========================================="
echo "🤖 Bybit Grid Trading Bot"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python3 -m venv venv"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please copy .env.example to .env and configure your API credentials"
    exit 1
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "❌ Dependencies not installed!"
    echo "Please run: pip install -r requirements.txt"
    exit 1
fi

echo "✓ Dependencies OK"
echo ""

# Auto-start Web UI + Bot (no menu)
echo "🚀 Starting Web UI + Bot..."
echo "Open browser at: http://localhost:8000"
echo ""
python ui_server.py
