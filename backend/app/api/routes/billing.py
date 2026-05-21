"""
Stripe billing routes for subscription management.
Handles: checkout sessions, webhooks, subscription lifecycle, and tier upgrades.

Webhook flow:
  checkout.session.completed → provision org, set plan to enterprise, status=active
  customer.subscription.deleted → downgrade org to free, status=canceled
  customer.subscription.updated → sync plan/status
  invoice.payment_failed → set subscription_status=past_due
"""

import structlog
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.middleware.security import get_current_user, require_platform_role

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
    org_id: Optional[str] = None  # existing org to upgrade
    success_url: str = "http://localhost:3000/dashboard/settings?billing=success"
    cancel_url: str = "http://localhost:3000/dashboard/settings?billing=cancel"


class SubscriptionStatus(BaseModel):
    tier: str = "free"
    status: str = "active"
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False


@router.post("/checkout")
async def create_checkout_session(req: CheckoutRequest, user: dict = Depends(get_current_user)):
    """Create a Stripe Checkout session for tier upgrade."""
    if not STRIPE_AVAILABLE:
        raise HTTPException(status_code=501, detail="Stripe not configured")

    from app.config import get_settings
    settings = get_settings()

    if not settings.stripe_secret_key:
        raise HTTPException(status_code=501, detail="Stripe not configured")

    stripe.api_key = settings.stripe_secret_key

    # IDOR Protection: Verify org ownership before checkout
    if req.org_id:
        if user.get("platform_role") != "super_admin":
            if req.org_id != user.get("org_id"):
                raise HTTPException(status_code=403, detail="Access denied: department mismatch.")
            # The billing upgrade is an administrative action
            if user.get("org_role") not in ["admin", "incubator_manager", "workspace_owner"]:
                 raise HTTPException(status_code=403, detail="Missing permission to upgrade billing.")

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
            customer_email=user.get("email"),
            metadata={
                "tier": req.tier,
                "user_id": user["id"],
                "org_id": req.org_id or "",
            },
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        logger.error("Stripe checkout failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events for subscription lifecycle.
    This endpoint is NOT authenticated via JWT — it uses Stripe signature verification.
    """
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

    from app.models.database import get_db_service
    db = get_db_service()

    event_type = event["type"]
    data = event["data"]["object"]

    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(db, data)

        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(db, data)

        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(db, data)

        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(db, data)

    except Exception as e:
        logger.error("Webhook handler failed", event_type=event_type, error=str(e))

    return {"received": True}


async def _handle_checkout_completed(db, session: dict):
    """Provision access after successful payment."""
    metadata = session.get("metadata", {})
    tier = metadata.get("tier", "pro")
    user_id = metadata.get("user_id")
    org_id = metadata.get("org_id")
    enterprise_request_id = metadata.get("enterprise_request_id")
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    logger.info(
        "Checkout completed",
        tier=tier, user_id=user_id, org_id=org_id,
        enterprise_request_id=enterprise_request_id,
    )

    # Update user tier
    if user_id:
        try:
            db._client.table("profiles").update({
                "tier": tier,
            }).eq("id", user_id).execute()
        except Exception as e:
            logger.warning("Failed to update user tier", error=str(e))

    # If this is an enterprise request approval → provision the org
    if enterprise_request_id:
        try:
            req = db._client.table("enterprise_requests").select("*").eq("id", enterprise_request_id).execute()
            if req.data:
                req_data = req.data[0]
                import uuid
                new_org_id = str(uuid.uuid4())
                slug = req_data["company_name"].lower().replace(" ", "-")[:50]

                org_data = {
                    "id": new_org_id,
                    "name": req_data["company_name"],
                    "slug": slug,
                    "plan": "enterprise",
                    "max_members": req_data.get("required_seats") or 10,
                    "subscription_status": "active",
                    "stripe_customer_id": customer_id,
                    "stripe_subscription_id": subscription_id,
                    "billing_email": req_data["contact_email"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                db._client.table("organizations").insert(org_data).execute()

                # Update the enterprise request
                db._client.table("enterprise_requests").update({
                    "status": "approved",
                }).eq("id", enterprise_request_id).execute()

                logger.info("Enterprise org provisioned", org_id=new_org_id, company=req_data["company_name"])
        except Exception as e:
            logger.error("Failed to provision enterprise org", error=str(e))

    # If upgrading an existing org
    elif org_id:
        try:
            db._client.table("organizations").update({
                "plan": tier,
                "subscription_status": "active",
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", org_id).execute()
        except Exception as e:
            logger.warning("Failed to update org plan", error=str(e))


async def _handle_subscription_deleted(db, subscription: dict):
    """Downgrade org when subscription is canceled."""
    subscription_id = subscription.get("id")
    logger.info("Subscription deleted", subscription_id=subscription_id)

    try:
        orgs = (
            db._client.table("organizations")
            .select("id")
            .eq("stripe_subscription_id", subscription_id)
            .execute()
        )
        for org in (orgs.data or []):
            db._client.table("organizations").update({
                "plan": "free",
                "subscription_status": "canceled",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", org["id"]).execute()
            logger.info("Org downgraded to free", org_id=org["id"])
    except Exception as e:
        logger.error("Failed to handle subscription deletion", error=str(e))


async def _handle_subscription_updated(db, subscription: dict):
    """Sync subscription status changes."""
    subscription_id = subscription.get("id")
    status = subscription.get("status")  # active, past_due, canceled, etc.
    current_period_end = subscription.get("current_period_end")

    try:
        update_data = {
            "subscription_status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if current_period_end:
            update_data["current_period_end"] = datetime.fromtimestamp(
                current_period_end, tz=timezone.utc
            ).isoformat()

        db._client.table("organizations").update(update_data).eq(
            "stripe_subscription_id", subscription_id
        ).execute()
    except Exception as e:
        logger.error("Failed to sync subscription update", error=str(e))


async def _handle_payment_failed(db, invoice: dict):
    """Mark org as past_due when payment fails."""
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return

    try:
        db._client.table("organizations").update({
            "subscription_status": "past_due",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("stripe_subscription_id", subscription_id).execute()
        logger.warning("Payment failed, org marked past_due", subscription_id=subscription_id)
    except Exception as e:
        logger.error("Failed to handle payment failure", error=str(e))


@router.get("/status")
async def get_billing_status(user: dict = Depends(get_current_user)):
    """Get current billing/subscription status for the user's active org."""
    org_id = user.get("org_id")
    if not org_id:
        return SubscriptionStatus(tier=user.get("tier", "free"), status="active")

    from app.models.database import get_db_service
    db = get_db_service()

    try:
        org = db._client.table("organizations").select(
            "plan, subscription_status, current_period_end"
        ).eq("id", org_id).single().execute()
        if org.data:
            return SubscriptionStatus(
                tier=org.data.get("plan", "free"),
                status=org.data.get("subscription_status", "active"),
                current_period_end=org.data.get("current_period_end"),
            )
    except Exception:
        pass

    return SubscriptionStatus(tier=user.get("tier", "free"), status="active")


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
                    "Team collaboration (up to seat limit)",
                    "API access",
                    "Custom investor profiles",
                    "White-label reports",
                    "SSO authentication",
                    "Audit trail",
                    "Dedicated support",
                ],
            },
        ]
    }
