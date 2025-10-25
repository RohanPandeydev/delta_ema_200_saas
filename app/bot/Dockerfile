FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy bot files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir \
    delta-rest-client>=1.0.0 \
    python-dotenv>=1.0.0 \
    pandas>=2.0.0 \
    numpy>=1.24.0 \
    requests>=2.31.0 \
    python-telegram-bot>=20.0 \
    flask>=3.0.0 \
    ta>=0.11.0 \
    colorama>=0.4.6 \
    pytz==2023.3

# Create logs directory
RUN mkdir -p /app/logs

# Create entrypoint script
RUN echo '#!/bin/bash\n\
echo "🚀 Starting Trading Bot Container..."\n\
echo "🤖 Bot Type: $BOT_TYPE"\n\
echo "📊 Symbol: $SYMBOL"\n\
echo "⏰ Timeframe: $TIMEFRAME"\n\
\n\
if [ "$BOT_TYPE" = "EMA" ]; then\n\
    echo "📈 Starting EMA Bot..."\n\
    python ema_bot.py\n\
elif [ "$BOT_TYPE" = "RSI_SMA" ]; then\n\
    echo "📊 Starting RSI+SMA Bot..."\n\
    python rsi_sma_bot.py\n\
else\n\
    echo "❌ Unknown bot type: $BOT_TYPE"\n\
    echo "💡 Available types: EMA, RSI_SMA"\n\
    exit 1\n\
fi' > /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]