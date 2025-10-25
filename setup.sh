#!/bin/bash

echo "🚀 Trading Bot Platform - Automated Setup"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

echo "✅ All prerequisites found!"
echo ""

# Generate keys if .env doesn't exist
if [ ! -f .env ]; then
    echo "📝 Generating encryption keys..."
    
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    
    cat > .env << EOF
# ============================================
# Flask Application Settings
# ============================================
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# ============================================
# Database Configuration
# ============================================
DATABASE_URL=mysql+pymysql://trading_user:trading_password@db:3306/trading_bot_db

# ============================================
# Docker Settings
# ============================================
DOCKER_NETWORK=trading_bot_network
BOT_IMAGE=trading-bot:latest

# ============================================
# Optional Settings
# ============================================
REQUIRE_SUBSCRIPTION=False
EOF
    
    echo "✅ Generated .env file with secure keys"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🐳 Building bot Docker image..."
cd bot
docker build -t trading-bot:latest . || {
    echo "❌ Failed to build bot image"
    exit 1
}
cd ..
echo "✅ Bot image built successfully"

echo ""
echo "🚀 Starting services..."
docker-compose up -d || {
    echo "❌ Failed to start services"
    exit 1
}

echo ""
echo "⏳ Waiting for database to be ready..."
sleep 15

echo ""
echo "📊 Checking service status..."
docker-compose ps

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "🌐 Access the application at: http://localhost:5000"
echo ""
echo "📝 Next steps:"
echo "   1. Open http://localhost:5000 in your browser"
echo "   2. Register a new account"
echo "   3. Add your trading credentials"
echo "   4. Start a bot and monitor logs"
echo ""
echo "📖 For detailed instructions, see SETUP_GUIDE.md"
echo ""
echo "🔍 View logs with: docker-compose logs -f"
echo "🛑 Stop services with: docker-compose down"
echo ""