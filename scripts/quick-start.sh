#!/bin/bash
#
# Quick Start Script for AI SEO Agent
# One-liner to get started quickly
#

set -e

echo "🚀 AI SEO Agent - Quick Start"
echo "=============================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION detected"

# Check if in virtual environment (recommended)
if [ -z "$VIRTUAL_ENV" ]; then
    echo ""
    echo "⚠️  Not in a virtual environment. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -e . -q

# Run interactive setup
echo ""
echo "🧙 Starting interactive setup wizard..."
echo ""
python3 scripts/setup.py

echo ""
echo "✅ Quick start complete!"
