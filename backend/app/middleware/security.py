"""
Security middleware stack for the AI Incubator backend.
Provides: rate limiting, request correlation IDs, JWT auth, and timing.
"""

import uuid
import time
import structlog
import jwt
from collections import defaultdict
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
from app.config import get_settings

logger = structlog.get_logger()
security_scheme = HTTPBearer(auto_error=False)

# ═══════════════════════════════════════════════════════════════════
# MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60, burst_limit: int = 10):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.burst = burst_limit
        self._windows: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _clean_window(self, key: str, now: float):
        cutoff = now - 60.0
        self._windows[key] = [t for t in self._windows[key] if t > cutoff]

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.time()
        
        self._clean_window(client_ip, now)

        if len(self._windows[client_ip]) >= self.rpm:
            logger.warning("Rate limit exceeded", client_ip=client_ip, path=request.url.path)
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "detail": f"Max {self.rpm} requests per minute"},
                headers={"Retry-After": "60"},
            )

        self._windows[client_ip].append(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        response.headers["X-RateLimit-Remaining"] = str(self.rpm - len(self._windows[client_ip]))
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        if request.url.path not in ("/health", "/"):
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        return response


# ═══════════════════════════════════════════════════════════════════
# AUTH DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> dict:
    """
    Validates the custom JWT and returns the user payload.
    """
    settings = get_settings()

    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=["HS256"]
        )
        # Check mock db if user exists
        from app.models.database import _mock_db
        user_id = payload.get("sub")
        if not user_id or user_id not in _mock_db["users"]:
             raise HTTPException(status_code=401, detail="User not found")
             
        return _mock_db["users"][user_id]

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

