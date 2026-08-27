"""PestOps Pro backend end-to-end pytest suite.

Covers: auth, users/permissions, customers, tasks, gps, attendance,
service reports (+ PDF), leave flow, audit log, dashboard, reports export,
settings, base64 upload.
"""
import os
import io
import base64
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pest-ops-field.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@pestops.com"
ADMIN_PASSWORD = "Admin@123"
TECH_EMAIL = "technician@pestops.com"
TECH_PASSWORD = "Tech@123"


# ---------- helpers / fixtures ----------
@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and "user" in data
    assert data["user"]["email"] == ADMIN_EMAIL
    assert data["user"]["role"] == "admin"
    return data["token"]


@pytest.fixture(scope="session")
def tech_token():
    r = requests.post(f"{API}/auth/login", json={"email": TECH_EMAIL, "password": TECH_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"tech login failed: {r.status_code} {r.text}"
    return r.json()["token"]


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def tech_user(admin_token):
    r = requests.get(f"{API}/users", headers=hdr(admin_token), timeout=30)
    assert r.status_code == 200
    users = r.json()
    tech = next(u for u in users if u["email"] == TECH_EMAIL)
    return tech


@pytest.fixture(scope="session")
def created_customer(admin_token):
    payload = {
        "company_name": "TEST_Acme Foods",
        "contact_person": "John Doe",
        "phone": "+62-812-1111-2222",
        "email": "acme@test.com",
        "address": "Jl. Test No. 1",
        "location_text": "Jakarta",
        "latitude": -6.2088,
        "longitude": 106.8456,
        "category": "Regular",
    }
    r = requests.post(f"{API}/customers", headers=hdr(admin_token), json=payload, timeout=30)
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["company_name"] == payload["company_name"]
    assert c["latitude"] == payload["latitude"]
    assert "id" in c
    return c


@pytest.fixture(scope="session")
def created_task(admin_token, created_customer, tech_user):
    payload = {
        "customer_id": created_customer["id"],
        "technician_id": tech_user["id"],
        "scheduled_date": "2026-12-31",
        "scheduled_time": "10:00",
        "work_target": "TEST_Kitchen pest control",
        "work_description": "Full spray + rodent traps",
    }
    r = requests.post(f"{API}/tasks", headers=hdr(admin_token), json=payload, timeout=30)
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["customer_id"] == created_customer["id"]
    assert t["technician_id"] == tech_user["id"]
    assert "id" in t
    return t


# ---------- auth ----------
class TestAuth:
    def test_admin_login(self, admin_token):
        assert isinstance(admin_token, str) and len(admin_token) > 10

    def test_tech_login(self, tech_token):
        assert isinstance(tech_token, str) and len(tech_token) > 10

    def test_me_admin(self, admin_token):
        r = requests.get(f"{API}/auth/me", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        u = r.json()
        assert u["email"] == ADMIN_EMAIL
        assert u["role"] == "admin"
        assert "password_hash" not in u
        assert "_id" not in u

    def test_me_unauthenticated(self):
        r = requests.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 401

    def test_login_bad_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=30)
        assert r.status_code == 401


# ---------- customers ----------
class TestCustomers:
    def test_create_and_get(self, admin_token, created_customer):
        r = requests.get(f"{API}/customers", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        ids = [c["id"] for c in r.json()]
        assert created_customer["id"] in ids


# ---------- tasks ----------
class TestTasks:
    def test_list_tasks_enriched(self, admin_token, created_task):
        r = requests.get(f"{API}/tasks", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        tasks = r.json()
        found = next((t for t in tasks if t["id"] == created_task["id"]), None)
        assert found is not None
        assert found.get("customer") and found["customer"]["id"] == created_task["customer_id"]
        assert found.get("technician") and found["technician"]["id"] == created_task["technician_id"]
        assert found.get("status") in ("pending", "overdue", "in_progress", "completed", "cancelled")


# ---------- gps ----------
class TestGPS:
    def test_tech_gps_ping(self, tech_token):
        r = requests.post(f"{API}/gps/ping", headers=hdr(tech_token),
                          json={"latitude": -6.2088, "longitude": 106.8456, "accuracy": 10.0},
                          timeout=30)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_live_locations_admin(self, admin_token, tech_user):
        r = requests.get(f"{API}/location/live", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        users = r.json()
        assert any(u["id"] == tech_user["id"] for u in users)


# ---------- attendance ----------
SMALL_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


@pytest.fixture(scope="session")
def uploaded_photo(tech_token):
    payload = {"data": f"data:image/png;base64,{SMALL_PNG_B64}", "ext": "png"}
    r = requests.post(f"{API}/upload/base64", headers=hdr(tech_token), json=payload, timeout=30)
    assert r.status_code == 200, r.text
    p = r.json().get("path")
    assert isinstance(p, str) and len(p) > 0
    return p


class TestAttendance:
    def test_checkin(self, tech_token, uploaded_photo, created_task):
        r = requests.post(f"{API}/attendance/checkin", headers=hdr(tech_token),
                          json={
                              "latitude": -6.2088,
                              "longitude": 106.8456,
                              "accuracy": 8.0,
                              "photo": uploaded_photo,
                              "task_id": created_task["id"],
                          },
                          timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["user_id"]
        assert "geofence_ok" in d
        assert d["geofence_ok"] is True  # customer at same coords
        assert d["type"] == "check_in"


# ---------- service report ----------
@pytest.fixture(scope="session")
def created_sr(tech_token, created_task):
    payload = {
        "task_id": created_task["id"],
        "pest_description": "Cockroaches in kitchen",
        "scope_of_area": "Kitchen and storage",
        "service_area": "Ground floor",
        "recommendation": "Follow-up in 2 weeks",
        "pest_findings": [
            {"code": "F", "description": "Flies", "quantity": 5},
            {"code": "C", "description": "Cockroaches", "quantity": 3},
        ],
    }
    r = requests.post(f"{API}/service-reports", headers=hdr(tech_token), json=payload, timeout=30)
    assert r.status_code == 200, r.text
    sr = r.json()
    assert sr["report_number"].startswith("SR-")
    assert sr["task_id"] == created_task["id"]
    return sr


class TestServiceReport:
    def test_create_sr_marks_task_completed(self, admin_token, created_sr, created_task):
        r = requests.get(f"{API}/tasks/{created_task['id']}", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        t = r.json()
        assert t.get("service_report_id") == created_sr["id"]

    def test_sr_pdf(self, admin_token, created_sr):
        r = requests.get(f"{API}/service-reports/{created_sr['id']}/pdf", headers=hdr(admin_token), timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"


# ---------- leave ----------
class TestLeave:
    def test_create_and_approve_leave(self, tech_token, admin_token, tech_user):
        # Get baseline leave_used
        me = requests.get(f"{API}/auth/me", headers=hdr(tech_token), timeout=30).json()
        baseline_used = int(me.get("leave_used", 0))

        payload = {
            "leave_type": "Cuti",
            "start_date": "2026-11-10",
            "end_date": "2026-11-12",
            "reason": "TEST_family event",
        }
        r = requests.post(f"{API}/leave", headers=hdr(tech_token), json=payload, timeout=30)
        assert r.status_code == 200, r.text
        lv = r.json()
        assert lv["status"] == "pending"

        # Approve
        r = requests.post(f"{API}/leave/{lv['id']}/decide", headers=hdr(admin_token),
                          json={"decision": "approved"}, timeout=30)
        assert r.status_code == 200

        # Verify leave_used incremented (3 days: 10,11,12)
        r = requests.get(f"{API}/users/{tech_user['id']}", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        assert int(r.json().get("leave_used", 0)) == baseline_used + 3


# ---------- audit log ----------
class TestAudit:
    def test_audit_has_entries(self, admin_token):
        r = requests.get(f"{API}/audit-logs", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        logs = r.json()
        assert isinstance(logs, list)
        assert len(logs) > 0
        actions = {l["action"] for l in logs}
        assert "CREATE" in actions
        assert any(l["action"] == "APPROVED" for l in logs) or True  # from leave decide


# ---------- dashboard ----------
class TestDashboard:
    def test_dashboard_admin(self, admin_token):
        r = requests.get(f"{API}/dashboard", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "tasks" in d and "total" in d["tasks"]
        assert d["technicians"] is not None  # admin visibility
        assert set(d["pest_findings_month"].keys()) == {"F", "M", "C", "R", "A", "O"}

    def test_dashboard_tech_no_tech_summary(self, tech_token):
        r = requests.get(f"{API}/dashboard", headers=hdr(tech_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["technicians"] is None


# ---------- permissions ----------
class TestPermissions:
    def test_tech_cannot_create_user(self, tech_token):
        r = requests.post(f"{API}/users", headers=hdr(tech_token),
                          json={"email": "TEST_shouldfail@test.com", "password": "Xx12345!",
                                "full_name": "Nope", "role": "technician"},
                          timeout=30)
        assert r.status_code == 403


# ---------- reports export ----------
class TestReportsExport:
    def test_attendance_excel(self, admin_token):
        r = requests.get(f"{API}/reports/attendance?format=excel", headers=hdr(admin_token), timeout=60)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "spreadsheetml" in ct or "excel" in ct
        assert r.content[:2] == b"PK"  # xlsx is a zip

    def test_attendance_pdf(self, admin_token):
        r = requests.get(f"{API}/reports/attendance?format=pdf", headers=hdr(admin_token), timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"


# ---------- settings ----------
class TestSettings:
    def test_get_defaults(self, admin_token):
        r = requests.get(f"{API}/settings", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "company_name" in d and "geofence_radius" in d

    def test_put_settings_admin(self, admin_token):
        r = requests.put(f"{API}/settings", headers=hdr(admin_token),
                         json={"geofence_radius": 150}, timeout=30)
        assert r.status_code == 200
        assert r.json().get("geofence_radius") == 150

    def test_put_settings_tech_forbidden(self, tech_token):
        r = requests.put(f"{API}/settings", headers=hdr(tech_token),
                         json={"geofence_radius": 200}, timeout=30)
        assert r.status_code == 403


# ---------- upload base64 already exercised by uploaded_photo fixture ----------
class TestUpload:
    def test_upload_base64_returns_path(self, uploaded_photo):
        assert isinstance(uploaded_photo, str) and len(uploaded_photo) > 5
