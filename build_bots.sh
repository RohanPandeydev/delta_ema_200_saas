#!/bin/bash

echo "🔨 Building Trading Bot Docker Image..."

cd app/bot

# Build the Docker image
docker build -t trading-bot:latest .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully!"
    echo ""
    echo "🚀 To test your bots:"
    echo "   EMA Bot:    docker run --rm -e BOT_TYPE=EMA -e SYMBOL=BTCUSD trading-bot:latest"
    echo "   RSI_SMA Bot: docker run --rm -e BOT_TYPE=RSI_SMA -e SYMBOL=BTCUSD trading-bot:latest"
else
    echo "❌ Docker build failed!"
    exit 1
fi