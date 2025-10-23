"""

# 🚀 Multi-User Trading Bot Platform

A complete multi-user trading bot orchestration system with Docker containerization, real-time logs via WebSockets, and secure credential management.

## ✨ Features

- 🔐 **Secure Authentication**: User registration, login with Flask-Login
- 🔑 **Encrypted Credentials**: API keys encrypted with Fernet (cryptography)
- 🐳 **Docker Orchestration**: Automatic container spawning per user
- 📊 **Real-time Logs**: WebSocket-based live log streaming
- 💳 **Subscription Management**: Stripe webhook integration
- 🔄 **Async Tasks**: Celery + Redis for background jobs
- 📱 **Responsive Dashboard**: Modern UI with real-time updates
- 🛡️ **Isolated Bots**: Each user gets their own containerized bot

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│ Orchestrator│────▶│  PostgreSQL │
│  (User UI)  │◀────│   (Flask)   │◀────│     DB      │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ├──────▶ Redis (Celery)
                           │
                           ├──────▶ Docker Engine
                           │        │
                           │        ├─▶ Bot Container 1
                           │        ├─▶ Bot Container 2
                           │        └─▶ Bot Container N
                           │
                           └──────▶ WebSocket (Logs)
```

## 📦 Project Structure

```
project/
├── orchestrator/              # Main Flask application
│   ├── app.py                # Application factory
│   ├── config.py             # Configuration
│   ├── extensions.py         # Flask extensions
│   ├── models.py             # Database models
│   ├── wsgi.py               # WSGI entry point
│   ├── routes/               # Route blueprints
│   │   ├── auth.py          # Authentication routes
│   │   ├── dashboard.py     # Dashboard routes
│   │   ├── credentials.py   # Credential management
│   │   └── webhook.py       # Payment webhooks
│   ├── services/            # Business logic
│   │   ├── docker_manager.py   # Docker operations
│   │   ├── encryption.py       # Encryption service
│   │   └── tasks.py            # Celery tasks
│   ├── static/              # CSS, JS files
│   ├── templates/           # HTML templates
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile          # Orchestrator image
├── bot/                     # Trading bot
│   ├── main.py             # Bot main script
│   ├── requirements.txt    # Bot dependencies
│   └── Dockerfile          # Bot image
├── docker-compose.yml      # Multi-container setup
├── .env.example           # Environment variables template
└── README.md              # This file
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- PostgreSQL (via Docker)
- Redis (via Docker)

### Installation

1. **Clone the repository**

```bash
git clone <repository-url>
cd project
```

2. **Create environment file**

```bash
cp .env.example .env
```

3. **Generate encryption key**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add the output to `.env` as `ENCRYPTION_KEY`

4. **Build bot image**

```bash
cd bot
docker build -t trading-bot:latest .
cd ..
```

5. **Start services**

```bash
docker-compose up -d
```

6. **Access the application**

```
http://localhost:5000
```

## 🔧 Configuration

### Environment Variables

| Variable                | Description                  | Required |
| ----------------------- | ---------------------------- | -------- |
| `SECRET_KEY`            | Flask secret key             | Yes      |
| `ENCRYPTION_KEY`        | Fernet encryption key        | Yes      |
| `DATABASE_URL`          | PostgreSQL connection string | Yes      |
| `REDIS_URL`             | Redis connection string      | Yes      |
| `STRIPE_SECRET_KEY`     | Stripe API key               | No       |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret        | No       |

### Database Schema

**Users Table**

- Authentication and subscription info
- Relationships to credentials and containers

**Credentials Table**

- Encrypted API keys
- Trading configuration
- Telegram settings

**BotContainers Table**

- Docker container metadata
- Status tracking
- Resource limits

## 💡 Usage

### 1. Register an Account

- Navigate to `/auth/register`
- Create account with email and password

### 2. Add Trading Credentials

- Go to "Manage Credentials"
- Add exchange API keys
- Configure trading parameters:
  - Symbol (e.g., BTCUSD)
  - Lot size
  - Timeframe
  - Telegram notifications (optional)

### 3. Start a Bot

- Click "Start Bot" on credential
- Container automatically spawns
- Bot starts trading with your settings

### 4. Monitor Logs

- View real-time logs via WebSocket
- Logs update every 5 seconds
- See trade execution details

### 5. Stop a Bot

- Click "Stop" on running container
- Container gracefully shuts down
- All data persists in database

## 🔐 Security Features

### Credential Encryption

- All API keys encrypted with Fernet (AES-128)
- Encryption key stored separately
- Keys never exposed in logs or UI

### Authentication

- Password hashing with bcrypt
- Session management with Flask-Login
- CSRF protection on forms

### Container Isolation

- Each user gets isolated container
- Resource limits (CPU, memory)
- Network isolation

### Docker Socket Access

- Only orchestrator has socket access
- Containers cannot spawn other containers
- Prevent privilege escalation

## 🎯 API Endpoints

### Authentication

- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/logout` - User logout

### Dashboard

- `GET /dashboard/` - Main dashboard
- `GET /dashboard/logs/<id>` - View logs
- `GET /dashboard/api/container/<id>/logs` - Get logs JSON

### Credentials

- `GET /credentials/` - List credentials
- `POST /credentials/add` - Add credential
- `POST /credentials/delete/<id>` - Delete credential
- `POST /credentials/start/<id>` - Start bot
- `POST /credentials/stop/<id>` - Stop bot

### Webhooks

- `POST /webhook/stripe` - Stripe payment webhook

## 🐳 Docker Commands

### Build images

```bash
docker build -t trading-bot:latest ./bot
docker-compose build
```

### Start services

```bash
docker-compose up -d
```

### View logs

```bash
docker-compose logs -f orchestrator
docker-compose logs -f celery_worker
```

### Stop services

```bash
docker-compose down
```

### Reset database

```bash
docker-compose down -v
docker-compose up -d
```

## 🔄 Celery Tasks

### Async Operations

**spawn_container_task**

- Creates new Docker container
- Injects encrypted credentials
- Starts bot process
- Updates database

**stop_container_task**

- Stops running container
- Cleans up resources
- Updates container status

### Monitor Celery

```bash
# View worker status
docker exec -it trading_bot_celery celery -A orchestrator.app:celery inspect active

# View registered tasks
docker exec -it trading_bot_celery celery -A orchestrator.app:celery inspect registered
```

## 📊 WebSocket Events

### Client → Server

- `subscribe_logs` - Subscribe to container logs

### Server → Client

- `connected` - Connection established
- `subscribed` - Subscribed to logs
- `log_update` - New log line

## 🚨 Troubleshooting

### Container won't start

- Check Docker daemon is running
- Verify bot image exists: `docker images | grep trading-bot`
- Check orchestrator logs: `docker-compose logs orchestrator`

### Logs not updating

- Verify WebSocket connection in browser console
- Check Redis is running: `docker-compose ps redis`
- Restart orchestrator: `docker-compose restart orchestrator`

### Database connection errors

- Ensure PostgreSQL is running: `docker-compose ps db`
- Check DATABASE_URL in .env
- Verify network connectivity

### Encryption errors

- Generate new key if invalid
- Update ENCRYPTION_KEY in .env
- Restart services

## 📈 Production Deployment

### Recommended Setup

1. **Use managed database**: AWS RDS, Azure Database
2. **Use managed Redis**: AWS ElastiCache, Redis Cloud
3. **Enable HTTPS**: Use Nginx reverse proxy
4. **Set strong secrets**: Random SECRET_KEY, ENCRYPTION_KEY
5. **Configure firewall**: Only expose port 443
6. **Enable monitoring**: Prometheus, Grafana
7. **Setup backups**: Database backups, credential exports
8. **Use container orchestration**: Kubernetes, Docker Swarm

### Environment Variables (Production)

```bash
SECRET_KEY=<64-char-random-string>
ENCRYPTION_KEY=<fernet-key>
DATABASE_URL=postgresql://user:pass@prod-db:5432/trading_bot_db
REDIS_URL=redis://prod-redis:6379/0
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📄 License

MIT License - See LICENSE file for details

## 💬 Support

For issues and questions:

- Open GitHub issue
- Email: support@example.com

## 🎉 Acknowledgments

- Flask framework
- Docker
- PostgreSQL
- Redis
- Celery
- Socket.IO
- Cryptography library

---

**Built with ❤️ for automated trading**
"""

# ============================================

# ADDITIONAL FILES

# ============================================

# FILE: orchestrator/run.py

"""
Development server runner
"""
from orchestrator.app import create_app, socketio

if **name** == "**main**":
app = create_app()
socketio.run(app, host='0.0.0.0', port=5000, debug=True)
"""

# FILE: .gitignore

"""

# Python

**pycache**/
_.py[cod]
_$py.class
_.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
_.egg-info/
.installed.cfg
\*.egg

# Flask

instance/
.webassets-cache

# Environment

.env
.env.local

# Database

_.db
_.sqlite
\*.sqlite3

# Logs

\*.log
logs/

# Docker

docker-compose.override.yml

# IDE

.vscode/
.idea/
_.swp
_.swo
\*~

# OS

.DS_Store
Thumbs.db
"""

# ============================================

# SETUP INSTRUCTIONS

# ============================================

"""
COMPLETE SETUP GUIDE:

1. CREATE PROJECT STRUCTURE:
   mkdir -p orchestrator/{routes,services,static/{css,js},templates/{auth,dashboard}}
   mkdir -p bot
   mkdir -p logs

2. COPY ALL FILES to their respective locations

3. GENERATE KEYS:
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   python -c "import secrets; print(secrets.token_hex(32))"

4. CREATE .env file with generated keys

5. BUILD BOT IMAGE:
   cd bot
   docker build -t trading-bot:latest .
   cd ..

6. START SERVICES:
   docker-compose up -d

7. CHECK LOGS:
   docker-compose logs -f

8. ACCESS APPLICATION:
   http://localhost:5000

9. REGISTER USER and add credentials

10. START BOT and view logs!

TROUBLESHOOTING:

- If containers don't start, check: docker ps -a
- If database errors, reset: docker-compose down -v && docker-compose up -d
- If permission denied on docker.sock: sudo chmod 666 /var/run/docker.sock
- If logs not showing, check browser console for WebSocket errors

PRODUCTION DEPLOYMENT:

- Set strong SECRET_KEY and ENCRYPTION_KEY
- Use production database (not localhost)
- Enable HTTPS with reverse proxy
- Set environment variables securely
- Monitor with logging/monitoring tools
- Setup automated backups
- Configure firewall rules
- Use container orchestration (K8s) for scaling
  """
