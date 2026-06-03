"""
Payment service — Stripe integration extracted from payments.py.
"""
import os

import stripe
from dotenv import load_dotenv

load_dotenv()

stripe.api_key        = os.getenv('STRIPE_SECRET_KEY')
PREMIUM_PRICE_ID      = os.getenv('STRIPE_PREMIUM_PRICE_ID')


def create_checkout_session(conn, user_id: int, user_email: str,
                             stripe_customer_id: str | None,
                             host_url: str) -> dict:
    """
    Create (or reuse) a Stripe Customer and return a Stripe checkout session.
    Returns dict with 'sessionId' on success or raises on Stripe error.
    """
    cursor = conn.cursor()

    if not stripe_customer_id:
        customer = stripe.Customer.create(
            email=user_email,
            metadata={'user_id': user_id},
        )
        cursor.execute(
            "UPDATE webapp.users SET stripe_customer_id = %s WHERE user_id = %s",
            (customer.id, user_id),
        )
        conn.commit()
        customer_id = customer.id
    else:
        customer_id = stripe_customer_id

    cursor.close()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=['card'],
        line_items=[{'price': PREMIUM_PRICE_ID, 'quantity': 1}],
        mode='subscription',
        success_url=host_url + 'payment/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=host_url + 'pricing',
        metadata={'user_id': user_id},
    )
    return {'sessionId': session.id, 'url': session.url}


def handle_checkout_completed(conn, session: dict) -> None:
    """Upgrade the user to Premium (tier_id=2) after successful payment."""
    user_id     = session['metadata']['user_id']
    customer_id = session['customer']
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE webapp.users
               SET tier_id = 2, stripe_customer_id = %s,
                   subscription_status = 'active',
                   subscription_start_date = CURRENT_TIMESTAMP
             WHERE user_id = %s
            """,
            (customer_id, user_id),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print(f"[payment_service] handle_checkout_completed error for user {user_id}: {exc}")
    finally:
        cursor.close()


def handle_subscription_updated(conn, subscription: dict) -> None:
    customer_id = subscription['customer']
    status      = subscription['status']
    cursor      = conn.cursor()
    try:
        cursor.execute(
            "UPDATE webapp.users SET subscription_status = %s WHERE stripe_customer_id = %s",
            (status, customer_id),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print(f"[payment_service] handle_subscription_updated error for customer {customer_id}: {exc}")
    finally:
        cursor.close()


def handle_subscription_deleted(conn, subscription: dict) -> None:
    customer_id = subscription['customer']
    cursor      = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE webapp.users
               SET tier_id = 1, subscription_status = 'cancelled',
                   subscription_end_date = CURRENT_TIMESTAMP
             WHERE stripe_customer_id = %s
            """,
            (customer_id,),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print(f"[payment_service] handle_subscription_deleted error for customer {customer_id}: {exc}")
    finally:
        cursor.close()


def cancel_user_subscription(stripe_customer_id: str) -> None:
    """Cancel all active subscriptions at period end."""
    subscriptions = stripe.Subscription.list(customer=stripe_customer_id)
    for sub in subscriptions.data:
        if sub.status == 'active':
            stripe.Subscription.modify(sub.id, cancel_at_period_end=True)
