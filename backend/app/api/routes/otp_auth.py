import random
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import jwt
from datetime import datetime, timedelta, timezone
import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from app.config import get_settings
from app.models.database import _mock_db
from app.middleware.security import get_current_user

logger = structlog.get_logger()
router = APIRouter()

# In-memory store for OTPs: { "email@example.com": {"otp": "123456", "expires": 1690000000.0} }
_OTP_STORE = {}

class SendOtpRequest(BaseModel):
    email: EmailStr

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str

def _send_email_sync(to_email: str, subject: str, body: str):
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        logger.warning("SMTP not configured. Skipping email send.", to_email=to_email, body=body)
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.smtp_from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
        logger.info("OTP email sent successfully", email=to_email)
    except Exception as e:
        logger.error("Failed to send OTP email", error=str(e), email=to_email)
        raise HTTPException(status_code=500, detail="Failed to send email. Please try again.")

@router.post("/send-otp")
async def send_otp(req: SendOtpRequest):
    email = req.email.lower().strip()
    
    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    
    # Store with 5-minute expiry
    _OTP_STORE[email] = {
        "otp": otp,
        "expires": time.time() + 300
    }
    logger.info("Generated OTP for testing", email=email, otp=otp)
    
    # Send email
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eaeaea; border-radius: 10px;">
          <h2 style="color: #2563eb;">AI Start-up Incubator Simulator</h2>
          <p>Your one-time password (OTP) to sign in is:</p>
          <h1 style="font-size: 36px; letter-spacing: 4px; color: #1e293b;">{otp}</h1>
          <p style="color: #64748b; font-size: 14px;">This code will expire in 5 minutes.</p>
        </div>
      </body>
    </html>
    """
    import asyncio
    await asyncio.to_thread(_send_email_sync, email, "Your AI Incubator Login Code", html_body)
    
    return {"message": "OTP sent successfully"}


@router.post("/verify-otp")
async def verify_otp(req: VerifyOtpRequest):
    email = req.email.lower().strip()
    otp = req.otp.strip()
    
    stored = _OTP_STORE.get(email)
    if not stored:
        raise HTTPException(status_code=400, detail="No OTP requested for this email")
        
    if time.time() > stored["expires"]:
        del _OTP_STORE[email]
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
        
    if stored["otp"] != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    # Valid OTP! Clean up store
    del _OTP_STORE[email]
    
    # Ensure user exists in mock DB (auto-register on first login)
    user_id = f"usr_{hash(email)}"
    if user_id not in _mock_db["users"]:
        _mock_db["users"][user_id] = {
            "id": user_id,
            "email": email,
            "role": "founder",
            "tier": "enterprise" # Give all features to the user
        }
    
    # Issue JWT
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expiry_hours)
    }
    
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
    
    return {
        "access_token": token,
        "user": _mock_db["users"][user_id]
    }


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user


@router.post("/logout")
async def logout():
    # Client handles clearing JWT from local storage
    return {"message": "Logged out successfully"}
