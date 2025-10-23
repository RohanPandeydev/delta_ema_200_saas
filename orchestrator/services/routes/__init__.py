
# ============================================
# FILE: orchestrator/routes/__init__.py
# ============================================
"""
Route blueprints initialization
"""
from flask import Blueprint

# Create blueprints
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
credentials_bp = Blueprint('credentials', __name__, url_prefix='/credentials')
webhook_bp = Blueprint('webhook', __name__, url_prefix='/webhook')