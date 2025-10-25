from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.bot import BotConfiguration

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    try:
        user_bots = BotConfiguration.query.filter_by(user_id=current_user.id).all()
        bots = list(user_bots) if user_bots else []
    except Exception as e:
        print(f"Error fetching bots: {e}")
        bots = []
    
    return render_template('dashboard/index.html', bots=bots)

@dashboard_bp.route('/debug/bots')
@login_required
def debug_bots():
    """Debug route to check bot data"""
    try:
        user_bots = BotConfiguration.query.filter_by(user_id=current_user.id).all()
        bot_data = []
        for bot in user_bots:
            bot_data.append({
                'id': bot.id,
                'name': bot.bot_name,
                'type': bot.bot_type,
                'status': bot.status,
                'container': bot.container_name
            })
        
        from flask import jsonify
        return jsonify({
            'user_id': current_user.id,
            'bot_count': len(user_bots),
            'bots': bot_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket events will be added separately to avoid circular imports