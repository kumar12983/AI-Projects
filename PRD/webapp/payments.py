"""
Stripe payment integration for Premium subscriptions
"""
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
import stripe
import os
from dotenv import load_dotenv
from services import payment_service

load_dotenv()

payments_bp = Blueprint('payments', __name__)

stripe.api_key       = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
WEBHOOK_SECRET        = os.getenv('STRIPE_WEBHOOK_SECRET')


def get_db_connection():
    """Import from app.py"""
    from app import get_db_connection as _get_db
    return _get_db()


@payments_bp.route('/checkout')
@login_required
def checkout():
    """Premium checkout page"""
    return render_template('checkout.html', 
                         stripe_publishable_key=STRIPE_PUBLISHABLE_KEY,
                         user=current_user)


@payments_bp.route('/api/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        result = payment_service.create_checkout_session(
            conn,
            current_user.user_id,
            current_user.email,
            getattr(current_user, 'stripe_customer_id', None),
            request.host_url,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


@payments_bp.route('/payment/success')
@login_required
def payment_success():
    """Payment success page"""
    session_id = request.args.get('session_id')
    return render_template('payment_success.html', session_id=session_id)


@payments_bp.route('/api/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks for subscription events"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle subscription events
    if event['type'] == 'checkout.session.completed':
        conn = get_db_connection()
        if conn:
            payment_service.handle_checkout_completed(conn, event['data']['object'])
            conn.close()

    elif event['type'] == 'customer.subscription.updated':
        conn = get_db_connection()
        if conn:
            payment_service.handle_subscription_updated(conn, event['data']['object'])
            conn.close()

    elif event['type'] == 'customer.subscription.deleted':
        conn = get_db_connection()
        if conn:
            payment_service.handle_subscription_deleted(conn, event['data']['object'])
            conn.close()

    return jsonify({'status': 'success'})


@payments_bp.route('/api/cancel-subscription', methods=['POST'])
@login_required
def cancel_subscription():
    customer_id = getattr(current_user, 'stripe_customer_id', None)
    if not customer_id:
        return jsonify({'error': 'No active subscription'}), 400
    try:
        payment_service.cancel_user_subscription(customer_id)
        return jsonify({'success': True, 'message': 'Subscription will be cancelled at period end'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
