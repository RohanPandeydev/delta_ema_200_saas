# ============================================
# FILE: orchestrator/routes/credentials.py
# ============================================
"""
Credential management routes
"""
from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from orchestrator.routes import credentials_bp
from orchestrator.extensions import db
from orchestrator.models import Credential
from orchestrator.services.encryption import encryption_service
from orchestrator.services.tasks import spawn_container_task, stop_container_task

@credentials_bp.route('/')
@login_required
def index():
    """List user credentials"""
    credentials = Credential.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard/credentials.html', credentials=credentials)

@credentials_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Add new credential"""
    try:
        exchange_name = request.form.get('exchange_name')
        api_key = request.form.get('api_key')
        api_secret = request.form.get('api_secret')
        symbol = request.form.get('symbol', 'BTCUSD')
        lot_size = float(request.form.get('lot_size', 60))
        timeframe = int(request.form.get('timeframe', 15))
        telegram_bot_token = request.form.get('telegram_bot_token', '')
        telegram_chat_id = request.form.get('telegram_chat_id', '')
        
        # Validation
        if not all([exchange_name, api_key, api_secret]):
            flash('Exchange name, API Key, and API Secret are required', 'danger')
            return redirect(url_for('credentials.index'))
        
        # Encrypt credentials
        api_key_encrypted = encryption_service.encrypt(api_key)
        api_secret_encrypted = encryption_service.encrypt(api_secret)
        telegram_token_encrypted = encryption_service.encrypt(telegram_bot_token) if telegram_bot_token else None
        
        # Create credential
        credential = Credential(
            user_id=current_user.id,
            exchange_name=exchange_name,
            api_key_encrypted=api_key_encrypted,
            api_secret_encrypted=api_secret_encrypted,
            symbol=symbol,
            lot_size=lot_size,
            timeframe=timeframe,
            telegram_bot_token_encrypted=telegram_token_encrypted,
            telegram_chat_id=telegram_chat_id
        )
        
        db.session.add(credential)
        db.session.commit()
        
        flash('Credential added successfully!', 'success')
        return redirect(url_for('credentials.index'))
        
    except Exception as e:
        flash(f'Error adding credential: {str(e)}', 'danger')
        return redirect(url_for('credentials.index'))

@credentials_bp.route('/delete/<int:cred_id>', methods=['POST'])
@login_required
def delete(cred_id):
    """Delete credential"""
    credential = Credential.query.get_or_404(cred_id)
    
    if credential.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(credential)
    db.session.commit()
    
    flash('Credential deleted successfully', 'success')
    return redirect(url_for('credentials.index'))

@credentials_bp.route('/start/<int:cred_id>', methods=['POST'])
@login_required
def start_bot(cred_id):
    """Start bot with credential"""
    credential = Credential.query.get_or_404(cred_id)
    
    if credential.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check subscription
    if not current_user.is_subscribed:
        flash('Please subscribe to start trading bots', 'warning')
        return redirect(url_for('credentials.index'))
    
    # Spawn container asynchronously
    task = spawn_container_task.delay(current_user.id, cred_id)
    
    flash('Bot is starting... Please wait a moment.', 'info')
    return redirect(url_for('dashboard.index'))

@credentials_bp.route('/stop/<int:container_db_id>', methods=['POST'])
@login_required
def stop_bot(container_db_id):
    """Stop running bot"""
    from orchestrator.models import BotContainer
    
    container = BotContainer.query.get_or_404(container_db_id)
    
    if container.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Stop container asynchronously
    task = stop_container_task.delay(container.container_id)
    
    flash('Bot is stopping...', 'info')
    return redirect(url_for('dashboard.index'))