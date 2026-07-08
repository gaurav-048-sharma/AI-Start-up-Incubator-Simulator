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
import bcrypt
import uuid

from app.config import get_settings
from app.middleware.security import get_current_user
from app.models.database import get_db_service

logger = structlog.get_logger()
router = APIRouter()

_OTP_STORE = {}

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str

class ResendOtpRequest(BaseModel):
    email: EmailStr

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

def _generate_and_store_otp(email: str) -> str:
    otp = str(random.randint(100000, 999999))
    _OTP_STORE[email] = {
        "otp": otp,
        "expires": time.time() + 300
    }
    logger.info("Generated OTP for testing", email=email, otp=otp)
    return otp

async def _send_otp_email(email: str, otp: str):
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eaeaea; border-radius: 10px;">
          <h2 style="color: #2563eb;">AI Start-up Incubator Simulator</h2>
          <p>Your one-time password (OTP) to verify your account is:</p>
          <h1 style="font-size: 36px; letter-spacing: 4px; color: #1e293b;">{otp}</h1>
          <p style="color: #64748b; font-size: 14px;">This code will expire in 5 minutes.</p>
        </div>
      </body>
    </html>
    """
    import asyncio
    await asyncio.to_thread(_send_email_sync, email, "Verify your AI Incubator Account", html_body)

@router.post("/signup")
async def signup(req: SignupRequest):
    email = req.email.lower().strip()
    db = get_db_service()
    
    existing = await db.get_profile_by_email(email)
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, email))
    # Hash password with native bcrypt
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(req.password.encode('utf-8'), salt).decode('utf-8')
    
    user_data = {
        "id": user_id,
        "email": email,
        "full_name": req.full_name,
        "password_hash": hashed_password,
        "is_verified": 0,
        "role": "founder",
        "tier": "enterprise"
    }
    
    await db.update_profile(user_id, user_data)
    
    # Send OTP
    otp = _generate_and_store_otp(email)
    await _send_otp_email(email, otp)
    
    return {"message": "User created. Please verify your email."}

@router.post("/verify-signup")
async def verify_signup(req: VerifyOtpRequest):
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
        
    del _OTP_STORE[email]
    
    db = get_db_service()
    user_data = await db.get_profile_by_email(email)
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
        
    await db.update_profile(user_data["id"], {"is_verified": 1})
    
    # Issue JWT
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_data["id"],
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expiry_hours)
    }
    
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
    
    user_data["is_verified"] = 1
    return {
        "access_token": token,
        "user": user_data
    }

@router.post("/login")
async def login(req: LoginRequest):
    email = req.email.lower().strip()
    db = get_db_service()
    
    user_data = await db.get_profile_by_email(email)
    if not user_data:
        raise HTTPException(status_code=400, detail="Invalid email or password")
        
    stored_hash = user_data.get("password_hash", "")
    try:
        if not bcrypt.checkpw(req.password.encode('utf-8'), stored_hash.encode('utf-8')):
            raise HTTPException(status_code=400, detail="Invalid email or password")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid email or password")
        
    if not user_data.get("is_verified"):
        raise HTTPException(status_code=403, detail="Please verify your email first")
        
    # Issue JWT
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_data["id"],
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expiry_hours)
    }
    
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
    
    return {
        "access_token": token,
        "user": user_data
    }

@router.post("/resend-otp")
async def resend_otp(req: ResendOtpRequest):
    email = req.email.lower().strip()
    db = get_db_service()
    
    user_data = await db.get_profile_by_email(email)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user_data.get("is_verified"):
        raise HTTPException(status_code=400, detail="User is already verified")
        
    otp = _generate_and_store_otp(email)
    await _send_otp_email(email, otp)
    
    return {"message": "OTP resent"}

@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user

@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}
