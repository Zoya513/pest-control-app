"""Authentication & permission helpers."""
import os
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request

JWT_ALG = "HS256"


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def _secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str, minutes: int = 60 * 12) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=minutes),
        "type": "access",
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALG)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=[JWT_ALG])


async def get_current_user(request: Request):
    from server import db  # lazy to avoid circular
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"password_hash": 0, "_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.get("status") != "active":
        raise HTTPException(status_code=403, detail="Account disabled")
    return user


# ---- Permission System ----
MODULES = [
    "tasks", "customers", "service_reports", "attendance", "location",
    "members", "leave", "reports", "schedule", "travel", "settings", "audit_log",
    "monthly_reports", "email", "branding"
]
ACTIONS = ["view", "create", "update", "delete", "approve", "export", "track", "manage"]


def default_admin_permissions() -> dict:
    return {m: {a: True for a in ACTIONS} for m in MODULES}


def default_developer_permissions() -> dict:
    perms = {m: {a: False for a in ACTIONS} for m in MODULES}
    perms["branding"] = {a: True for a in ACTIONS}
    perms["settings"] = {a: True for a in ACTIONS}
    perms["audit_log"] = {"view": True, "export": True, "create": False, "update": False, "delete": False, "approve": False, "track": False, "manage": False}
    return perms


def default_client_permissions() -> dict:
    """Client can only VIEW data related to their own customer_id (backend scopes it)."""
    perms = {m: {a: False for a in ACTIONS} for m in MODULES}
    perms["tasks"]["view"] = True
    perms["service_reports"].update({"view": True, "export": True})
    perms["attendance"]["view"] = True
    perms["location"]["view"] = True
    perms["schedule"]["view"] = True
    perms["monthly_reports"].update({"view": True, "export": True})
    perms["reports"].update({"view": True, "export": True})
    return perms


def default_technician_permissions() -> dict:
    perms = {m: {a: False for a in ACTIONS} for m in MODULES}
    perms["tasks"].update({"view": True, "update": True})
    perms["customers"]["view"] = True
    perms["service_reports"].update({"view": True, "create": True, "update": True})
    perms["attendance"].update({"view": True, "create": True})
    perms["location"]["view"] = True
    perms["leave"].update({"view": True, "create": True})
    perms["schedule"]["view"] = True
    perms["travel"].update({"view": True, "track": True})
    return perms


def require_permission(user: dict, module: str, action: str):
    if user.get("role") == "admin":
        return True
    perms = user.get("permissions") or {}
    if not perms.get(module, {}).get(action, False):
        raise HTTPException(status_code=403, detail=f"Missing permission: {module}.{action}")
    return True


def has_permission(user: dict, module: str, action: str) -> bool:
    if user.get("role") == "admin":
        return True
    return (user.get("permissions") or {}).get(module, {}).get(action, False)
