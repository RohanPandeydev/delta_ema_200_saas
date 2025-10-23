"""
Development server runner
"""
from orchestrator.app import create_app, socketio

if __name__ == "__main__":
    app = create_app()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
"""

# FILE: .gitignore
"""
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
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
*.egg-info/
.installed.cfg
*.egg

# Flask
instance/
.webassets-cache

# Environment
.env
.env.local

# Database
*.db
*.sqlite
*.sqlite3

# Logs
*.log
logs/

# Docker
docker-compose.override.yml

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

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