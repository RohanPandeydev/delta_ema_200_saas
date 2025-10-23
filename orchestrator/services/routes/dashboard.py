
# ============================================
# FILE: orchestrator/routes/dashboard.py
# ============================================
"""
Dashboard routes
"""
from flask import render_template, jsonify
from flask_login import login_required, current_user
from orchestrator.routes import dashboard_bp
from orchestrator.models import BotContainer, Credential
from orchestrator.services.docker_manager import docker_manager

@dashboard_bp.route('/')
@login_required
def index():
    """Main dashboard"""
    containers = BotContainer.query.filter_by(user_id=current_user.id).all()
    credentials = Credential.query.filter_by(user_id=current_user.id).all()
    
    return render_template('dashboard/index.html',
                         containers=containers,
                         credentials=credentials)

@dashboard_bp.route('/logs/<int:container_db_id>')
@login_required
def logs(container_db_id):
    """View container logs"""
    container = BotContainer.query.get_or_404(container_db_id)
    
    # Security check
    if container.user_id != current_user.id:
        return "Unauthorized", 403
    
    return render_template('dashboard/logs.html', container=container)

@dashboard_bp.route('/api/container/<int:container_db_id>/logs')
@login_required
def api_get_logs(container_db_id):
    """API endpoint to get container logs"""
    container = BotContainer.query.get_or_404(container_db_id)
    
    if container.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    logs = docker_manager.get_container_logs(container.container_id, tail=50)
    
    return jsonify({
        'success': True,
        'logs': logs,
        'container_name': container.container_name
    })