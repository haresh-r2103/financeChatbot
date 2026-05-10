#!/usr/bin/env bash
set -euo pipefail

echo "═══════════════════════════════════════════"
echo "  FinanceBot — Build"
echo "═══════════════════════════════════════════"

# Check .env exists
if [ ! -f .env ]; then
    echo "⚠  No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "   → Edit .env and add your GEMINI_API_KEY"
fi

# Option 1: Docker build
if command -v docker &> /dev/null; then
    echo ""
    echo "🐳 Building Docker image..."
    docker compose build
    echo "✅ Docker build complete"
    echo "   Run:  docker compose up"
    exit 0
fi

# Option 2: Local build
echo ""
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "🔧 Installing frontend dependencies..."
cd frontend
npm ci
echo ""
echo "🏗  Building frontend..."
npm run build
cd ..

echo ""
echo "📊 Generating sample data..."
python generate_data.py

echo ""
echo "✅ Build complete!"
echo "   Run:  uvicorn main:app --reload"
