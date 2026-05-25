"""
Stripe payment API routes.
create_checkout_session and cancel_subscription require a valid JWT (CurrentUser).
stripe_webhook is public — Stripe signature verification replaces auth.
"""
import os

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from db_utils import get_db_connection
from dependencies import get_current_user, get_db
from services import payment_service

router = APIRouter(tags=["payments"])

stripe.api_key  = os.getenv("STRIPE_SECRET_KEY")
_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@router.post("/api/create-checkout-session")
def create_checkout_session(
    request: Request,
    user=Depends(get_current_user),
    conn=Depends(get_db),
):
    try:
        result = payment_service.create_checkout_session(
            conn,
            user.user_id,
            user.email,
            getattr(user, "stripe_customer_id", None),
            str(request.base_url),
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post("/api/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe sends raw POST bodies — we must read the raw bytes to verify the
    signature.  This is an async function so FastAPI reads the body before
    the route runs (sync routes can't await request.body()).
    """
    payload    = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, _WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    conn = get_db_connection()
    if conn:
        try:
            if event["type"] == "checkout.session.completed":
                payment_service.handle_checkout_completed(conn, event["data"]["object"])
            elif event["type"] == "customer.subscription.updated":
                payment_service.handle_subscription_updated(conn, event["data"]["object"])
            elif event["type"] == "customer.subscription.deleted":
                payment_service.handle_subscription_deleted(conn, event["data"]["object"])
        finally:
            conn.close()

    return {"status": "success"}


@router.post("/api/cancel-subscription")
def cancel_subscription(user=Depends(get_current_user)):
    customer_id = getattr(user, "stripe_customer_id", None)
    if not customer_id:
        raise HTTPException(status_code=400, detail="No active subscription")
    try:
        payment_service.cancel_user_subscription(customer_id)
        return {"success": True, "message": "Subscription will be cancelled at period end"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
