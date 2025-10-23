# ============================================
# FILE: orchestrator/routes/webhook.py
# ============================================
"""
Webhook handlers for payment providers
"""
from flask import request, jsonify
from orchestrator.routes import webhook_bp
from orchestrator.extensions import db
from orchestrator.models import User
from orchestrator.services.tasks import spawn_container_task, stop_container_task
from datetime import datetime, timedelta
import stripe
import os

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@webhook_bp.route('/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle events
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('client_reference_id')
        
        if user_id:
            user = User.query.get(int(user_id))
            if user:
                user.is_subscribed = True
                user.subscription_plan = 'basic'
                user.subscription_expires = datetime.utcnow() + timedelta(days=30)
                db.session.commit()
                
                # Auto-start first credential if exists
                from orchestrator.models import Credential
                first_cred = Credential.query.filter_by(user_id=user.id, is_active=True).first()
                if first_cred:
                    spawn_container_task.delay(user.id, first_cred.id)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        # Stop all user containers
        # Implement based on your needs
        pass
    
    return jsonify({'success': True})