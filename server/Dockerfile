FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for any Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY tradeexecute.py .
COPY config.py .
COPY telegram_notifier.py .

# Create logs directory with proper permissions
RUN mkdir -p /app/logs && chmod 755 /app/logs

# Set timezone
ENV TZ=Asia/Kolkata
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Add healthcheck (optional but recommended)
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/app/logs') else 1)" || exit 1

# Run the trading bot
CMD ["python", "-u", "tradeexecute.py"]