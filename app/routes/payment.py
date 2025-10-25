from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.user import User
from app import db

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/payment')
@payment_bp.route('/payment/<bot_type>')
@login_required
def payment_page(bot_type=None):
    # Debug print to check if route is working
    print(f"Payment page accessed. Bot type: {bot_type}")
    return render_template('payment/payment.html', bot_type=bot_type)

@payment_bp.route('/payment/success')
@payment_bp.route('/payment/success/<bot_type>')
@login_required
def payment_success(bot_type=None):
    # Bypass actual payment - mark user as premium
    current_user.is_premium = True
    db.session.commit()
    
    flash('🎉 Payment successful! Premium features activated. You can now create trading bots.', 'success')
    
    # Redirect based on whether bot_type was provided
    if bot_type:
        return redirect(url_for('bots.bot_config', bot_type=bot_type))
    else:
        return redirect(url_for('dashboard.index'))