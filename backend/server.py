"""PestOps Pro - Field Operations Management Platform for Pest Control.
Backend: FastAPI + MongoDB.
"""
from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import io
import uuid
import math
import logging
from datetime import datetime, timezone, timedelta, date
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File, Query, Header, Body
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

from auth import (
    hash_password, verify_password, create_access_token, get_current_user,
    require_permission, has_permission, default_admin_permissions,
    default_technician_permissions, default_client_permissions,
    default_developer_permissions, MODULES, ACTIONS
)
from storage import init_storage, put_object, get_object, APP_NAME
from reports import (
    generate_service_report_pdf, generate_attendance_excel,
    generate_simple_pdf, generate_simple_excel
)
from emailer import send_email_with_attachments, render_report_email, EMAIL_FROM_NAME
import httpx
import zipfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pestops")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="PestOps Pro")
api = APIRouter(prefix="/api")


# ---------- utilities ----------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def uid() -> str:
    return str(uuid.uuid4())


def clean(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


async def audit(user: dict, action: str, module: str, record_id: str, old=None, new=None, ip: str = ""):
    await db.audit_logs.insert_one({
        "id": uid(),
        "user_id": user["id"],
        "user_name": user.get("full_name") or user["email"],
        "action": action,
        "module": module,
        "record_id": record_id,
        "old_value": old,
        "new_value": new,
        "ip": ip,
        "timestamp": now_iso(),
    })


# ---------- Models (pydantic) ----------
class LoginBody(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "technician"  # admin | technician
    position: Optional[str] = ""
    phone: Optional[str] = ""
    address: Optional[str] = ""
    id_number: Optional[str] = ""
    leave_quota: int = 12


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    id_number: Optional[str] = None
    leave_quota: Optional[int] = None
    status: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[dict] = None
    profile_photo: Optional[str] = None


class CustomerCreate(BaseModel):
    company_name: str
    contact_person: str = ""
    phone: str = ""
    email: str = ""
    project_name: str = ""
    address: str = ""
    location_text: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    category: str = "Regular"
    contract_start: Optional[str] = None
    contract_end: Optional[str] = None
    photo: Optional[str] = None
    # Optional client login credentials (when Admin wants to create login-enabled client account)
    client_email: Optional[str] = None
    client_password: Optional[str] = None


class TaskCreate(BaseModel):
    customer_id: str
    technician_id: str
    scheduled_date: str  # YYYY-MM-DD
    scheduled_time: str = "09:00"
    deadline: Optional[str] = None  # ISO
    work_target: str
    work_description: str = ""


class GPSPing(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    task_id: Optional[str] = None
    device_id: Optional[str] = ""


class PestFinding(BaseModel):
    code: str  # F/M/C/R/A/O
    description: str = ""
    quantity: int = 0


class SRPhoto(BaseModel):
    path: str
    caption: str = ""


class ServiceReportCreate(BaseModel):
    task_id: str
    pest_description: str = ""
    scope_of_area: str = ""
    service_area: str = ""
    recommendation: str = ""
    pest_findings: List[PestFinding] = []
    technician_signature: Optional[str] = None  # storage path
    client_signature: Optional[str] = None
    photos: List[SRPhoto] = []  # multi photos with captions


class LeaveCreate(BaseModel):
    leave_type: str = "Cuti"  # Cuti | Izin
    start_date: str
    end_date: str
    return_date: Optional[str] = None
    start_time: Optional[str] = None
    reason: str
    photo: Optional[str] = None


class AttendanceCheckIn(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    photo: str  # storage path
    task_id: Optional[str] = None


class AttendanceCheckOut(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    photo: str
    attendance_id: str


class HeartbeatBody(BaseModel):
    gps_status: str = "active"  # active|searching|limited|denied
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ScheduleMassCreate(BaseModel):
    customer_id: str
    technician_id: str
    start_date: str  # YYYY-MM-DD
    end_date: str
    start_time: str = "08:00"
    end_time: str = "17:00"
    weekdays: List[int] = [0, 1, 2, 3, 4, 5]  # 0=Mon..6=Sun
    notes: str = ""


class ScheduleUpdate(BaseModel):
    technician_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class SendReportEmail(BaseModel):
    subject: str
    message: str = ""
    override_recipient: Optional[EmailStr] = None


# ---------- geocoding helpers (Nominatim proxy) ----------
async def reverse_geocode(lat: float, lon: float) -> str:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json", "zoom": 18, "addressdetails": 1},
                headers={"User-Agent": "PestOpsPro/1.0"},
            )
            r.raise_for_status()
            return r.json().get("display_name", "")
    except Exception:
        return ""


# ---------- Startup / Seed ----------
@app.on_event("startup")
async def startup():
    # Indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.customers.create_index("id", unique=True)
    await db.tasks.create_index("id", unique=True)
    await db.tasks.create_index("technician_id")
    await db.tasks.create_index("customer_id")
    await db.gps_tracking.create_index([("user_id", 1), ("timestamp", -1)])
    await db.gps_tracking.create_index("task_id")
    await db.attendance.create_index([("user_id", 1), ("date", -1)])
    await db.service_reports.create_index("task_id")
    await db.leave_requests.create_index("user_id")
    await db.audit_logs.create_index([("timestamp", -1)])
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])

    # Storage init
    init_storage()

    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@pestops.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "id": uid(),
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "full_name": "System Administrator",
            "role": "admin",
            "position": "Administrator",
            "phone": "",
            "address": "",
            "id_number": "",
            "leave_quota": 12,
            "leave_used": 0,
            "status": "active",
            "profile_photo": None,
            "permissions": default_admin_permissions(),
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })
        logger.info(f"Seeded admin {admin_email}")
    else:
        # Sync password if changed
        if not verify_password(admin_password, existing.get("password_hash", "")):
            await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})

    # Seed demo technician (re-sync password & default permissions on every startup)
    tech_email = "technician@pestops.com"
    tech_existing = await db.users.find_one({"email": tech_email})
    if not tech_existing:
        await db.users.insert_one({
            "id": uid(),
            "email": tech_email,
            "password_hash": hash_password("Tech@123"),
            "full_name": "Wawan Gunawan",
            "role": "technician",
            "position": "Field Technician",
            "phone": "+62 812-3456-7890",
            "address": "Depok, Jawa Barat",
            "id_number": "3276012345670001",
            "leave_quota": 12,
            "leave_used": 0,
            "status": "active",
            "profile_photo": None,
            "permissions": default_technician_permissions(),
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })
        logger.info("Seeded demo technician")
    else:
        # Re-sync default permissions for seeded technician to prevent drift
        await db.users.update_one(
            {"email": tech_email},
            {"$set": {"permissions": default_technician_permissions(), "role": "technician", "status": "active"}}
        )

    # Seed developer
    dev_email = "developer@pestops.com"
    if not await db.users.find_one({"email": dev_email}):
        await db.users.insert_one({
            "id": uid(),
            "email": dev_email,
            "password_hash": hash_password("Dev@123"),
            "full_name": "Developer Account",
            "role": "developer",
            "position": "System Developer",
            "phone": "", "address": "", "id_number": "",
            "leave_quota": 0, "leave_used": 0,
            "status": "active", "profile_photo": None,
            "permissions": default_developer_permissions(),
            "created_at": now_iso(), "updated_at": now_iso(),
        })
        logger.info("Seeded developer")
    else:
        await db.users.update_one({"email": dev_email},
                                  {"$set": {"permissions": default_developer_permissions(), "role": "developer", "status": "active"}})

    # Seed demo customer + client login
    demo_customer_id = None
    demo_cust = await db.customers.find_one({"company_name": "PT. John Robert Powers"})
    if not demo_cust:
        demo_customer_id = uid()
        await db.customers.insert_one({
            "id": demo_customer_id,
            "company_name": "PT. John Robert Powers",
            "project_name": "JRP Kelapa Gading Office",
            "contact_person": "ahmad",
            "phone": "+62-21-1234567",
            "email": "client@pestops.com",
            "address": "Jl. Boulevard Raya No.1 LA 3, Kelapa Gading, Jakarta Utara",
            "location_text": "Kelapa Gading",
            "latitude": -6.1568, "longitude": 106.9051,
            "category": "Corporate",
            "contract_start": "2026-01-01", "contract_end": "2026-12-31",
            "status": "active",
            "registration_date": now_iso(),
            "created_by": "system",
            "created_at": now_iso(), "updated_at": now_iso(),
        })
    else:
        demo_customer_id = demo_cust["id"]

    # Seed client login
    client_email = "client@pestops.com"
    if not await db.users.find_one({"email": client_email}):
        await db.users.insert_one({
            "id": uid(),
            "email": client_email,
            "password_hash": hash_password("Client@123"),
            "full_name": "PT. John Robert Powers",
            "role": "client",
            "position": "Client",
            "customer_id": demo_customer_id,
            "phone": "", "address": "",
            "id_number": "",
            "leave_quota": 0, "leave_used": 0,
            "status": "active", "profile_photo": None,
            "permissions": default_client_permissions(),
            "created_at": now_iso(), "updated_at": now_iso(),
        })
        logger.info("Seeded client account")
    else:
        await db.users.update_one({"email": client_email},
                                  {"$set": {"permissions": default_client_permissions(),
                                            "role": "client", "customer_id": demo_customer_id, "status": "active"}})

    # Update credentials file
    try:
        creds_path = Path("/app/memory/test_credentials.md")
        creds_path.parent.mkdir(parents=True, exist_ok=True)
        creds_path.write_text(
            "# Test Credentials — PestOps Pro\n\n"
            "## Admin\n"
            f"- Email: `{admin_email}`\n"
            f"- Password: `{admin_password}`\n"
            "- Role: admin (full permissions)\n\n"
            "## Technician\n"
            "- Email: `technician@pestops.com`\n"
            "- Password: `Tech@123`\n"
            "- Role: technician (default field permissions)\n\n"
            "## Client\n"
            "- Email: `client@pestops.com`\n"
            "- Password: `Client@123`\n"
            "- Role: client (scoped to their own customer_id)\n\n"
            "## Developer\n"
            "- Email: `developer@pestops.com`\n"
            "- Password: `Dev@123`\n"
            "- Role: developer (branding/settings only)\n\n"
            "## Auth endpoints\n"
            "- POST `/api/auth/login`\n"
            "- POST `/api/auth/logout`\n"
            "- GET  `/api/auth/me`\n"
        )
    except Exception as e:
        logger.warning(f"credentials file write: {e}")


# ================= AUTH =================
@api.post("/auth/login")
async def login(body: LoginBody, response: Response, request: Request):
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("status") != "active":
        raise HTTPException(status_code=403, detail="Account disabled")
    token = create_access_token(user["id"], user["email"])
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="none", max_age=60 * 60 * 12, path="/")
    return {"user": clean(user), "token": token}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return clean(user)


# ================= USERS =================
@api.get("/users")
async def list_users(q: Optional[str] = None, user: dict = Depends(get_current_user)):
    require_permission(user, "members", "view")
    query = {}
    if q:
        query["$or"] = [
            {"email": {"$regex": q, "$options": "i"}},
            {"full_name": {"$regex": q, "$options": "i"}},
        ]
    users = await db.users.find(query, {"password_hash": 0, "_id": 0}).to_list(500)
    return users


@api.post("/users")
async def create_user(body: UserCreate, request: Request, user: dict = Depends(get_current_user)):
    require_permission(user, "members", "create")
    if await db.users.find_one({"email": body.email.lower()}):
        raise HTTPException(400, "Email already exists")
    perms = default_admin_permissions() if body.role == "admin" else default_technician_permissions()
    doc = {
        "id": uid(),
        "email": body.email.lower(),
        "password_hash": hash_password(body.password),
        "full_name": body.full_name,
        "role": body.role,
        "position": body.position or "",
        "phone": body.phone or "",
        "address": body.address or "",
        "id_number": body.id_number or "",
        "leave_quota": body.leave_quota,
        "leave_used": 0,
        "status": "active",
        "profile_photo": None,
        "permissions": perms,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.users.insert_one(doc)
    await audit(user, "CREATE", "members", doc["id"], None, {"email": doc["email"]}, request.client.host if request.client else "")
    return clean(doc)


@api.get("/users/{user_id}")
async def get_user(user_id: str, user: dict = Depends(get_current_user)):
    if user["id"] != user_id:
        require_permission(user, "members", "view")
    u = await db.users.find_one({"id": user_id}, {"password_hash": 0, "_id": 0})
    if not u:
        raise HTTPException(404, "Not found")
    return u


@api.put("/users/{user_id}")
async def update_user(user_id: str, body: UserUpdate, request: Request, user: dict = Depends(get_current_user)):
    is_self = user["id"] == user_id
    if not is_self:
        require_permission(user, "members", "update")
    existing = await db.users.find_one({"id": user_id})
    if not existing:
        raise HTTPException(404, "Not found")
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    # Only admins can change role/permissions/status
    if not has_permission(user, "members", "manage"):
        upd.pop("role", None)
        upd.pop("permissions", None)
        upd.pop("status", None)
    upd["updated_at"] = now_iso()
    await db.users.update_one({"id": user_id}, {"$set": upd})
    await audit(user, "UPDATE", "members", user_id, {k: existing.get(k) for k in upd}, upd,
                request.client.host if request.client else "")
    u = await db.users.find_one({"id": user_id}, {"password_hash": 0, "_id": 0})
    return u


@api.delete("/users/{user_id}")
async def delete_user(user_id: str, request: Request, user: dict = Depends(get_current_user)):
    require_permission(user, "members", "delete")
    if user_id == user["id"]:
        raise HTTPException(400, "Cannot delete self")
    await db.users.update_one({"id": user_id}, {"$set": {"status": "disabled", "updated_at": now_iso()}})
    await audit(user, "DELETE", "members", user_id, None, None, request.client.host if request.client else "")
    return {"ok": True}


# ================= CUSTOMERS =================
@api.get("/customers")
async def list_customers(q: Optional[str] = None, status: Optional[str] = None,
                         user: dict = Depends(get_current_user)):
    require_permission(user, "customers", "view")
    query = {}
    if q:
        query["$or"] = [
            {"company_name": {"$regex": q, "$options": "i"}},
            {"contact_person": {"$regex": q, "$options": "i"}},
        ]
    if status:
        query["status"] = status
    docs = await db.customers.find(query, {"_id": 0}).to_list(500)
    # Auto-inactive if contract ended
    today = date.today().isoformat()
    for d in docs:
        if d.get("contract_end") and d["contract_end"] < today and d.get("status") != "inactive":
            await db.customers.update_one({"id": d["id"]}, {"$set": {"status": "inactive"}})
            d["status"] = "inactive"
    return docs


@api.post("/customers")
async def create_customer(body: CustomerCreate, request: Request, user: dict = Depends(get_current_user)):
    require_permission(user, "customers", "create")
    doc = body.model_dump()
    # Remove client credentials from customer doc
    client_email = doc.pop("client_email", None)
    client_password = doc.pop("client_password", None)
    doc.update({
        "id": uid(),
        "status": "active",
        "registration_date": now_iso(),
        "last_visit": None,
        "created_by": user["id"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    })
    await db.customers.insert_one(doc)
    # Optionally create a client login account tied to this customer
    if client_email and client_password:
        client_email = client_email.lower()
        if not await db.users.find_one({"email": client_email}):
            await db.users.insert_one({
                "id": uid(),
                "email": client_email,
                "password_hash": hash_password(client_password),
                "full_name": doc.get("contact_person") or doc["company_name"],
                "role": "client",
                "position": "Client",
                "phone": doc.get("phone", ""),
                "address": doc.get("address", ""),
                "customer_id": doc["id"],
                "id_number": "",
                "leave_quota": 0,
                "leave_used": 0,
                "status": "active",
                "profile_photo": None,
                "permissions": default_client_permissions(),
                "created_at": now_iso(),
                "updated_at": now_iso(),
            })
    await audit(user, "CREATE", "customers", doc["id"], None, {"company_name": doc["company_name"]}, "")
    return clean(doc)


@api.put("/customers/{cid}")
async def update_customer(cid: str, body: CustomerCreate, request: Request, user: dict = Depends(get_current_user)):
    require_permission(user, "customers", "update")
    existing = await db.customers.find_one({"id": cid})
    if not existing:
        raise HTTPException(404, "Not found")
    upd = body.model_dump()
    upd["updated_at"] = now_iso()
    await db.customers.update_one({"id": cid}, {"$set": upd})
    await audit(user, "UPDATE", "customers", cid, {"company_name": existing.get("company_name")}, upd, "")
    return await db.customers.find_one({"id": cid}, {"_id": 0})


@api.delete("/customers/{cid}")
async def delete_customer(cid: str, user: dict = Depends(get_current_user)):
    require_permission(user, "customers", "delete")
    await db.customers.update_one({"id": cid}, {"$set": {"status": "inactive"}})
    await audit(user, "DELETE", "customers", cid)
    return {"ok": True}


# ================= TASKS =================
def compute_task_status(task: dict) -> str:
    if task.get("status") == "cancelled":
        return "cancelled"
    if task.get("service_report_id") and task.get("check_out_at"):
        return "completed"
    if task.get("check_in_at"):
        return "in_progress"
    # Overdue check
    sched = task.get("scheduled_date")
    dl = task.get("deadline")
    today = date.today().isoformat()
    if dl and dl < now_iso():
        return "overdue"
    if sched and sched < today:
        return "overdue"
    return "pending"


@api.get("/tasks")
async def list_tasks(filter: Optional[str] = None,
                     customer_id: Optional[str] = None,
                     technician_id: Optional[str] = None,
                     date_from: Optional[str] = None,
                     date_to: Optional[str] = None,
                     user: dict = Depends(get_current_user)):
    require_permission(user, "tasks", "view")
    query = {}
    # Client role: only see their assigned customer (hard-enforced, overrides any query param)
    if user.get("role") == "client":
        if customer_id and customer_id != user.get("customer_id"):
            raise HTTPException(403, "Forbidden: cannot query other customer's data")
        query["customer_id"] = user.get("customer_id") or "__none__"
    elif user.get("role") == "technician" and not has_permission(user, "tasks", "manage"):
        query["technician_id"] = user["id"]
        if customer_id:
            query["customer_id"] = customer_id
    else:
        if customer_id:
            query["customer_id"] = customer_id
    if technician_id and user.get("role") != "client":
        query["technician_id"] = technician_id
    if date_from:
        query["scheduled_date"] = {"$gte": date_from}
    if date_to:
        query.setdefault("scheduled_date", {})["$lte"] = date_to
    docs = await db.tasks.find(query, {"_id": 0}).sort("scheduled_date", -1).to_list(1000)
    # Enrich + compute status
    cust_ids = list({d["customer_id"] for d in docs})
    tech_ids = list({d["technician_id"] for d in docs})
    cmap = {c["id"]: c for c in await db.customers.find({"id": {"$in": cust_ids}}, {"_id": 0}).to_list(500)}
    tmap = {t["id"]: t for t in await db.users.find({"id": {"$in": tech_ids}}, {"_id": 0, "password_hash": 0}).to_list(500)}
    result = []
    for d in docs:
        d["status"] = compute_task_status(d)
        d["customer"] = cmap.get(d["customer_id"])
        d["technician"] = tmap.get(d["technician_id"])
        if filter == "pending" and d["status"] != "pending":
            continue
        if filter == "overdue" and d["status"] != "overdue":
            continue
        if filter == "completed" and d["status"] != "completed":
            continue
        if filter == "in_progress" and d["status"] != "in_progress":
            continue
        result.append(d)
    return result


@api.post("/tasks")
async def create_task(body: TaskCreate, request: Request, user: dict = Depends(get_current_user)):
    require_permission(user, "tasks", "create")
    doc = body.model_dump()
    doc.update({
        "id": uid(),
        "assigned_by": user["id"],
        "status": "pending",
        "check_in_at": None,
        "check_out_at": None,
        "service_report_id": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    })
    await db.tasks.insert_one(doc)
    await db.notifications.insert_one({
        "id": uid(),
        "user_id": body.technician_id,
        "title": "New Task Assigned",
        "message": f"You have been assigned a new task: {body.work_target}",
        "type": "task",
        "record_id": doc["id"],
        "read": False,
        "created_at": now_iso(),
    })
    await audit(user, "CREATE", "tasks", doc["id"], None, {"target": body.work_target}, "")
    return clean(doc)


@api.get("/tasks/{tid}")
async def get_task(tid: str, user: dict = Depends(get_current_user)):
    require_permission(user, "tasks", "view")
    t = await db.tasks.find_one({"id": tid}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Not found")
    if user.get("role") != "admin" and t["technician_id"] != user["id"] and not has_permission(user, "tasks", "manage"):
        raise HTTPException(403, "Forbidden")
    t["status"] = compute_task_status(t)
    t["customer"] = await db.customers.find_one({"id": t["customer_id"]}, {"_id": 0})
    t["technician"] = await db.users.find_one({"id": t["technician_id"]}, {"_id": 0, "password_hash": 0})
    return t


@api.put("/tasks/{tid}")
async def update_task(tid: str, body: dict = Body(...), user: dict = Depends(get_current_user)):
    require_permission(user, "tasks", "update")
    body.pop("id", None)
    body["updated_at"] = now_iso()
    await db.tasks.update_one({"id": tid}, {"$set": body})
    await audit(user, "UPDATE", "tasks", tid, None, body)
    return await db.tasks.find_one({"id": tid}, {"_id": 0})


@api.delete("/tasks/{tid}")
async def delete_task(tid: str, user: dict = Depends(get_current_user)):
    require_permission(user, "tasks", "delete")
    await db.tasks.delete_one({"id": tid})
    await audit(user, "DELETE", "tasks", tid)
    return {"ok": True}


# ================= ATTENDANCE =================
@api.post("/attendance/checkin")
async def checkin(body: AttendanceCheckIn, user: dict = Depends(get_current_user)):
    require_permission(user, "attendance", "create")
    geofence_ok = True
    distance = None
    if body.task_id:
        task = await db.tasks.find_one({"id": body.task_id}, {"_id": 0})
        if task:
            cust = await db.customers.find_one({"id": task["customer_id"]})
            if cust and cust.get("latitude") and cust.get("longitude"):
                distance = haversine_m(body.latitude, body.longitude, cust["latitude"], cust["longitude"])
                radius = float(os.environ.get("GEOFENCE_RADIUS_METERS", "100"))
                geofence_ok = distance <= radius
    address = await reverse_geocode(body.latitude, body.longitude)
    doc = {
        "id": uid(),
        "user_id": user["id"],
        "user_name": user.get("full_name"),
        "task_id": body.task_id,
        "type": "check_in",
        "latitude": body.latitude,
        "longitude": body.longitude,
        "accuracy": body.accuracy,
        "photo": body.photo,
        "address": address,
        "geofence_ok": geofence_ok,
        "distance_meters": distance,
        "date": date.today().isoformat(),
        "timestamp": now_iso(),
    }
    await db.attendance.insert_one(doc)
    if body.task_id:
        await db.tasks.update_one({"id": body.task_id}, {"$set": {"check_in_at": doc["timestamp"], "updated_at": now_iso()}})
    return clean(doc)


@api.post("/attendance/checkout")
async def checkout(body: AttendanceCheckOut, user: dict = Depends(get_current_user)):
    require_permission(user, "attendance", "create")
    ci = await db.attendance.find_one({"id": body.attendance_id})
    if not ci:
        raise HTTPException(404, "Check-in not found")
    address = await reverse_geocode(body.latitude, body.longitude)
    # Compute working hours
    working_hours = None
    try:
        d1 = datetime.fromisoformat(ci["timestamp"])
        d2 = datetime.now(timezone.utc)
        working_hours = round((d2 - d1).total_seconds() / 3600.0, 2)
    except Exception:
        pass
    doc = {
        "id": uid(),
        "user_id": user["id"],
        "user_name": user.get("full_name"),
        "task_id": ci.get("task_id"),
        "type": "check_out",
        "latitude": body.latitude,
        "longitude": body.longitude,
        "accuracy": body.accuracy,
        "photo": body.photo,
        "address": address,
        "checkin_ref": body.attendance_id,
        "working_hours": working_hours,
        "date": date.today().isoformat(),
        "timestamp": now_iso(),
    }
    await db.attendance.insert_one(doc)
    # update the check-in row so listing shows working_hours + checkout_address on the pair
    await db.attendance.update_one({"id": body.attendance_id}, {"$set": {
        "checkout_id": doc["id"], "working_hours": working_hours,
        "checkout_address": address, "checkout_timestamp": doc["timestamp"],
    }})
    if ci.get("task_id"):
        await db.tasks.update_one({"id": ci["task_id"]}, {"$set": {"check_out_at": doc["timestamp"], "updated_at": now_iso()}})
    return clean(doc)


@api.get("/attendance")
async def list_attendance(user_id: Optional[str] = None,
                          customer_id: Optional[str] = None,
                          date_from: Optional[str] = None,
                          date_to: Optional[str] = None,
                          user: dict = Depends(get_current_user)):
    require_permission(user, "attendance", "view")
    query = {}
    if user.get("role") == "client":
        # Filter to attendance where task's customer = client's
        cid = user.get("customer_id") or "__none__"
        tasks = await db.tasks.find({"customer_id": cid}, {"_id": 0, "id": 1}).to_list(2000)
        query["task_id"] = {"$in": [t["id"] for t in tasks]}
    elif user_id:
        query["user_id"] = user_id
    elif not has_permission(user, "attendance", "manage") and user.get("role") not in ("admin",):
        query["user_id"] = user["id"]
    if customer_id and user.get("role") != "client":
        tasks = await db.tasks.find({"customer_id": customer_id}, {"_id": 0, "id": 1}).to_list(2000)
        query["task_id"] = {"$in": [t["id"] for t in tasks]}
    if date_from:
        query["date"] = {"$gte": date_from}
    if date_to:
        query.setdefault("date", {})["$lte"] = date_to
    docs = await db.attendance.find(query, {"_id": 0}).sort("timestamp", -1).to_list(1000)
    return docs


# ================= GPS TRACKING =================
@api.post("/gps/ping")
async def gps_ping(body: GPSPing, user: dict = Depends(get_current_user)):
    # Users track their own location — require travel.track OR own-tracking (admins always allowed)
    if user.get("role") != "admin" and not has_permission(user, "travel", "track"):
        raise HTTPException(status_code=403, detail="Missing permission: travel.track")
    doc = body.model_dump()
    doc.update({
        "id": uid(),
        "user_id": user["id"],
        "timestamp": now_iso(),
    })
    await db.gps_tracking.insert_one(doc)
    await db.users.update_one({"id": user["id"]}, {"$set": {
        "last_lat": body.latitude,
        "last_lng": body.longitude,
        "last_gps_at": doc["timestamp"],
        "last_seen": doc["timestamp"],
        "online": True,
        "gps_status": "active",
    }})
    return {"ok": True}


@api.post("/heartbeat")
async def heartbeat(body: HeartbeatBody, user: dict = Depends(get_current_user)):
    upd = {"last_seen": now_iso(), "online": True, "gps_status": body.gps_status}
    if body.latitude and body.longitude:
        upd["last_lat"] = body.latitude
        upd["last_lng"] = body.longitude
        upd["last_gps_at"] = now_iso()
    await db.users.update_one({"id": user["id"]}, {"$set": upd})
    return {"ok": True}


@api.get("/gps/tracks")
async def gps_tracks(user_id: Optional[str] = None, task_id: Optional[str] = None,
                     date_from: Optional[str] = None, date_to: Optional[str] = None,
                     user: dict = Depends(get_current_user)):
    require_permission(user, "location", "view")
    query = {}
    if user_id:
        query["user_id"] = user_id
    if task_id:
        query["task_id"] = task_id
    if date_from:
        query["timestamp"] = {"$gte": date_from}
    if date_to:
        query.setdefault("timestamp", {})["$lte"] = date_to + "T23:59:59"
    docs = await db.gps_tracking.find(query, {"_id": 0}).sort("timestamp", 1).limit(2000).to_list(2000)
    return docs


@api.get("/location/live")
async def live_locations(user: dict = Depends(get_current_user)):
    require_permission(user, "location", "view")
    query = {"last_lat": {"$exists": True}}
    if user.get("role") != "admin" and not has_permission(user, "location", "track"):
        query["id"] = user["id"]
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(200)
    # Compute online status: heartbeat within 90s
    threshold = datetime.now(timezone.utc) - timedelta(seconds=90)
    for u in users:
        try:
            ls = datetime.fromisoformat(u.get("last_seen", ""))
            u["online"] = ls >= threshold
        except Exception:
            u["online"] = False
    return users


# ================= TRAVEL / PERJALANAN =================
@api.get("/travel")
async def travel_summary(user_id: Optional[str] = None, date_from: Optional[str] = None,
                         date_to: Optional[str] = None, user: dict = Depends(get_current_user)):
    require_permission(user, "travel", "view")
    query = {}
    if user_id:
        query["user_id"] = user_id
    elif user.get("role") != "admin":
        query["user_id"] = user["id"]
    if date_from:
        query["timestamp"] = {"$gte": date_from}
    if date_to:
        query.setdefault("timestamp", {})["$lte"] = date_to + "T23:59:59"
    tracks = await db.gps_tracking.find(query, {"_id": 0}).sort("timestamp", 1).to_list(5000)

    # Group by user_id + task_id
    groups: Dict[str, List[dict]] = {}
    for t in tracks:
        key = f"{t['user_id']}::{t.get('task_id') or 'nomission'}"
        groups.setdefault(key, []).append(t)

    out = []
    for key, pts in groups.items():
        if len(pts) < 2:
            continue
        dist = 0.0
        for i in range(1, len(pts)):
            dist += haversine_m(pts[i - 1]["latitude"], pts[i - 1]["longitude"], pts[i]["latitude"], pts[i]["longitude"])
        u_id, t_id = key.split("::")
        out.append({
            "user_id": u_id,
            "task_id": None if t_id == "nomission" else t_id,
            "start_time": pts[0]["timestamp"],
            "end_time": pts[-1]["timestamp"],
            "distance_m": round(dist, 2),
            "point_count": len(pts),
            "start": {"lat": pts[0]["latitude"], "lng": pts[0]["longitude"]},
            "end": {"lat": pts[-1]["latitude"], "lng": pts[-1]["longitude"]},
        })
    return out


# ================= SERVICE REPORT =================
@api.post("/service-reports")
async def create_sr(body: ServiceReportCreate, request: Request, user: dict = Depends(get_current_user)):
    require_permission(user, "service_reports", "create")
    task = await db.tasks.find_one({"id": body.task_id})
    if not task:
        raise HTTPException(404, "Task not found")
    # Auto-generate report number
    count = await db.service_reports.count_documents({})
    report_no = f"SR-{datetime.now().strftime('%Y%m')}-{count + 1:04d}"
    now = datetime.now(timezone.utc)
    doc = body.model_dump()
    doc.update({
        "id": uid(),
        "report_number": report_no,
        "date": now.date().isoformat(),
        "time": now.strftime("%H:%M:%S"),
        "technician_id": task["technician_id"],
        "customer_id": task["customer_id"],
        "status": "submitted",
        "created_by": user["id"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    })
    await db.service_reports.insert_one(doc)
    await db.tasks.update_one({"id": body.task_id}, {"$set": {"service_report_id": doc["id"], "status": "completed", "updated_at": now_iso()}})
    await audit(user, "CREATE", "service_reports", doc["id"], None, {"task_id": body.task_id, "report": report_no})
    return clean(doc)


@api.get("/service-reports")
async def list_sr(customer_id: Optional[str] = None,
                  technician_id: Optional[str] = None,
                  date_from: Optional[str] = None,
                  date_to: Optional[str] = None,
                  user: dict = Depends(get_current_user)):
    require_permission(user, "service_reports", "view")
    query = {}
    if user.get("role") == "client":
        if customer_id and customer_id != user.get("customer_id"):
            raise HTTPException(403, "Forbidden")
        query["customer_id"] = user.get("customer_id") or "__none__"
    elif user.get("role") == "technician" and not has_permission(user, "service_reports", "manage"):
        query["technician_id"] = user["id"]
        if customer_id:
            query["customer_id"] = customer_id
    else:
        if customer_id:
            query["customer_id"] = customer_id
    if technician_id and user.get("role") != "client":
        query["technician_id"] = technician_id
    if date_from:
        query["date"] = {"$gte": date_from}
    if date_to:
        query.setdefault("date", {})["$lte"] = date_to
    docs = await db.service_reports.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    # Enrich with customer + technician names
    cust_ids = list({d["customer_id"] for d in docs})
    tech_ids = list({d["technician_id"] for d in docs})
    cmap = {c["id"]: c for c in await db.customers.find({"id": {"$in": cust_ids}}, {"_id": 0}).to_list(500)}
    tmap = {t["id"]: t for t in await db.users.find({"id": {"$in": tech_ids}}, {"_id": 0, "password_hash": 0}).to_list(500)}
    for d in docs:
        d["customer_name"] = cmap.get(d["customer_id"], {}).get("company_name", "")
        d["technician_name"] = tmap.get(d["technician_id"], {}).get("full_name", "")
    return docs


@api.get("/service-reports/{sid}")
async def get_sr(sid: str, user: dict = Depends(get_current_user)):
    require_permission(user, "service_reports", "view")
    sr = await db.service_reports.find_one({"id": sid}, {"_id": 0})
    if not sr:
        raise HTTPException(404, "Not found")
    sr["task"] = await db.tasks.find_one({"id": sr["task_id"]}, {"_id": 0})
    sr["customer"] = await db.customers.find_one({"id": sr["customer_id"]}, {"_id": 0})
    sr["technician"] = await db.users.find_one({"id": sr["technician_id"]}, {"_id": 0, "password_hash": 0})
    return sr


@api.get("/service-reports/{sid}/pdf")
async def sr_pdf(sid: str, user: dict = Depends(get_current_user)):
    require_permission(user, "service_reports", "export")
    sr = await db.service_reports.find_one({"id": sid}, {"_id": 0})
    if not sr:
        raise HTTPException(404, "Not found")
    task = await db.tasks.find_one({"id": sr["task_id"]}, {"_id": 0}) or {}
    cust = await db.customers.find_one({"id": sr["customer_id"]}, {"_id": 0}) or {}
    tech = await db.users.find_one({"id": sr["technician_id"]}, {"_id": 0, "password_hash": 0}) or {}
    pdf = generate_service_report_pdf(sr, task, cust, tech)
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={sr['report_number']}.pdf"})


# ================= LEAVE =================
@api.post("/leave")
async def create_leave(body: LeaveCreate, user: dict = Depends(get_current_user)):
    require_permission(user, "leave", "create")
    doc = body.model_dump()
    doc.update({
        "id": uid(),
        "user_id": user["id"],
        "user_name": user.get("full_name"),
        "status": "pending",
        "created_at": now_iso(),
        "reviewed_by": None,
        "reviewed_at": None,
    })
    await db.leave_requests.insert_one(doc)
    return clean(doc)


@api.get("/leave")
async def list_leave(user: dict = Depends(get_current_user)):
    require_permission(user, "leave", "view")
    query = {}
    if user.get("role") != "admin" and not has_permission(user, "leave", "approve"):
        query["user_id"] = user["id"]
    docs = await db.leave_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return docs


@api.post("/leave/{lid}/decide")
async def decide_leave(lid: str, decision: str = Body(..., embed=True), user: dict = Depends(get_current_user)):
    require_permission(user, "leave", "approve")
    if decision not in ("approved", "rejected"):
        raise HTTPException(400, "Invalid decision")
    lv = await db.leave_requests.find_one({"id": lid})
    if not lv:
        raise HTTPException(404, "Not found")
    await db.leave_requests.update_one({"id": lid}, {"$set": {"status": decision, "reviewed_by": user["id"], "reviewed_at": now_iso()}})
    if decision == "approved":
        # Compute days
        try:
            sd = datetime.fromisoformat(lv["start_date"]).date()
            ed = datetime.fromisoformat(lv["end_date"]).date()
            days = (ed - sd).days + 1
            await db.users.update_one({"id": lv["user_id"]}, {"$inc": {"leave_used": days}})
        except Exception:
            pass
    await audit(user, decision.upper(), "leave", lid, {"status": "pending"}, {"status": decision})
    return {"ok": True}


# ================= FILE UPLOAD =================
@api.post("/upload")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = (file.filename or "bin").rsplit(".", 1)[-1].lower()
    path = f"{APP_NAME}/uploads/{user['id']}/{uid()}.{ext}"
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/octet-stream")
    await db.files.insert_one({
        "id": uid(),
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": file.content_type,
        "size": result.get("size", len(data)),
        "uploaded_by": user["id"],
        "created_at": now_iso(),
    })
    return {"path": result["path"], "size": result.get("size", len(data))}


@api.post("/upload/base64")
async def upload_b64(payload: dict = Body(...), user: dict = Depends(get_current_user)):
    """Upload base64 dataURL (used for camera photos & signatures)."""
    import base64
    data_url = payload.get("data", "")
    ext = payload.get("ext", "png")
    if "," in data_url:
        header, b64 = data_url.split(",", 1)
        # detect content type
        ct = "image/png"
        if "image/jpeg" in header:
            ct = "image/jpeg"
        elif "image/webp" in header:
            ct = "image/webp"
    else:
        b64 = data_url
        ct = "image/png"
    binary = base64.b64decode(b64)
    path = f"{APP_NAME}/uploads/{user['id']}/{uid()}.{ext}"
    result = put_object(path, binary, ct)
    return {"path": result["path"]}


@api.get("/files/{path:path}")
async def download_file(path: str, request: Request, auth: Optional[str] = Query(None)):
    # allow token via query param for <img> tags
    try:
        token = request.cookies.get("access_token") or auth
        if not token:
            raise HTTPException(401, "Not authenticated")
        from auth import decode_token
        decode_token(token)
    except Exception:
        raise HTTPException(401, "Invalid token")
    try:
        data, ct = get_object(path)
    except Exception:
        raise HTTPException(404, "File not found")
    return Response(content=data, media_type=ct)


# ================= NOTIFICATIONS =================
@api.get("/notifications")
async def list_notifs(user: dict = Depends(get_current_user)):
    docs = await db.notifications.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return docs


@api.post("/notifications/{nid}/read")
async def mark_read(nid: str, user: dict = Depends(get_current_user)):
    await db.notifications.update_one({"id": nid, "user_id": user["id"]}, {"$set": {"read": True}})
    return {"ok": True}


# ================= AUDIT LOG =================
@api.get("/audit-logs")
async def list_audit(user: dict = Depends(get_current_user)):
    require_permission(user, "audit_log", "view")
    docs = await db.audit_logs.find({}, {"_id": 0}).sort("timestamp", -1).limit(500).to_list(500)
    return docs


# ================= DASHBOARD =================
@api.get("/dashboard")
async def dashboard(user: dict = Depends(get_current_user)):
    is_admin = user.get("role") == "admin" or has_permission(user, "tasks", "manage")
    task_q = {} if is_admin else {"technician_id": user["id"]}
    all_tasks = await db.tasks.find(task_q, {"_id": 0}).to_list(1000)
    today = date.today().isoformat()
    for t in all_tasks:
        t["status"] = compute_task_status(t)
    tasks_summary = {
        "total": len(all_tasks),
        "pending": sum(1 for t in all_tasks if t["status"] == "pending"),
        "overdue": sum(1 for t in all_tasks if t["status"] == "overdue"),
        "completed": sum(1 for t in all_tasks if t["status"] == "completed"),
        "today": sum(1 for t in all_tasks if t.get("scheduled_date") == today),
    }

    # Technician summary (admin only)
    tech_summary = None
    if is_admin:
        techs = await db.users.find({"role": "technician"}, {"_id": 0, "password_hash": 0}).to_list(500)
        threshold = datetime.now(timezone.utc) - timedelta(seconds=90)
        online = 0
        for tt in techs:
            try:
                ls = datetime.fromisoformat(tt.get("last_seen", ""))
                if ls >= threshold:
                    online += 1
            except Exception:
                pass
        # On task = has task in progress
        in_prog_tech = set()
        for t in all_tasks:
            if t["status"] == "in_progress":
                in_prog_tech.add(t["technician_id"])
        tech_summary = {
            "total": len(techs),
            "online": online,
            "offline": len(techs) - online,
            "on_task": len(in_prog_tech),
            "not_on_task": len(techs) - len(in_prog_tech),
        }

    # Attendance today
    today_attend = await db.attendance.find({"date": today}, {"_id": 0}).to_list(500)
    checked_in = len({a["user_id"] for a in today_attend if a["type"] == "check_in"})
    checked_out = len({a["user_id"] for a in today_attend if a["type"] == "check_out"})
    attendance_summary = {"checked_in": checked_in, "checked_out": checked_out}

    # Pest findings this month
    month_prefix = datetime.now(timezone.utc).strftime("%Y-%m")
    srs = await db.service_reports.find({"date": {"$regex": f"^{month_prefix}"}}, {"_id": 0}).to_list(500)
    pest_totals = {"F": 0, "M": 0, "C": 0, "R": 0, "A": 0, "O": 0}
    for sr in srs:
        for f in sr.get("pest_findings") or []:
            if f.get("code") in pest_totals:
                pest_totals[f["code"]] += int(f.get("quantity") or 0)

    return {
        "tasks": tasks_summary,
        "technicians": tech_summary,
        "attendance": attendance_summary,
        "pest_findings_month": pest_totals,
    }


# ================= REPORTS =================
@api.get("/reports/attendance")
async def report_attendance(format: str = "excel", date_from: Optional[str] = None,
                            date_to: Optional[str] = None, user_id: Optional[str] = None,
                            user: dict = Depends(get_current_user)):
    require_permission(user, "reports", "export")
    q = {}
    if user_id:
        q["user_id"] = user_id
    if date_from:
        q["date"] = {"$gte": date_from}
    if date_to:
        q.setdefault("date", {})["$lte"] = date_to
    att = await db.attendance.find(q, {"_id": 0}).sort("timestamp", 1).to_list(2000)
    # Pair check-in with check-out
    checkins = {a["id"]: a for a in att if a["type"] == "check_in"}
    rows = []
    for a in att:
        if a["type"] != "check_in":
            continue
        co = next((x for x in att if x.get("checkin_ref") == a["id"]), None)
        wh = ""
        if co:
            try:
                d1 = datetime.fromisoformat(a["timestamp"])
                d2 = datetime.fromisoformat(co["timestamp"])
                wh = f"{(d2 - d1).total_seconds() / 3600:.2f}h"
            except Exception:
                pass
        rows.append([
            a.get("user_name", ""),
            a["date"], a["timestamp"][11:19],
            co["date"] if co else "", (co["timestamp"][11:19] if co else ""),
            wh,
            f'{a.get("latitude", "")},{a.get("longitude", "")}',
        ])
    headers = ["Employee", "Check-in Date", "Check-in Time", "Check-out Date", "Check-out Time", "Working Hours", "Location"]
    if format == "pdf":
        b = generate_simple_pdf("ATTENDANCE REPORT", headers, rows)
        return StreamingResponse(io.BytesIO(b), media_type="application/pdf",
                                 headers={"Content-Disposition": "attachment; filename=attendance.pdf"})
    b = generate_simple_excel("Attendance", headers, rows)
    return StreamingResponse(io.BytesIO(b),
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=attendance.xlsx"})


@api.get("/reports/customers")
async def report_customers(format: str = "excel", user: dict = Depends(get_current_user)):
    require_permission(user, "reports", "export")
    docs = await db.customers.find({}, {"_id": 0}).to_list(2000)
    headers = ["Company", "Contact", "Phone", "Email", "Address", "Category", "Status", "Contract Start", "Contract End"]
    rows = [[d.get("company_name", ""), d.get("contact_person", ""), d.get("phone", ""), d.get("email", ""),
             d.get("address", ""), d.get("category", ""), d.get("status", ""),
             d.get("contract_start") or "", d.get("contract_end") or ""] for d in docs]
    if format == "pdf":
        b = generate_simple_pdf("CUSTOMER REPORT", headers, rows)
        return StreamingResponse(io.BytesIO(b), media_type="application/pdf",
                                 headers={"Content-Disposition": "attachment; filename=customers.pdf"})
    b = generate_simple_excel("Customers", headers, rows)
    return StreamingResponse(io.BytesIO(b),
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=customers.xlsx"})


@api.get("/reports/employees")
async def report_employees(format: str = "excel", user: dict = Depends(get_current_user)):
    require_permission(user, "reports", "export")
    docs = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(2000)
    headers = ["Name", "Username/Email", "Position", "ID Number", "Address", "Join Date", "Status", "Leave Quota", "Remaining"]
    rows = [[d.get("full_name", ""), d.get("email", ""), d.get("position", ""), d.get("id_number", ""),
             d.get("address", ""), d.get("created_at", "")[:10], d.get("status", ""),
             d.get("leave_quota", 0), max(0, d.get("leave_quota", 0) - d.get("leave_used", 0))] for d in docs]
    if format == "pdf":
        b = generate_simple_pdf("EMPLOYEE DATA REPORT", headers, rows)
        return StreamingResponse(io.BytesIO(b), media_type="application/pdf",
                                 headers={"Content-Disposition": "attachment; filename=employees.pdf"})
    b = generate_simple_excel("Employees", headers, rows)
    return StreamingResponse(io.BytesIO(b),
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=employees.xlsx"})


# ================= SETTINGS =================
@api.get("/settings")
async def get_settings(user: dict = Depends(get_current_user)):
    doc = await db.settings.find_one({"_id": "app"}, {"_id": 0}) or {}
    doc.setdefault("company_name", os.environ.get("COMPANY_NAME", "Proteksi Pest Control"))
    doc.setdefault("company_address", os.environ.get("COMPANY_ADDRESS", ""))
    doc.setdefault("company_email", os.environ.get("COMPANY_EMAIL", ""))
    doc.setdefault("geofence_radius", int(os.environ.get("GEOFENCE_RADIUS_METERS", "100")))
    doc.setdefault("gps_interval", int(os.environ.get("GPS_INTERVAL_SECONDS", "4")))
    return doc


@api.put("/settings")
async def update_settings(body: dict = Body(...), user: dict = Depends(get_current_user)):
    require_permission(user, "settings", "manage")
    body["updated_at"] = now_iso()
    await db.settings.update_one({"_id": "app"}, {"$set": body}, upsert=True)
    return await get_settings(user)


# ================= Health =================
@api.get("/health")
async def health():
    try:
        await db.command("ping")
        return {"status": "ok", "db": "up", "timestamp": now_iso()}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}



# ================= SCHEDULES (recurring standby) =================
@api.get("/schedules")
async def list_schedules(customer_id: Optional[str] = None,
                         technician_id: Optional[str] = None,
                         date_from: Optional[str] = None,
                         date_to: Optional[str] = None,
                         user: dict = Depends(get_current_user)):
    require_permission(user, "schedule", "view")
    query = {}
    if user.get("role") == "client":
        if customer_id and customer_id != user.get("customer_id"):
            raise HTTPException(403, "Forbidden")
        query["customer_id"] = user.get("customer_id") or "__none__"
    elif user.get("role") == "technician" and not has_permission(user, "schedule", "manage"):
        query["technician_id"] = user["id"]
        if customer_id:
            query["customer_id"] = customer_id
    else:
        if customer_id:
            query["customer_id"] = customer_id
    if technician_id and user.get("role") != "client":
        query["technician_id"] = technician_id
    if date_from:
        query["date"] = {"$gte": date_from}
    if date_to:
        query.setdefault("date", {})["$lte"] = date_to
    docs = await db.schedules.find(query, {"_id": 0}).sort("date", 1).to_list(2000)
    cust_ids = list({d["customer_id"] for d in docs})
    tech_ids = list({d["technician_id"] for d in docs})
    cmap = {c["id"]: c for c in await db.customers.find({"id": {"$in": cust_ids}}, {"_id": 0}).to_list(500)}
    tmap = {t["id"]: t for t in await db.users.find({"id": {"$in": tech_ids}}, {"_id": 0, "password_hash": 0}).to_list(500)}
    for d in docs:
        d["customer"] = cmap.get(d["customer_id"])
        d["technician"] = tmap.get(d["technician_id"])
    return docs


@api.post("/schedules/mass-create")
async def mass_create_schedules(body: ScheduleMassCreate, user: dict = Depends(get_current_user)):
    require_permission(user, "schedule", "create")
    try:
        sd = datetime.fromisoformat(body.start_date).date()
        ed = datetime.fromisoformat(body.end_date).date()
    except Exception:
        raise HTTPException(400, "Invalid dates")
    if ed < sd:
        raise HTTPException(400, "End date before start date")
    if (ed - sd).days > 366:
        raise HTTPException(400, "Range too large (max 366 days)")
    weekdays = set(body.weekdays or [0, 1, 2, 3, 4, 5])
    created = []
    cur = sd
    while cur <= ed:
        if cur.weekday() in weekdays:
            doc = {
                "id": uid(),
                "customer_id": body.customer_id,
                "technician_id": body.technician_id,
                "date": cur.isoformat(),
                "start_time": body.start_time,
                "end_time": body.end_time,
                "status": "scheduled",
                "notes": body.notes,
                "created_by": user["id"],
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
            created.append(doc)
        cur = cur + timedelta(days=1)
    if created:
        await db.schedules.insert_many(created)
    await audit(user, "CREATE", "schedule", f"mass-{len(created)}", None, {"count": len(created), "customer": body.customer_id, "technician": body.technician_id})
    return {"count": len(created), "schedules": [clean(d) for d in created]}


@api.put("/schedules/{sid}")
async def update_schedule(sid: str, body: ScheduleUpdate, user: dict = Depends(get_current_user)):
    require_permission(user, "schedule", "update")
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    upd["updated_at"] = now_iso()
    await db.schedules.update_one({"id": sid}, {"$set": upd})
    await audit(user, "UPDATE", "schedule", sid, None, upd)
    return await db.schedules.find_one({"id": sid}, {"_id": 0})


@api.delete("/schedules/{sid}")
async def delete_schedule(sid: str, user: dict = Depends(get_current_user)):
    require_permission(user, "schedule", "delete")
    await db.schedules.delete_one({"id": sid})
    await audit(user, "DELETE", "schedule", sid)
    return {"ok": True}


# ================= GEOCODING (Nominatim proxy) =================
@api.get("/geocode/search")
async def geocode_search(q: str, user: dict = Depends(get_current_user)):
    if not q or len(q) < 3:
        return []
    try:
        async with httpx.AsyncClient(timeout=10) as cli:
            r = await cli.get("https://nominatim.openstreetmap.org/search",
                              params={"q": q, "format": "json", "limit": 5, "addressdetails": 1},
                              headers={"User-Agent": "PestOpsPro/1.0"})
            r.raise_for_status()
            data = r.json()
        return [{"display_name": d.get("display_name"),
                 "lat": float(d.get("lat", 0)), "lng": float(d.get("lon", 0))} for d in data]
    except Exception as e:
        logger.warning(f"Geocode failed: {e}")
        return []


@api.get("/geocode/reverse")
async def geocode_reverse_api(lat: float, lon: float, user: dict = Depends(get_current_user)):
    return {"display_name": await reverse_geocode(lat, lon)}


# ================= MONTHLY REPORT =================
@api.get("/monthly-report")
async def monthly_report(customer_id: str, month: str, user: dict = Depends(get_current_user)):
    """month = YYYY-MM. Returns aggregated data + PDF-ready payload."""
    require_permission(user, "monthly_reports", "view")
    if user.get("role") == "client" and user.get("customer_id") != customer_id:
        raise HTTPException(403, "Forbidden")
    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(404, "Customer not found")
    year, mon = month.split("-")
    m_prefix = f"{year}-{mon}"
    # Contract start month for historical pest chart
    contract_start = customer.get("contract_start") or "2026-01-01"
    try:
        cs = datetime.fromisoformat(contract_start).date().replace(day=1)
    except Exception:
        cs = date(2026, 1, 1)
    target = date(int(year), int(mon), 1)

    # Historical pest per-month from contract_start → target
    historical = []
    cur = cs
    while cur <= target:
        prefix = cur.strftime("%Y-%m")
        srs_m = await db.service_reports.find(
            {"customer_id": customer_id, "date": {"$regex": f"^{prefix}"}}, {"_id": 0}
        ).to_list(500)
        totals = {"F": 0, "M": 0, "C": 0, "R": 0, "A": 0, "O": 0}
        for sr in srs_m:
            for f in sr.get("pest_findings") or []:
                if f.get("code") in totals:
                    totals[f["code"]] += int(f.get("quantity") or 0)
        historical.append({"month": prefix, **totals, "total": sum(totals.values())})
        # next month
        y2, m2 = (cur.year + (1 if cur.month == 12 else 0), 1 if cur.month == 12 else cur.month + 1)
        cur = date(y2, m2, 1)

    # Current month reports/attendance/work
    srs = await db.service_reports.find({"customer_id": customer_id, "date": {"$regex": f"^{m_prefix}"}}, {"_id": 0}).sort("date", 1).to_list(500)
    tasks = await db.tasks.find({"customer_id": customer_id, "scheduled_date": {"$regex": f"^{m_prefix}"}}, {"_id": 0}).to_list(500)
    task_ids = [t["id"] for t in tasks]
    attendance = await db.attendance.find({"task_id": {"$in": task_ids}, "type": "check_in"}, {"_id": 0}).sort("timestamp", 1).to_list(500)

    # Enrich SRs with tech names
    tech_ids = list({s["technician_id"] for s in srs})
    tmap = {t["id"]: t for t in await db.users.find({"id": {"$in": tech_ids}}, {"_id": 0, "password_hash": 0}).to_list(500)}
    for s in srs:
        s["technician_name"] = tmap.get(s["technician_id"], {}).get("full_name", "")

    return {
        "customer": customer,
        "month": m_prefix,
        "contract_start": contract_start,
        "historical_pest": historical,
        "service_reports": srs,
        "tasks": tasks,
        "attendance": attendance,
    }


def _generate_monthly_pdf(payload: dict, brand: dict) -> bytes:
    from reportlab.platypus import Image
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(f"<b>{brand.get('company_name','PestOps')}</b>", styles["Title"]))
    story.append(Paragraph(brand.get('company_address', ''), styles["Normal"]))
    story.append(Paragraph(f"<b>MONTHLY REPORT — {payload['month']}</b>", styles["Heading2"]))
    story.append(Spacer(1, 5 * mm))

    c = payload["customer"]
    story.append(Paragraph("<b>CLIENT INFORMATION</b>", styles["Heading4"]))
    ct = Table([["Company", c.get("company_name", "")], ["Project", c.get("project_name", "") or c.get("company_name", "")],
                ["Address", c.get("address", "")], ["Contract Start", c.get("contract_start", "")]],
               colWidths=[35 * mm, 140 * mm])
    ct.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(ct)
    story.append(Spacer(1, 4 * mm))

    # Attendance table
    story.append(Paragraph("<b>EMPLOYEE ATTENDANCE</b>", styles["Heading4"]))
    if payload["attendance"]:
        rows = [["Technician", "Date", "Check-in", "Check-out", "Working Hours"]]
        for a in payload["attendance"]:
            rows.append([a.get("user_name", ""), a.get("date", ""), a.get("timestamp", "")[11:19],
                         (a.get("checkout_timestamp", "") or "")[11:19] if a.get("checkout_timestamp") else "-",
                         str(a.get("working_hours") or "-")])
        t = Table(rows, repeatRows=1)
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                               ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                               ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("FONTSIZE", (0, 0), (-1, -1), 8)]))
        story.append(t)
    else:
        story.append(Paragraph("No attendance records this period.", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    # Work summary from SRs
    story.append(Paragraph("<b>WORK REALIZATION</b>", styles["Heading4"]))
    if payload["service_reports"]:
        rows = [["Date", "Technician", "Scope", "Recommendation"]]
        for s in payload["service_reports"]:
            rows.append([s.get("date", ""), s.get("technician_name", ""),
                         (s.get("scope_of_area", "") or "")[:40],
                         (s.get("recommendation", "") or "")[:60]])
        t = Table(rows, repeatRows=1, colWidths=[22 * mm, 35 * mm, 55 * mm, 63 * mm])
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                               ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                               ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("FONTSIZE", (0, 0), (-1, -1), 8)]))
        story.append(t)
    story.append(Spacer(1, 4 * mm))

    # Pest historical chart (as table since chart is on frontend)
    story.append(Paragraph("<b>PEST FINDINGS — HISTORICAL (contract start → current month)</b>", styles["Heading4"]))
    rows = [["Month", "F", "M", "C", "R", "A", "O", "Total"]]
    for h in payload["historical_pest"]:
        rows.append([h["month"], str(h["F"]), str(h["M"]), str(h["C"]), str(h["R"]), str(h["A"]), str(h["O"]), str(h["total"])])
    t = Table(rows, repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    story.append(t)
    story.append(Spacer(1, 4 * mm))

    # Photo documentation (thumbnails names only for compact PDF)
    all_photos = []
    for s in payload["service_reports"]:
        for p in (s.get("photos") or []):
            if isinstance(p, dict) and p.get("path"):
                all_photos.append(p)
    if all_photos:
        story.append(Paragraph("<b>PHOTO DOCUMENTATION</b>", styles["Heading4"]))
        rows = [["#", "Caption", "Path"]]
        for i, p in enumerate(all_photos, 1):
            rows.append([str(i), (p.get("caption") or "")[:50], p["path"][-40:]])
        t = Table(rows, repeatRows=1, colWidths=[10 * mm, 80 * mm, 85 * mm])
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                               ("FONTSIZE", (0, 0), (-1, -1), 8)]))
        story.append(t)

    doc.build(story)
    return buf.getvalue()


@api.get("/monthly-report/pdf")
async def monthly_report_pdf(customer_id: str, month: str, user: dict = Depends(get_current_user)):
    require_permission(user, "monthly_reports", "export")
    payload = await monthly_report(customer_id=customer_id, month=month, user=user)
    settings = await db.settings.find_one({"_id": "app"}) or {}
    brand = {
        "company_name": settings.get("company_name") or os.environ.get("COMPANY_NAME", "PestOps Pro"),
        "company_address": settings.get("company_address") or os.environ.get("COMPANY_ADDRESS", ""),
    }
    pdf = _generate_monthly_pdf(payload, brand)
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename=monthly-{customer_id[:8]}-{month}.pdf"})


# ================= BULK ZIP EXPORT =================
@api.get("/service-reports/export/zip")
async def sr_bulk_zip(customer_id: Optional[str] = None,
                      date_from: Optional[str] = None,
                      date_to: Optional[str] = None,
                      user: dict = Depends(get_current_user)):
    require_permission(user, "service_reports", "export")
    query = {}
    if user.get("role") == "client":
        query["customer_id"] = user.get("customer_id") or "__none__"
    elif customer_id:
        query["customer_id"] = customer_id
    if date_from:
        query["date"] = {"$gte": date_from}
    if date_to:
        query.setdefault("date", {})["$lte"] = date_to
    srs = await db.service_reports.find(query, {"_id": 0}).to_list(500)
    if not srs:
        raise HTTPException(404, "No reports found")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for sr in srs:
            task = await db.tasks.find_one({"id": sr["task_id"]}, {"_id": 0}) or {}
            cust = await db.customers.find_one({"id": sr["customer_id"]}, {"_id": 0}) or {}
            tech = await db.users.find_one({"id": sr["technician_id"]}, {"_id": 0, "password_hash": 0}) or {}
            pdf = generate_service_report_pdf(sr, task, cust, tech)
            zf.writestr(f"{sr.get('report_number', sr['id'])}.pdf", pdf)
    buf.seek(0)
    return StreamingResponse(io.BytesIO(buf.getvalue()), media_type="application/zip",
                             headers={"Content-Disposition": "attachment; filename=service_reports.zip"})


# ================= EMAIL SEND =================
async def _get_brand():
    s = await db.settings.find_one({"_id": "app"}) or {}
    return {
        "company_name": s.get("company_name") or os.environ.get("COMPANY_NAME", "PestOps Pro"),
        "company_address": s.get("company_address") or os.environ.get("COMPANY_ADDRESS", ""),
    }


@api.post("/service-reports/{sid}/email")
async def email_single_sr(sid: str, body: SendReportEmail, user: dict = Depends(get_current_user)):
    require_permission(user, "email", "create")
    sr = await db.service_reports.find_one({"id": sid}, {"_id": 0})
    if not sr:
        raise HTTPException(404, "Not found")
    cust = await db.customers.find_one({"id": sr["customer_id"]}, {"_id": 0}) or {}
    recipient = body.override_recipient or cust.get("email")
    if not recipient:
        raise HTTPException(400, "No client email available")
    task = await db.tasks.find_one({"id": sr["task_id"]}, {"_id": 0}) or {}
    tech = await db.users.find_one({"id": sr["technician_id"]}, {"_id": 0, "password_hash": 0}) or {}
    pdf = generate_service_report_pdf(sr, task, cust, tech)
    brand = await _get_brand()
    html = render_report_email(
        brand_name=brand["company_name"], brand_address=brand["company_address"],
        recipient_name=cust.get("contact_person") or cust.get("company_name", ""),
        client_name=cust.get("company_name", ""), period=sr.get("date", ""),
        admin_message=body.message, report_kind="Service Report",
    )
    email_id = await send_email_with_attachments(
        to=recipient, subject=body.subject or f"Service Report - {sr.get('report_number','')}",
        html=html, attachments=[{"filename": f"{sr.get('report_number','report')}.pdf", "content": pdf}],
    )
    await audit(user, "EMAIL", "service_reports", sid, None, {"to": recipient, "email_id": email_id})
    return {"ok": True, "email_id": email_id, "recipient": recipient}


@api.post("/monthly-report/email")
async def email_monthly_report(customer_id: str = Body(...), month: str = Body(...),
                               body: SendReportEmail = Body(...), user: dict = Depends(get_current_user)):
    require_permission(user, "email", "create")
    payload = await monthly_report(customer_id=customer_id, month=month, user=user)
    cust = payload["customer"]
    recipient = body.override_recipient or cust.get("email")
    if not recipient:
        raise HTTPException(400, "No client email available")
    brand = await _get_brand()
    pdf = _generate_monthly_pdf(payload, brand)
    html = render_report_email(
        brand_name=brand["company_name"], brand_address=brand["company_address"],
        recipient_name=cust.get("contact_person") or cust.get("company_name", ""),
        client_name=cust.get("company_name", ""), period=month,
        admin_message=body.message, report_kind="Monthly Report",
    )
    email_id = await send_email_with_attachments(
        to=recipient, subject=body.subject or f"Monthly Report - {month}",
        html=html, attachments=[{"filename": f"monthly-{month}.pdf", "content": pdf}],
    )
    await audit(user, "EMAIL", "monthly_reports", f"{customer_id}-{month}", None, {"to": recipient, "email_id": email_id})
    return {"ok": True, "email_id": email_id, "recipient": recipient}


# ================= BRANDING =================
@api.get("/branding")
async def get_branding(user: dict = Depends(get_current_user)):
    s = await db.settings.find_one({"_id": "app"}) or {}
    return {
        "company_name": s.get("company_name") or "PestOps Pro",
        "company_address": s.get("company_address") or "",
        "company_email": s.get("company_email") or "",
        "company_phone": s.get("company_phone") or "",
        "logo_path": s.get("logo_path") or None,
        "app_name": s.get("app_name") or "PestOps Pro",
    }


@api.put("/branding")
async def put_branding(body: dict = Body(...), user: dict = Depends(get_current_user)):
    # Developer or admin
    if user.get("role") not in ("admin", "developer") and not has_permission(user, "branding", "manage"):
        raise HTTPException(403, "Forbidden")
    body["updated_at"] = now_iso()
    await db.settings.update_one({"_id": "app"}, {"$set": body}, upsert=True)
    await audit(user, "UPDATE", "branding", "app", None, body)
    return await get_branding(user)



app.include_router(api)

# CORS - permissive for preview environment, cookies allowed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # using Bearer token from localStorage as primary
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def _sd():
    client.close()
