"""
MFA (Multi-Factor Authentication) API Routes.

Provides TOTP-based 2FA operations using Supabase Auth's built-in MFA:
  - Enroll a TOTP factor (returns QR code)
  - Verify enrollment with a TOTP code
  - Create and verify MFA challenges (login step-up)
  - List enrolled factors
  - Unenroll a factor

All operations use the user's own JWT context (not the service role key).
"""

import structlog
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.middleware.security import (
    get_current_user,
    security_scheme,
    current_jwt,
    has_role_level,
    resolve_effective_org_role,
)
from app.config import get_settings

logger = structlog.get_logger()
router = APIRouter()


# ── Request / Response Models ─────────────────────────────────────

class MfaEnrollRequest(BaseModel):
    """Request to enroll a new TOTP factor."""
    friendly_name: Optional[str] = Field("Authenticator App", description="Human-readable label for the factor")


class MfaVerifyRequest(BaseModel):
    """Request to verify a TOTP code (enrollment confirmation or challenge)."""
    factor_id: str = Field(..., description="The MFA factor UUID")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")


class MfaChallengeRequest(BaseModel):
    """Request to create an MFA challenge."""
    factor_id: str = Field(..., description="The MFA factor UUID to challenge")


class MfaChallengeVerifyRequest(BaseModel):
    """Verify an MFA challenge to upgrade session to aal2."""
    factor_id: str = Field(..., description="The MFA factor UUID")
    challenge_id: str = Field(..., description="The challenge UUID returned from /challenge")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")


class MfaUnenrollRequest(BaseModel):
    """Request to remove a TOTP factor."""
    factor_id: str = Field(..., description="The MFA factor UUID to remove")


# ── Helper: Supabase Auth REST client ─────────────────────────────

def _get_supabase_auth_url() -> str:
    """Get the Supabase Auth base URL."""
    settings = get_settings()
    base = ''
    if not base:
        raise HTTPException(status_code=500, detail="Supabase is not configured")
    return f"{base}/auth/v1"


def _get_auth_headers() -> dict:
    """Get headers for Supabase Auth REST API calls using the current user's JWT."""
    settings = get_settings()
    token = current_jwt.get()
    if not token:
        raise HTTPException(status_code=401, detail="No active JWT session")
    return {
        "Authorization": f"Bearer {token}",
        "apikey": '' or "",
        "Content-Type": "application/json",
    }


# ── Endpoints ─────────────────────────────────────────────────────

@router.get("/mfa/factors")
async def list_factors(user: dict = Depends(get_current_user)):
    """
    List all enrolled MFA factors for the current user.
    Returns factor IDs, types, friendly names, and verification status.
    """
    try:
        auth_url = _get_supabase_auth_url()
        headers = _get_auth_headers()

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{auth_url}/factors", headers=headers)

            if resp.status_code == 200:
                factors = resp.json()
                # Normalize: ensure we always return a list
                if isinstance(factors, dict):
                    factors = factors.get("all", factors.get("totp", []))
                
                verified_factors = [f for f in factors if f.get("status") == "verified"]
                return {
                    "factors": factors,
                    "has_verified_factor": len(verified_factors) > 0,
                    "mfa_enabled": len(verified_factors) > 0,
                }
            elif resp.status_code == 401:
                raise HTTPException(status_code=401, detail="Session expired")
            else:
                logger.warning("Supabase MFA factors fetch failed", status=resp.status_code, body=resp.text)
                return {"factors": [], "has_verified_factor": False, "mfa_enabled": False}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list MFA factors", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve MFA factors")


@router.post("/mfa/enroll")
async def enroll_factor(body: MfaEnrollRequest, user: dict = Depends(get_current_user)):
    """
    Begin TOTP factor enrollment.
    Returns a QR code URI and secret that the user scans with their authenticator app.
    The factor is in 'unverified' state until POST /mfa/verify is called.
    """
    try:
        auth_url = _get_supabase_auth_url()
        headers = _get_auth_headers()

        payload = {
            "friendly_name": body.friendly_name or "Authenticator App",
            "factor_type": "totp",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{auth_url}/factors", headers=headers, json=payload)

            if resp.status_code in (200, 201):
                data = resp.json()
                logger.info("MFA TOTP factor enrollment started", user_id=user["id"], factor_id=data.get("id"))
                return {
                    "factor_id": data.get("id"),
                    "totp": {
                        "qr_code": data.get("totp", {}).get("qr_code", ""),
                        "secret": data.get("totp", {}).get("secret", ""),
                        "uri": data.get("totp", {}).get("uri", ""),
                    },
                    "friendly_name": data.get("friendly_name", body.friendly_name),
                }
            elif resp.status_code == 422:
                raise HTTPException(
                    status_code=409,
                    detail="A TOTP factor is already enrolled. Unenroll the existing factor first."
                )
            elif resp.status_code == 401:
                raise HTTPException(status_code=401, detail="Session expired — please log in again")
            else:
                logger.error("MFA enroll failed", status=resp.status_code, body=resp.text)
                raise HTTPException(status_code=resp.status_code, detail="Failed to enroll MFA factor")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("MFA enrollment error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start MFA enrollment")


@router.post("/mfa/verify")
async def verify_factor(body: MfaVerifyRequest, user: dict = Depends(get_current_user)):
    """
    Verify the TOTP code to confirm factor enrollment.
    After this, the factor status transitions from 'unverified' to 'verified'.
    This also creates a challenge + verifies it, upgrading the session to aal2.
    """
    try:
        auth_url = _get_supabase_auth_url()
        headers = _get_auth_headers()

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Step 1: Create a challenge for the factor
            challenge_resp = await client.post(
                f"{auth_url}/factors/{body.factor_id}/challenge",
                headers=headers,
            )

            if challenge_resp.status_code not in (200, 201):
                logger.error("MFA challenge creation failed during verify", status=challenge_resp.status_code)
                raise HTTPException(status_code=400, detail="Failed to create MFA challenge")

            challenge_data = challenge_resp.json()
            challenge_id = challenge_data.get("id")

            # Step 2: Verify the challenge with the TOTP code
            verify_resp = await client.post(
                f"{auth_url}/factors/{body.factor_id}/verify",
                headers=headers,
                json={
                    "challenge_id": challenge_id,
                    "code": body.code,
                },
            )

            if verify_resp.status_code == 200:
                verify_data = verify_resp.json()
                logger.info("MFA factor verified successfully", user_id=user["id"], factor_id=body.factor_id)
                return {
                    "success": True,
                    "message": "Two-factor authentication has been enabled",
                    "access_token": verify_data.get("access_token"),
                    "refresh_token": verify_data.get("refresh_token"),
                }
            elif verify_resp.status_code == 422:
                raise HTTPException(status_code=400, detail="Invalid verification code. Please try again.")
            else:
                logger.warning("MFA verify failed", status=verify_resp.status_code, body=verify_resp.text)
                raise HTTPException(status_code=400, detail="Verification failed — check your code and try again")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("MFA verification error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to verify MFA code")


@router.post("/mfa/challenge")
async def create_challenge(body: MfaChallengeRequest, user: dict = Depends(get_current_user)):
    """
    Create an MFA challenge for a verified factor.
    Used during login when the user has aal1 but needs to step up to aal2.
    Returns a challenge_id that must be verified with /mfa/challenge/verify.
    """
    try:
        auth_url = _get_supabase_auth_url()
        headers = _get_auth_headers()

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{auth_url}/factors/{body.factor_id}/challenge",
                headers=headers,
            )

            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    "challenge_id": data.get("id"),
                    "factor_id": body.factor_id,
                    "expires_at": data.get("expires_at"),
                }
            elif resp.status_code == 401:
                raise HTTPException(status_code=401, detail="Session expired")
            else:
                logger.warning("MFA challenge creation failed", status=resp.status_code, body=resp.text)
                raise HTTPException(status_code=400, detail="Failed to create MFA challenge")

    except Exception as e:
        logger.error("MFA challenge error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create MFA challenge")


@router.post("/mfa/challenge/verify")
async def verify_challenge(body: MfaChallengeVerifyRequest, user: dict = Depends(get_current_user)):
    """
    Verify an MFA challenge to upgrade the session to aal2.
    Returns new access and refresh tokens with aal2 assurance level.
    """
    try:
        auth_url = _get_supabase_auth_url()
        headers = _get_auth_headers()

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{auth_url}/factors/{body.factor_id}/verify",
                headers=headers,
                json={
                    "challenge_id": body.challenge_id,
                    "code": body.code,
                },
            )

            if resp.status_code == 200:
                data = resp.json()
                logger.info("MFA challenge verified — session upgraded to aal2", user_id=user["id"])
                return {
                    "success": True,
                    "access_token": data.get("access_token"),
                    "refresh_token": data.get("refresh_token"),
                }
            elif resp.status_code == 422:
                raise HTTPException(status_code=400, detail="Invalid TOTP code. Please check and try again.")
            else:
                logger.warning("MFA challenge verify failed", status=resp.status_code, body=resp.text)
                raise HTTPException(status_code=400, detail="Challenge verification failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("MFA challenge verification error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to verify MFA challenge")


@router.delete("/mfa/unenroll")
async def unenroll_factor(body: MfaUnenrollRequest, user: dict = Depends(get_current_user)):
    """
    Remove an enrolled TOTP factor.
    This disables 2FA for the user. The user must currently have an aal2 session.
    
    SECURITY: super_admin and tenant admin roles cannot unenroll MFA — 
    it is mandatory for elevated roles.
    """
    # Block privileged roles from disabling MFA
    if user.get("platform_role") == "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Super Admins cannot disable MFA — it is mandatory for platform security."
        )

    if user.get("org_role") == "admin":
        raise HTTPException(
            status_code=403,
            detail="Organization Admins cannot disable MFA — it is required for workspace security."
        )

    try:
        auth_url = _get_supabase_auth_url()
        headers = _get_auth_headers()

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(
                f"{auth_url}/factors/{body.factor_id}",
                headers=headers,
            )

            if resp.status_code in (200, 204):
                logger.info("MFA factor unenrolled", user_id=user["id"], factor_id=body.factor_id)
                return {
                    "success": True,
                    "message": "Two-factor authentication has been disabled",
                }
            elif resp.status_code == 401:
                raise HTTPException(status_code=401, detail="Session expired — aal2 session required")
            elif resp.status_code == 404:
                raise HTTPException(status_code=404, detail="Factor not found")
            else:
                logger.warning("MFA unenroll failed", status=resp.status_code, body=resp.text)
                raise HTTPException(status_code=400, detail="Failed to remove MFA factor")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("MFA unenroll error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to unenroll MFA factor")


@router.get("/mfa/status")
async def mfa_status(user: dict = Depends(get_current_user)):
    """
    Quick endpoint to check the current user's MFA status.
    Returns whether MFA is active and whether the current session is at aal2.
    """
    settings = get_settings()
    is_dev = settings.debug or settings.environment == "development"
    
    # Hide MFA required banner in development
    effective_role = resolve_effective_org_role(user)
    is_privileged = (
        user.get("platform_role") in ("super_admin", "billing_admin")
        or has_role_level(effective_role, "admin")
    )
    mfa_required = False if is_dev else is_privileged

    return {
        "mfa_active": user.get("mfa_active", False),
        "platform_role": user.get("platform_role", "user"),
        "org_role": user.get("org_role"),
        "mfa_required": mfa_required,
        "enforcement": {
            "super_admin": "hard_block",
            "billing_admin": "hard_block",
            "org_admin": "hard_block",
            "workspace_owner": "hard_block",
            "other": "optional",
        },
    }
