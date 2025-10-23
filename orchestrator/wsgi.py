"""
WSGI entry point for production deployment
"""
from orchestrator.app import create_app, socketio

app = create_app()

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
"""

# ============================================
# FILE: .env.example
# ============================================
"""
# Flask Secret Key (Generate a random string)
SECRET_KEY=your-super-secret-key-here-change-in-production

# Encryption Key for API credentials (Generate using: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your-encryption-key-here

# Database
DATABASE_URL=postgresql://postgres:postgres@db:5432/trading_bot_db

# Redis
REDIS_URL=redis://redis:6379/0

# Stripe (Optional - for payments)
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx

# Docker
DOCKER_NETWORK=trading_bot_network
BOT_IMAGE=trading-bot:latest
"""