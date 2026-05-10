#!/usr/bin/env bash
set -euo pipefail

echo "═══════════════════════════════════════════"
echo "  FinanceBot — Deploy"
echo "═══════════════════════════════════════════"

# Check prerequisites
if [ ! -f .env ]; then
    echo "❌ .env file not found. Run: cp .env.example .env"
    exit 1
fi

if ! grep -q "GEMINI_API_KEY=." .env || grep -q "your_gemini_api_key_here" .env; then
    echo "❌ GEMINI_API_KEY not set in .env"
    echo "   Get a free key at: https://aistudio.google.com/apikey"
    exit 1
fi

echo ""
echo "🐳 Building and starting with Docker Compose..."
docker compose up -d --build

echo ""
echo "⏳ Waiting for health check..."
for i in $(seq 1 15); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo ""
        echo "✅ FinanceBot is live!"
        echo ""
        echo "   🌐 App:     http://localhost:8000"
        echo "   📡 API:     http://localhost:8000/docs"
        echo "   💚 Health:  http://localhost:8000/health"
        echo ""
        echo "   Logs:   docker compose logs -f"
        echo "   Stop:   docker compose down"
        exit 0
    fi
    printf "."
    sleep 2
done

echo ""
echo "⚠  Server didn't respond within 30s. Check logs:"
echo "   docker compose logs financebot"
exit 1
