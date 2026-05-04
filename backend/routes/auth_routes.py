"""
backend/routes/auth_routes.py
─────────────────────────────
Login using your existing AspNetUsers table.

Controlled by .env variable:
  CHECK_PASSWORD=false  → only check if username/email exists in DB
  CHECK_PASSWORD=true   → also verify password against PasswordHash
"""

import logging
import hashlib
import hmac
import base64
import struct
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from services.database_service import get_connection
from config import CHECK_PASSWORD

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class AuthSuccessResponse(BaseModel):
    status: str = "success"
    message: str
    user: dict


class AuthErrorResponse(BaseModel):
    status: str = "error"
    message: str


# ── ASP.NET Identity v3 Password Verifier ────────────────────────────────────

def _verify_aspnet_password(plain_password: str, hash_b64: str) -> bool:
    try:
        hash_bytes = base64.b64decode(hash_b64)
    except Exception:
        logger.error("Failed to base64-decode PasswordHash.")
        return False

    try:
        version = hash_bytes[0]
        if version != 0x01:
            logger.warning("ASP.NET Identity v2 hash detected — not supported.")
            return False

        iter_count  = struct.unpack_from('>I', hash_bytes, 5)[0]
        salt_length = struct.unpack_from('>I', hash_bytes, 9)[0]
        salt        = hash_bytes[13 : 13 + salt_length]
        stored_key  = hash_bytes[13 + salt_length:]

        derived_key = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt,
            iter_count,
            dklen=len(stored_key),
        )

        return hmac.compare_digest(derived_key, stored_key)

    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False


# ── DB Helper ─────────────────────────────────────────────────────────────────

def _get_user(username_or_email: str) -> dict | None:
    try:
        conn   = get_connection()
        cursor = conn.cursor()

        normalised = username_or_email.strip().upper()

        cursor.execute(
    """
    SELECT
        Id,
        UserName,
        Email,
        PasswordHash,
        CustomerId,
        Disabled,
        UserProfileName,
        IsSuperUser,
        CAST(LockoutEnd AS nvarchar(50)),
        AccessFailedCount
    FROM AspNetUsers
    WHERE UPPER(UserName) = ?
       OR UPPER(Email)    = ?
    """,
    (normalised, normalised),
)

        row = cursor.fetchone()
        conn.close()

        if not row:
            logger.warning(f"No user found for: '{normalised}'")
            return None

        logger.info(f"User found: {row[1]}")
        return {
            "id":            row[0],
            "username":      row[1],
            "email":         row[2],
            "password_hash": row[3],
            "customer_id":   row[4],
            "disabled":      bool(row[5]),
            "profile_name":  row[6],
            "is_super_user": bool(row[7]) if row[7] is not None else False,
            "lockout_end":   row[8],
            "access_failed": row[9],
        }

    except Exception as e:
        logger.error(f"DB error looking up user: {e}")
        return None


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/login")
def login(req: LoginRequest):
    username = req.username.strip()
    password = req.password

    if not username:
        return AuthErrorResponse(message="Email is required.")

    # 1. Check if user exists in DB
    user = _get_user(username)
    if not user:
        return AuthErrorResponse(message="User not found. Please check your email.")

    # 2. If CHECK_PASSWORD=false → username exists = access granted
    #    If CHECK_PASSWORD=true  → also verify password
    if CHECK_PASSWORD:
        logger.info(f"CHECK_PASSWORD=true → verifying password for '{username}'")
        if not user["password_hash"]:
            return AuthErrorResponse(message="No password set for this account.")
        if not _verify_aspnet_password(password, user["password_hash"]):
            return AuthErrorResponse(message="Invalid password.")
    else:
        logger.info(f"CHECK_PASSWORD=false → user '{username}' granted access without password check")

    # 3. Success
    return AuthSuccessResponse(
        message="Login successful.",
        user={
            "id":          user["id"],
            "username":    user["username"],
            "email":       user["email"],
            "customerId":  user["customer_id"],
            "profileName": user["profile_name"] or user["username"],
            "isSuperUser": user["is_super_user"],
        },
    )


@router.post("/logout")
def logout():
    return {"status": "success", "message": "Logged out."}