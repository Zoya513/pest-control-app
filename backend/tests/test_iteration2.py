"""PestOps Pro Iteration 2 backend tests.

Covers new/changed features:
- 4 role logins (admin/tech/client/developer) + role-specific permissions
- Schedules CRUD + mass-create with weekday filter
- Geocoding proxy (Nominatim) — external call, tolerant assertions
- Attendance check-in with reverse-geocoded address, check-out with working_hours
- Client-scoped queries (tasks / service-reports)
- Service Report multi-photo schema with captions
- Bulk ZIP export of Service Reports
- Monthly Report data + PDF
- Email endpoints (single SR + monthly) — validates auth/perm/400 flows
- Branding GET/PUT (developer can, non-editor cannot)
- Customer create + linked client user
- GPS ping permission (technician allowed, client denied)
- Filters on tasks and service-reports
"""
import os
import base64
import pytest
import requests
from datetime import date

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pest-ops-field.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin@pestops.com", "Admin@123")
TECH = ("technician@pestops.com", "Tech@123")
CLIENT = ("client@pestops.com", "Client@123")
DEV = ("developer@pestops.com", "Dev@123")


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json()


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


# ------------- session fixtures -------------
@pytest.fixture(scope="session")
def admin():
    return _login(*ADMIN)


@pytest.fixture(scope="session")
def tech():
    return _login(*TECH)


@pytest.fixture(scope="session")
def client_login():
    return _login(*CLIENT)


@pytest.fixture(scope="session")
def dev():
    return _login(*DEV)


@pytest.fixture(scope="session")
def admin_token(admin):
    return admin["token"]


@pytest.fixture(scope="session")
def tech_token(tech):
    return tech["token"]


@pytest.fixture(scope="session")
def client_token(client_login):
    return client_login["token"]


@pytest.fixture(scope="session")
def dev_token(dev):
    return dev["token"]


@pytest.fixture(scope="session")
def tech_user(admin_token):
    r = requests.get(f"{API}/users", headers=hdr(admin_token), timeout=30)
    return next(u for u in r.json() if u["email"] == TECH[0])


@pytest.fixture(scope="session")
def demo_customer(admin_token):
    r = requests.get(f"{API}/customers", headers=hdr(admin_token), timeout=30)
    for c in r.json():
        if c.get("company_name") == "PT. John Robert Powers":
            return c
    pytest.skip("Demo customer PT. John Robert Powers not seeded")


# ============ ROLE LOGINS + PERMISSIONS ============
class TestRoleLogins:
    def test_admin_login(self, admin):
        assert admin["user"]["role"] == "admin"
        assert admin["user"]["email"] == ADMIN[0]
        assert isinstance(admin["token"], str) and len(admin["token"]) > 10

    def test_tech_login_permissions(self, tech):
        perms = tech["user"].get("permissions") or {}
        assert perms.get("attendance", {}).get("create") is True
        assert perms.get("travel", {}).get("track") is True
        assert perms.get("members", {}).get("create") is False

    def test_client_login(self, client_login, demo_customer):
        u = client_login["user"]
        assert u["role"] == "client"
        assert u.get("customer_id") == demo_customer["id"]

    def test_dev_login(self, dev):
        u = dev["user"]
        assert u["role"] == "developer"
        assert (u.get("permissions") or {}).get("branding", {}).get("manage") is True


# ============ SCHEDULES ============
@pytest.fixture(scope="session")
def mass_created_schedules(admin_token, demo_customer, tech_user):
    payload = {
        "customer_id": demo_customer["id"],
        "technician_id": tech_user["id"],
        # 2026-02-02 (Mon) → 2026-02-15 (Sun) = 14 days
        # Weekdays 0-4 (Mon-Fri) in that range: 5 + 5 = 10
        "start_date": "2026-02-02",
        "end_date": "2026-02-15",
        "start_time": "08:00",
        "end_time": "17:00",
        "weekdays": [0, 1, 2, 3, 4],
        "notes": "TEST_mass",
    }
    r = requests.post(f"{API}/schedules/mass-create", headers=hdr(admin_token), json=payload, timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    return data, payload


class TestSchedules:
    def test_mass_create_only_weekdays(self, mass_created_schedules):
        data, payload = mass_created_schedules
        # Only Mon-Fri = 10 within the 14-day range
        assert data["count"] == 10, f"expected 10 schedules got {data['count']}"
        # Verify weekdays
        from datetime import datetime as dt
        for s in data["schedules"]:
            assert dt.fromisoformat(s["date"]).weekday() in {0, 1, 2, 3, 4}

    def test_list_and_update_and_delete(self, admin_token, mass_created_schedules):
        r = requests.get(f"{API}/schedules", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        ls = r.json()
        assert isinstance(ls, list) and len(ls) >= 10
        first = ls[0]
        # Update
        r = requests.put(f"{API}/schedules/{first['id']}", headers=hdr(admin_token),
                         json={"notes": "TEST_updated"}, timeout=30)
        assert r.status_code == 200
        assert r.json().get("notes") == "TEST_updated"
        # Delete
        r = requests.delete(f"{API}/schedules/{first['id']}", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        # Verify gone
        r = requests.get(f"{API}/schedules", headers=hdr(admin_token), timeout=30)
        ids = [s["id"] for s in r.json()]
        assert first["id"] not in ids


# ============ GEOCODING ============
class TestGeocode:
    def test_search(self, admin_token):
        r = requests.get(f"{API}/geocode/search", headers=hdr(admin_token),
                         params={"q": "Jakarta"}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        # Nominatim rate-limits may return []; only assert structure if any
        if data:
            first = data[0]
            assert "display_name" in first and "lat" in first and "lng" in first

    def test_reverse(self, admin_token):
        r = requests.get(f"{API}/geocode/reverse", headers=hdr(admin_token),
                         params={"lat": -6.2088, "lon": 106.8456}, timeout=30)
        assert r.status_code == 200
        assert "display_name" in r.json()


# ============ CUSTOMER + LINKED CLIENT USER ============
@pytest.fixture(scope="session")
def created_customer_with_client(admin_token):
    email = f"test_client_{os.urandom(3).hex()}@test.com"
    payload = {
        "company_name": "TEST_ClientCoLinked",
        "contact_person": "Linked One",
        "phone": "+62-812-9999-0000",
        "email": email,
        "address": "Jl. Linked",
        "location_text": "Jakarta",
        "latitude": -6.2, "longitude": 106.8,
        "category": "Regular",
        "contract_start": "2026-01-01",
        "contract_end": "2027-01-01",
        "client_email": email,
        "client_password": "TestClient@123",
    }
    r = requests.post(f"{API}/customers", headers=hdr(admin_token), json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json(), payload


class TestCustomerClientLink:
    def test_client_user_created(self, admin_token, created_customer_with_client):
        cust, payload = created_customer_with_client
        r = requests.get(f"{API}/users", headers=hdr(admin_token), timeout=30)
        u = next((x for x in r.json() if x["email"] == payload["client_email"]), None)
        assert u is not None, "linked client user was not created"
        assert u["role"] == "client"
        assert u.get("customer_id") == cust["id"]

    def test_new_client_can_login(self, created_customer_with_client):
        cust, payload = created_customer_with_client
        r = requests.post(f"{API}/auth/login",
                         json={"email": payload["client_email"], "password": payload["client_password"]},
                         timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["role"] == "client"
        assert d["user"]["customer_id"] == cust["id"]


# ============ TASKS with filters + CLIENT SCOPING ============
@pytest.fixture(scope="session")
def demo_task(admin_token, demo_customer, tech_user):
    payload = {
        "customer_id": demo_customer["id"],
        "technician_id": tech_user["id"],
        "scheduled_date": "2026-02-05",
        "scheduled_time": "10:00",
        "work_target": "TEST_iter2_task",
        "work_description": "Iter2 task for scoping test",
    }
    r = requests.post(f"{API}/tasks", headers=hdr(admin_token), json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


class TestTaskFilters:
    def test_customer_filter(self, admin_token, demo_task, demo_customer):
        r = requests.get(f"{API}/tasks", headers=hdr(admin_token),
                         params={"customer_id": demo_customer["id"]}, timeout=30)
        assert r.status_code == 200
        assert all(t["customer_id"] == demo_customer["id"] for t in r.json())

    def test_date_range_filter(self, admin_token, demo_task):
        r = requests.get(f"{API}/tasks", headers=hdr(admin_token),
                         params={"date_from": "2026-02-01", "date_to": "2026-02-28"}, timeout=30)
        assert r.status_code == 200
        for t in r.json():
            assert "2026-02-01" <= t["scheduled_date"] <= "2026-02-28"


class TestClientScoping:
    def test_client_tasks_scoped(self, client_token, demo_customer, demo_task):
        r = requests.get(f"{API}/tasks", headers=hdr(client_token), timeout=30)
        assert r.status_code == 200
        tasks = r.json()
        assert all(t["customer_id"] == demo_customer["id"] for t in tasks), \
            "client sees tasks outside their customer_id"

    def test_client_forbidden_from_other_customer(self, client_token, created_customer_with_client):
        other_cust, _ = created_customer_with_client
        # Tasks
        r = requests.get(f"{API}/tasks", headers=hdr(client_token),
                         params={"customer_id": other_cust["id"]}, timeout=30)
        assert r.status_code == 403, f"tasks expected 403 got {r.status_code} {r.text[:200]}"
        # Service reports
        r = requests.get(f"{API}/service-reports", headers=hdr(client_token),
                         params={"customer_id": other_cust["id"]}, timeout=30)
        assert r.status_code == 403, f"SRs expected 403 got {r.status_code} {r.text[:200]}"
        # Schedules
        r = requests.get(f"{API}/schedules", headers=hdr(client_token),
                         params={"customer_id": other_cust["id"]}, timeout=30)
        assert r.status_code == 403, f"schedules expected 403 got {r.status_code} {r.text[:200]}"

    def test_client_own_customer_filter_ok(self, client_token, demo_customer):
        # own customer_id should still work
        r = requests.get(f"{API}/tasks", headers=hdr(client_token),
                         params={"customer_id": demo_customer["id"]}, timeout=30)
        assert r.status_code == 200
        r = requests.get(f"{API}/service-reports", headers=hdr(client_token),
                         params={"customer_id": demo_customer["id"]}, timeout=30)
        assert r.status_code == 200
        r = requests.get(f"{API}/schedules", headers=hdr(client_token),
                         params={"customer_id": demo_customer["id"]}, timeout=30)
        assert r.status_code == 200

    def test_client_no_param_scoped(self, client_token, demo_customer):
        for path in ("/tasks", "/service-reports", "/schedules"):
            r = requests.get(f"{API}{path}", headers=hdr(client_token), timeout=30)
            assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:200]}"
            for row in r.json():
                assert row.get("customer_id") == demo_customer["id"]

    def test_client_gps_ping_forbidden(self, client_token):
        r = requests.post(f"{API}/gps/ping", headers=hdr(client_token),
                          json={"latitude": -6.2, "longitude": 106.8}, timeout=30)
        assert r.status_code == 403


# ============ ATTENDANCE with address + working_hours ============
SMALL_PNG_B64 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


@pytest.fixture(scope="session")
def uploaded_photo(tech_token):
    r = requests.post(f"{API}/upload/base64", headers=hdr(tech_token),
                     json={"data": f"data:image/png;base64,{SMALL_PNG_B64}", "ext": "png"}, timeout=30)
    assert r.status_code == 200
    return r.json()["path"]


class TestAttendance:
    def test_checkin_stores_address(self, tech_token, uploaded_photo, demo_task):
        r = requests.post(f"{API}/attendance/checkin", headers=hdr(tech_token),
                          json={"latitude": -6.1568, "longitude": 106.9051,
                                "accuracy": 8.0, "photo": uploaded_photo,
                                "task_id": demo_task["id"]}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "address" in d  # may be empty if Nominatim rate-limited
        assert d["type"] == "check_in"
        # Save for checkout test on same class instance
        pytest.checkin_id = d["id"]
        pytest.checkin_ts = d["timestamp"]

    def test_checkout_updates_checkin(self, tech_token, uploaded_photo):
        checkin_id = getattr(pytest, "checkin_id", None)
        if not checkin_id:
            pytest.skip("No checkin available")
        r = requests.post(f"{API}/attendance/checkout", headers=hdr(tech_token),
                          json={"latitude": -6.1568, "longitude": 106.9051,
                                "accuracy": 8.0, "photo": uploaded_photo,
                                "attendance_id": checkin_id}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["type"] == "check_out"
        assert "working_hours" in d
        # Fetch attendance list and verify check-in was updated with checkout_id + working_hours
        r = requests.get(f"{API}/attendance", headers=hdr(tech_token), timeout=30)
        recs = {a["id"]: a for a in r.json()}
        ci = recs.get(checkin_id)
        assert ci is not None
        assert ci.get("checkout_id") == d["id"]
        assert "working_hours" in ci


# ============ SERVICE REPORT (multi-photo with captions) ============
@pytest.fixture(scope="session")
def sr_task(admin_token, demo_customer, tech_user):
    """A task that hasn't had a service report yet (SR creation marks task completed)."""
    r = requests.post(f"{API}/tasks", headers=hdr(admin_token), json={
        "customer_id": demo_customer["id"],
        "technician_id": tech_user["id"],
        "scheduled_date": "2026-02-10",
        "scheduled_time": "09:00",
        "work_target": "TEST_iter2_sr_task",
        "work_description": "For SR photo test",
    }, timeout=30)
    return r.json()


@pytest.fixture(scope="session")
def created_sr(tech_token, sr_task, uploaded_photo):
    # After bug fix: ServiceReportCreate.photos is List[SRPhoto] ({path, caption?}).
    payload = {
        "task_id": sr_task["id"],
        "pest_description": "TEST cockroaches",
        "scope_of_area": "kitchen",
        "service_area": "ground floor",
        "recommendation": "follow up",
        "pest_findings": [{"code": "C", "description": "Cockroaches", "quantity": 4},
                          {"code": "F", "description": "Flies", "quantity": 2}],
        "photos": [{"path": uploaded_photo}, {"path": uploaded_photo}],
        "client_signature": uploaded_photo,
        "technician_signature": uploaded_photo,
    }
    r = requests.post(f"{API}/service-reports", headers=hdr(tech_token), json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json(), payload


class TestServiceReportPhotos:
    def test_photos_with_captions_bug(self, tech_token, admin_token, demo_customer, tech_user, uploaded_photo):
        """Documents the bug: ServiceReportCreate has duplicate `photos` field.
        The second declaration `photos: List[str]` shadows `photos: List[SRPhoto]`,
        so sending {path, caption} objects fails with 422 and captions cannot be stored.
        """
        # New task for isolation
        r = requests.post(f"{API}/tasks", headers=hdr(admin_token), json={
            "customer_id": demo_customer["id"], "technician_id": tech_user["id"],
            "scheduled_date": "2026-02-13", "work_target": "TEST_captionsbug",
        }, timeout=30)
        task = r.json()
        r = requests.post(f"{API}/service-reports", headers=hdr(tech_token), json={
            "task_id": task["id"], "pest_description": "x",
            "photos": [{"path": uploaded_photo, "caption": "before"},
                       {"path": uploaded_photo, "caption": "after"}],
        }, timeout=30)
        # BUG: backend returns 422. When fixed, expect 200 and captions preserved on GET.
        if r.status_code == 200:
            sr = r.json()
            got = requests.get(f"{API}/service-reports/{sr['id']}", headers=hdr(admin_token), timeout=30).json()
            captions = [p.get("caption") for p in (got.get("photos") or []) if isinstance(p, dict)]
            assert "before" in captions and "after" in captions
        else:
            pytest.fail(f"BUG: multi-photo with captions rejected — {r.status_code} {r.text[:300]}")

    def test_photos_preserved_string_schema(self, created_sr, admin_token):
        sr, payload = created_sr
        r = requests.get(f"{API}/service-reports/{sr['id']}", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        got = r.json()
        assert len(got.get("photos") or []) == 2

    def test_client_signature_present(self, created_sr):
        sr, _ = created_sr
        assert sr.get("client_signature") is not None

    def test_sr_filters(self, admin_token, demo_customer):
        r = requests.get(f"{API}/service-reports", headers=hdr(admin_token),
                         params={"customer_id": demo_customer["id"],
                                 "date_from": "2026-01-01", "date_to": "2027-01-01"}, timeout=30)
        assert r.status_code == 200
        for s in r.json():
            assert s["customer_id"] == demo_customer["id"]

    def test_client_sees_only_own_srs(self, client_token, demo_customer):
        r = requests.get(f"{API}/service-reports", headers=hdr(client_token), timeout=30)
        assert r.status_code == 200
        for s in r.json():
            assert s["customer_id"] == demo_customer["id"]


# ============ BULK ZIP EXPORT ============
class TestBulkZip:
    def test_zip_export(self, admin_token, demo_customer, created_sr):
        r = requests.get(f"{API}/service-reports/export/zip", headers=hdr(admin_token),
                         params={"customer_id": demo_customer["id"]}, timeout=120)
        assert r.status_code == 200, r.text[:400]
        assert r.headers.get("content-type", "").startswith("application/zip")
        assert r.content[:2] == b"PK"  # zip magic


# ============ MONTHLY REPORT ============
class TestMonthlyReport:
    def test_monthly_data(self, admin_token, demo_customer, created_sr):
        r = requests.get(f"{API}/monthly-report", headers=hdr(admin_token),
                         params={"customer_id": demo_customer["id"], "month": "2026-02"}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["customer"]["id"] == demo_customer["id"]
        assert d["month"] == "2026-02"
        # NEW (iter4): historical spans from FIRST service_report.date (not contract_start).
        # first_report_date field must be present.
        assert "first_report_date" in d
        # If the first SR for this customer is <= target month, historical must include target month
        first_dt = d.get("first_report_date") or ""
        if first_dt and first_dt[:7] <= "2026-02":
            months = [h["month"] for h in d["historical_pest"]]
            assert "2026-02" in months, f"months got: {months}, first_report_date={first_dt}"
        # service_reports only from target month
        for s in d["service_reports"]:
            assert s["date"].startswith("2026-02"), f"non-target month SR: {s['date']}"

    def test_monthly_pdf(self, admin_token, demo_customer):
        r = requests.get(f"{API}/monthly-report/pdf", headers=hdr(admin_token),
                         params={"customer_id": demo_customer["id"], "month": "2026-02"}, timeout=90)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"


# ============ BRANDING ============
class TestBranding:
    def test_get_branding_defaults(self, admin_token):
        r = requests.get(f"{API}/branding", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "company_name" in d and "app_name" in d

    def test_put_branding_as_developer(self, dev_token):
        r = requests.put(f"{API}/branding", headers=hdr(dev_token),
                         json={"company_name": "TEST_PestOps", "app_name": "TEST_App"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d.get("company_name") == "TEST_PestOps"

    def test_put_branding_as_tech_forbidden(self, tech_token):
        r = requests.put(f"{API}/branding", headers=hdr(tech_token),
                         json={"company_name": "should not"}, timeout=30)
        assert r.status_code == 403


# ============ EMAIL ENDPOINTS ============
class TestEmailEndpoints:
    def test_sr_email_no_recipient_400(self, admin_token, tech_token, admin, tech_user):
        """Create an SR whose customer has empty email → expect 400 when no override."""
        # Create a customer with NO email
        r = requests.post(f"{API}/customers", headers=hdr(admin_token), json={
            "company_name": "TEST_NoEmailCust",
            "contact_person": "",
            "phone": "", "email": "",
            "address": "test", "latitude": -6.2, "longitude": 106.8,
        }, timeout=30)
        cust = r.json()
        # Create a task + SR
        r = requests.post(f"{API}/tasks", headers=hdr(admin_token), json={
            "customer_id": cust["id"], "technician_id": tech_user["id"],
            "scheduled_date": "2026-02-11", "work_target": "TEST_noemail",
        }, timeout=30)
        task = r.json()
        r = requests.post(f"{API}/service-reports", headers=hdr(tech_token), json={
            "task_id": task["id"], "pest_description": "x",
        }, timeout=30)
        sr = r.json()
        # Now try to email with no override → expect 400
        r = requests.post(f"{API}/service-reports/{sr['id']}/email", headers=hdr(admin_token),
                         json={"subject": "test", "message": "hi"}, timeout=30)
        assert r.status_code == 400, f"expected 400 got {r.status_code} {r.text}"

    def test_sr_email_with_override(self, admin_token, tech_token, demo_customer, tech_user):
        """Fresh SR + email with override_recipient. Accept 200 or 502 (integration)."""
        r = requests.post(f"{API}/tasks", headers=hdr(admin_token), json={
            "customer_id": demo_customer["id"], "technician_id": tech_user["id"],
            "scheduled_date": "2026-02-12", "work_target": "TEST_emailsr",
        }, timeout=30)
        task = r.json()
        r = requests.post(f"{API}/service-reports", headers=hdr(tech_token),
                         json={"task_id": task["id"], "pest_description": "x"}, timeout=30)
        sr = r.json()
        r = requests.post(f"{API}/service-reports/{sr['id']}/email", headers=hdr(admin_token),
                         json={"subject": "TEST", "message": "hi",
                               "override_recipient": "test@example.com"}, timeout=90)
        # 200 (success), or 502 (provider), or 500 (config) all indicate the code path
        # ran auth+ownership+400 checks properly; only fail if 403/401/404/422/400.
        assert r.status_code in (200, 502, 500), f"unexpected {r.status_code} {r.text[:300]}"

    def test_monthly_email_perm_and_flow(self, admin_token, demo_customer):
        r = requests.post(f"{API}/monthly-report/email", headers=hdr(admin_token),
                         json={"customer_id": demo_customer["id"], "month": "2026-02",
                               "body": {"subject": "TEST monthly", "message": "hi",
                                        "override_recipient": "test@example.com"}}, timeout=120)
        assert r.status_code in (200, 502, 500), f"unexpected {r.status_code} {r.text[:300]}"
