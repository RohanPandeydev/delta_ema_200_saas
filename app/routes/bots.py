from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.bot import BotConfiguration
from app.utils.docker_manager import docker_manager  # Using the auto-selected manager
from app import db, socketio

bots_bp = Blueprint('bots', __name__)

def get_bot_specific_config(bot_type, form_data):
    if bot_type == 'EMA':
        return {
            'ema_period': int(form_data.get('ema_period', 200)),
        }
    elif bot_type == 'RSI_SMA':
        return {
            'rsi_period': int(form_data.get('rsi_period', 14)),
            'rsi_overbought': int(form_data.get('rsi_overbought', 75)),
            'rsi_oversold': int(form_data.get('rsi_oversold', 30)),
            'sma_period': int(form_data.get('sma_period', 21)),
            'timeframe_candle_m': form_data.get('timeframe_candle_m', '0'),
        }
    return {}
@bots_bp.route('/bot/config/<bot_type>', methods=['GET', 'POST'])
@login_required
def bot_config(bot_type):
    if not current_user.is_premium:
        flash('Please complete payment to access bot configuration', 'warning')
        return redirect(url_for('payment.payment_page', bot_type=bot_type))
    
    if request.method == 'POST':
        try:
            # Validate and sanitize bot name
            bot_name = request.form.get('bot_name', '').strip()
            if not bot_name:
                bot_name = f"{bot_type.lower()}_bot_{int(time.time())}"
            
            # Ensure bot name uniqueness for this user
            base_name = bot_name
            counter = 1
            while BotConfiguration.query.filter_by(
                user_id=current_user.id, 
                bot_name=bot_name
            ).first():
                bot_name = f"{base_name}_{counter}"
                counter += 1
            
            # Create bot configuration with user's input
            bot_config_data = {
                'user_id': current_user.id,
                'bot_type': bot_type,
                'bot_name': bot_name,
                'delta_api_key': request.form.get('delta_api_key'),
                'delta_api_secret': request.form.get('delta_api_secret'),
                'symbol': request.form.get('symbol', 'BTCUSD'),
                'timeframe': request.form.get('timeframe', '15'),
                'telegram_bot_token': request.form.get('telegram_bot_token', ''),
                'telegram_chat_id': request.form.get('telegram_chat_id', ''),
                'lot_size': request.form.get('lot_size', '3.0')
            }
            
            # Add bot-specific configuration
            bot_config_data.update(get_bot_specific_config(bot_type, request.form))
            
            bot_config = BotConfiguration(**bot_config_data)
            db.session.add(bot_config)
            db.session.commit()
            
            # Create actual Docker container
            try:
                container_id, container_name = docker_manager.create_bot_container(
                    current_user, bot_config
                )
                
                # Update database with real container info
                bot_config.container_id = container_id
                bot_config.container_name = container_name
                bot_config.status = 'running'
                db.session.commit()
                
                flash(f'✅ {bot_type} bot created and started successfully!', 'success')
                
            except Exception as docker_error:
                # If Docker fails, mark as error but keep configuration
                bot_config.status = 'error'
                bot_config.container_name = f"{current_user.username}_{current_user.id}_{bot_config.bot_name}_ERROR"
                db.session.commit()
                flash(f'⚠️ Bot configuration saved but Docker failed: {docker_error}', 'warning')
            
            return redirect(url_for('dashboard.index'))
            
        except Exception as e:
            flash(f'Error creating bot: {str(e)}', 'error')
            if 'bot_config' in locals() and bot_config.id:
                db.session.delete(bot_config)
            db.session.commit()
    
    return render_template(f'bots/bot_config_{bot_type.lower()}.html', bot_type=bot_type)

@bots_bp.route('/bot/<int:bot_id>/stop')
@login_required
def stop_bot(bot_id):
    bot = BotConfiguration.query.get_or_404(bot_id)
    if bot.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard.index'))
    
    # REAL DOCKER STOP
    if docker_manager.stop_bot(bot.container_id):
        bot.status = 'stopped'
        db.session.commit()
        flash('Bot stopped successfully', 'success')
    else:
        flash('Error stopping bot', 'error')
    
    return redirect(url_for('dashboard.index'))

@bots_bp.route('/bot/<int:bot_id>/delete')
@login_required
def delete_bot(bot_id):
    bot = BotConfiguration.query.get_or_404(bot_id)
    if bot.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard.index'))
    
    # REAL DOCKER DELETE
    if docker_manager.delete_bot(bot.container_id):
        db.session.delete(bot)
        db.session.commit()
        flash('Bot deleted successfully', 'success')
    else:
        flash('Error deleting bot', 'error')
    
    return redirect(url_for('dashboard.index'))
@bots_bp.route('/bot/<int:bot_id>/logs')
@login_required
def get_bot_logs(bot_id):
    """Get bot logs from Docker container"""
    try:
        bot = BotConfiguration.query.get_or_404(bot_id)
        
        # Check if user owns this bot
        if bot.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get logs from Docker manager
        logs = docker_manager.get_logs(bot.container_id)
        
        return jsonify({
            'success': True,
            'logs': logs,
            'bot_name': bot.bot_name,
            'container_id': bot.container_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error fetching logs: {str(e)}'
        }), 500