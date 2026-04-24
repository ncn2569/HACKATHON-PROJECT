import hashlib
import secrets
from datetime import datetime

try:
    from .data_pool import run_query
except ImportError:
    from data_pool import run_query


SESSION_STORE: dict[str, dict] = {}


# Hash password using SHA-256, matching logic from login sample.
def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# Validate password against either hashed or plain-stored value (hackathon-safe fallback).
def _match_password(stored_password_hash: str, input_password: str) -> bool:
    if not stored_password_hash:
        return False

    # Preferred: stored hash compared to sha256(input).
    if stored_password_hash == _hash_password(input_password):
        return True

    # Fallback for seeded demo data where password_hash may be plain text.
    if stored_password_hash == input_password:
        return True

    return False


# Authenticate user from PostgreSQL users table and open session token.
def login_user(email: str, password: str) -> dict:
    if not email or not password:
        return {"success": False, "message": "Vui long nhap email va mat khau."}

    rows = run_query(
        """
        SELECT user_id, email, password_hash, role, created_at
        FROM users
        WHERE LOWER(email) = LOWER(%s)
        LIMIT 1
        """,
        (email,),
    )

    if not rows:
        return {"success": False, "message": "Email chua duoc dang ky."}

    user = rows[0]
    if not _match_password(str(user.get("password_hash", "")), password):
        return {"success": False, "message": "Mat khau khong dung."}

    token = secrets.token_hex(16)
    session_user = {
        "user_id": int(user["user_id"]),
        "email": user.get("email", ""),
        "role": user.get("role", "student"),
        "created_at": str(user.get("created_at", "")),
    }
    SESSION_STORE[token] = {
        "user": session_user,
        "login_at": datetime.utcnow().isoformat(),
    }

    return {
        "success": True,
        "message": "Dang nhap thanh cong!",
        "session_token": token,
        "user": session_user,
    }


# Invalidate current session token.
def logout_user(session_token: str) -> dict:
    if not session_token:
        return {"success": False, "message": "Thieu session token."}

    removed = SESSION_STORE.pop(session_token, None)
    if removed is None:
        return {"success": False, "message": "Session khong ton tai hoac da het han."}

    return {"success": True, "message": "Dang xuat thanh cong."}


# Resolve user from active token.
def get_session_user(session_token: str) -> dict | None:
    if not session_token:
        return None
    session = SESSION_STORE.get(session_token)
    if not session:
        return None
    return session.get("user")
