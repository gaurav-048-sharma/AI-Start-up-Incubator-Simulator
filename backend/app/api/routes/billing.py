"""
Stripe billing routes for subscription management.
Handles: checkout sessions, webhooks, subscription status, and tier upgrades.
"""

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

logger = structlog.get_logger()
router = APIRouter()

# Try to import Stripe — graceful fallback
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None


class CheckoutRequest(BaseModel):
    tier: str  # "pro" or "enterprise"
    success_url: str = "http://localhost:3000/dashboard/settings?billing=success"
    cancel_url: str = "http://localhost:3000/dashboard/settings?billing=cancel"


class SubscriptionStatus(BaseModel):
    tier: str = "free"
    status: str = "active"
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False


@router.post("/checkout")
async def create_checkout_session(req: CheckoutRequest):
    """Create a Stripe Checkout session for tier upgrade."""
    if not STRIPE_AVAILABLE:
        raise HTTPException(status_code=501, detail="Stripe not configured")

    from app.config import get_settings
    settings = get_settings()

    if not settings.stripe_secret_key:
        raise HTTPException(status_code=501, detail="Stripe not configured")

    stripe.api_key = settings.stripe_secret_key

    price_map = {
        "pro": settings.stripe_price_pro,
        "enterprise": settings.stripe_price_enterprise,
    }

    price_id = price_map.get(req.tier)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {req.tier}")

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=req.success_url,
            cancel_url=req.cancel_url,
            metadata={"tier": req.tier},
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except stripe.error.StripeError as e:
        logger.error("Stripe checkout failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events (subscription changes)."""
    if not STRIPE_AVAILABLE:
        raise HTTPException(status_code=501, detail="Stripe not configured")

    from app.config import get_settings
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.error("Stripe webhook verification failed", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    # Handle events
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        tier = session.get("metadata", {}).get("tier", "pro")
        customer_email = session.get("customer_email")
        logger.info("Subscription created", tier=tier, email=customer_email)
        # TODO: Update user tier in Supabase profiles table

    elif event["type"] == "customer.subscription.deleted":
        logger.info("Subscription cancelled")
        # TODO: Downgrade user to free tier

    return {"received": True}


@router.get("/status")
async def get_billing_status():
    """Get current billing/subscription status."""
    # In production, this checks Stripe for the user's subscription
    return SubscriptionStatus(tier="free", status="active")


@router.get("/plans")
async def get_plans():
    """Return available subscription plans with features."""
    return {
        "plans": [
            {
                "tier": "free",
                "name": "Starter",
                "price": 0,
                "features": [
                    "3 ideas per month",
                    "Basic market analysis",
                    "Single agent execution",
                    "Standard reports",
                ],
            },
            {
                "tier": "pro",
                "name": "Professional",
                "price": 49,
                "features": [
                    "Unlimited ideas",
                    "Full 5-agent workflow",
                    "Investor pitch simulation",
                    "PDF report export",
                    "Custom agent configurations",
                    "Priority processing",
                ],
            },
            {
                "tier": "enterprise",
                "name": "Enterprise",
                "price": 199,
                "features": [
                    "Everything in Pro",
                    "Team collaboration (5 seats)",
                    "API access",
                    "Custom investor profiles",
                    "White-label reports",
                    "SSO authentication",
                    "Dedicated support",
                ],
            },
        ]
    }
