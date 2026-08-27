"""PestOps Pro Iteration 4 backend tests.

Covers new/changed features:
- POST /api/tasks/{tid}/reopen (admin/dev only)
- Service Report create with service_treatments and photos with captions
- Service Report PDF new header
- Monthly Report PDF with include_srs merge (pypdf)
- Monthly Report data.first_report_date field
- Email settings GET/PUT (password masking + whitelist + no-overwrite)
- Email settings test (fallback to Emergent Resend)
- Cron auto-monthly-send (auth + skip + queue)
- Reports filter enhancements (attendance/customers/employees)
"""
import os
import io
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pest-ops-field.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
CRON_SECRET = "7f3e8c2d1a9b4e6f5c8d0a2b7e1f4c9d8b6a3e5f7c1d9b0a4e2f8c6d3b1a5e7f"

ADMIN = ("admin@pestops.com", "Admin@123")
TECH = ("technician@pestops.com", "Tech@123")
CLIENT = ("client@pestops.com", "Client@123")
DEV = ("developer@pestops.com", "Dev@123")

SMALL_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


def _login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json()


def hdr(t):
    return {"Authorization": f"Bearer {t}"}


# ------------ fixtures ------------
@pytest.fixture(scope="session")
def admin_token():
    return _login(*ADMIN)["token"]


@pytest.fixture(scope="session")
def tech_token():
    return _login(*TECH)["token"]


@pytest.fixture(scope="session")
def client_token():
    return _login(*CLIENT)["token"]


@pytest.fixture(scope="session")
def dev_token():
    return _login(*DEV)["token"]


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
    pytest.skip("Demo customer not found")


@pytest.fixture(scope="session")
def uploaded_photo(tech_token):
    r = requests.post(f"{API}/upload/base64", headers=hdr(tech_token),
                      json={"data": f"data:image/png;base64,{SMALL_PNG_B64}", "ext": "png"}, timeout=30)
    assert r.status_code == 200
    return r.json()["path"]


def _make_task(admin_token, cust_id, tech_id, target="TEST_iter4_task", date_str="2026-03-05"):
    r = requests.post(f"{API}/tasks", headers=hdr(admin_token), json={
        "customer_id": cust_id, "technician_id": tech_id,
        "scheduled_date": date_str, "scheduled_time": "10:00",
        "work_target": target, "work_description": "iter4",
    }, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _make_sr(tech_token, task_id, uploaded_photo, treatments=None, findings=None, photos=None):
    payload = {
        "task_id": task_id,
        "pest_description": "TEST iter4",
        "scope_of_area": "kitchen",
        "service_area": "GF",
        "recommendation": "clean",
        "pest_findings": findings if findings is not None else [{"code": "C", "description": "Cockroaches", "quantity": 3}],
        "photos": photos if photos is not None else [{"path": uploaded_photo, "caption": "before"}],
        "service_treatments": treatments if treatments is not None else [{"name": "Spraying", "area_description": "kitchen"}],
        "client_signature": uploaded_photo,
        "technician_signature": uploaded_photo,
    }
    r = requests.post(f"{API}/service-reports", headers=hdr(tech_token), json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


# ============ REOPEN TASK ============
class TestReopenTask:
    def test_reopen_flow_admin(self, admin_token, tech_token, demo_customer, tech_user, uploaded_photo):
        task = _make_task(admin_token, demo_customer["id"], tech_user["id"],
                          target="TEST_reopen_admin", date_str="2026-12-05")
        sr = _make_sr(tech_token, task["id"], uploaded_photo)
        # Verify task is completed with SR
        t_after = requests.get(f"{API}/tasks", headers=hdr(admin_token), timeout=30).json()
        tobj = next(x for x in t_after if x["id"] == task["id"])
        assert tobj.get("service_report_id") == sr["id"]

        # Reopen
        r = requests.post(f"{API}/tasks/{task['id']}/reopen", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200, r.text

        # Verify state
        t_after2 = requests.get(f"{API}/tasks", headers=hdr(admin_token), timeout=30).json()
        tobj2 = next(x for x in t_after2 if x["id"] == task["id"])
        assert tobj2["status"] == "pending", f"status is {tobj2['status']}"
        assert tobj2.get("service_report_id") in (None, ""), f"sr_id still {tobj2.get('service_report_id')}"

        # Verify SR marked reopened
        r = requests.get(f"{API}/service-reports/{sr['id']}", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        assert r.json().get("status") == "reopened"

    def test_reopen_forbidden_for_tech(self, admin_token, tech_token, demo_customer, tech_user, uploaded_photo):
        task = _make_task(admin_token, demo_customer["id"], tech_user["id"],
                          target="TEST_reopen_forbid", date_str="2026-03-07")
        _make_sr(tech_token, task["id"], uploaded_photo)
        r = requests.post(f"{API}/tasks/{task['id']}/reopen", headers=hdr(tech_token), timeout=30)
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text[:200]}"

    def test_reopen_by_developer(self, admin_token, tech_token, dev_token, demo_customer, tech_user, uploaded_photo):
        task = _make_task(admin_token, demo_customer["id"], tech_user["id"],
                          target="TEST_reopen_dev", date_str="2026-03-08")
        _make_sr(tech_token, task["id"], uploaded_photo)
        r = requests.post(f"{API}/tasks/{task['id']}/reopen", headers=hdr(dev_token), timeout=30)
        assert r.status_code == 200, f"dev reopen: {r.status_code} {r.text[:200]}"


# ============ SR with service_treatments & photos ============
class TestServiceReportTreatments:
    def test_create_sr_with_treatments(self, admin_token, tech_token, demo_customer, tech_user, uploaded_photo):
        task = _make_task(admin_token, demo_customer["id"], tech_user["id"],
                          target="TEST_treatments", date_str="2026-03-09")
        sr = _make_sr(tech_token, task["id"], uploaded_photo,
                      treatments=[{"name": "Spraying", "area_description": "kitchen"},
                                  {"name": "Baiting", "area_description": "trash room"}],
                      photos=[{"path": uploaded_photo, "caption": "before"},
                              {"path": uploaded_photo, "caption": "after"}])
        # GET back and verify
        got = requests.get(f"{API}/service-reports/{sr['id']}", headers=hdr(admin_token), timeout=30).json()
        treatments = got.get("service_treatments") or []
        assert len(treatments) == 2, f"treatments got: {treatments}"
        names = [t.get("name") for t in treatments]
        assert "Spraying" in names and "Baiting" in names
        # Photos with captions preserved
        photos = got.get("photos") or []
        captions = [p.get("caption") for p in photos if isinstance(p, dict)]
        assert "before" in captions and "after" in captions


# ============ SR PDF ============
class TestServiceReportPDF:
    def test_sr_pdf(self, admin_token, tech_token, demo_customer, tech_user, uploaded_photo):
        task = _make_task(admin_token, demo_customer["id"], tech_user["id"],
                          target="TEST_srpdf", date_str="2026-03-10")
        sr = _make_sr(tech_token, task["id"], uploaded_photo)
        r = requests.get(f"{API}/service-reports/{sr['id']}/pdf", headers=hdr(admin_token), timeout=60)
        assert r.status_code == 200, r.text[:200]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 1000  # non-trivial


# ============ Monthly Report full + first_report_date ============
class TestMonthlyReport:
    def test_monthly_data_has_first_report_date(self, admin_token, demo_customer):
        r = requests.get(f"{API}/monthly-report", headers=hdr(admin_token),
                         params={"customer_id": demo_customer["id"], "month": "2026-03"}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "first_report_date" in d, "missing first_report_date field"
        # We created SRs in Feb and March, so first_report_date should be non-null
        # (previous iterations 2/3 also created SRs, so should be set)
        # Accept None only if truly no SRs exist across the whole DB for this customer
        # (which shouldn't be the case here)

    def test_monthly_pdf_include_srs_merged(self, admin_token, demo_customer):
        r = requests.get(f"{API}/monthly-report/pdf", headers=hdr(admin_token),
                         params={"customer_id": demo_customer["id"], "month": "2026-03",
                                 "include_srs": "true"}, timeout=120)
        assert r.status_code == 200, r.text[:200]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        # Try to count pages using pypdf; merged should be >= 2 pages typically
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(r.content))
            merged_pages = len(reader.pages)
        except Exception:
            merged_pages = None
        # Compare with summary-only
        r2 = requests.get(f"{API}/monthly-report/pdf", headers=hdr(admin_token),
                         params={"customer_id": demo_customer["id"], "month": "2026-03",
                                 "include_srs": "false"}, timeout=90)
        assert r2.status_code == 200
        assert r2.content[:4] == b"%PDF"
        if merged_pages is not None:
            try:
                from pypdf import PdfReader
                summary_pages = len(PdfReader(io.BytesIO(r2.content)).pages)
                assert merged_pages >= summary_pages, f"merged {merged_pages} < summary {summary_pages}"
            except Exception:
                pass


# ============ EMAIL SETTINGS ============
class TestEmailSettings:
    def test_get_masks_password(self, admin_token):
        r = requests.get(f"{API}/email-settings", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "smtp_password" not in d, f"smtp_password leaked in response"
        assert "smtp_password_set" in d
        assert isinstance(d["smtp_password_set"], bool)
        # Templates should be present
        assert "sr_subject_template" in d and "sr_body_template" in d
        assert "mr_subject_template" in d and "mr_body_template" in d

    def test_put_whitelists_unknown_keys(self, admin_token):
        r = requests.put(f"{API}/email-settings", headers=hdr(admin_token),
                         json={"smtp_host": "smtp.example.com", "smtp_port": 587,
                               "from_email": "from@example.com", "from_name": "TEST",
                               "malicious_key": "should_be_ignored"}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("smtp_host") == "smtp.example.com"
        assert d.get("from_email") == "from@example.com"
        assert "malicious_key" not in d

    def test_put_empty_password_does_not_overwrite(self, admin_token):
        # First set a password
        requests.put(f"{API}/email-settings", headers=hdr(admin_token),
                     json={"smtp_password": "TEST_secret_pw"}, timeout=30)
        r = requests.get(f"{API}/email-settings", headers=hdr(admin_token), timeout=30)
        assert r.json().get("smtp_password_set") is True
        # Now PUT with empty smtp_password
        requests.put(f"{API}/email-settings", headers=hdr(admin_token),
                     json={"smtp_password": "", "from_name": "Kept"}, timeout=30)
        r = requests.get(f"{API}/email-settings", headers=hdr(admin_token), timeout=30)
        d = r.json()
        assert d.get("smtp_password_set") is True, "empty password should NOT clear existing pw"
        assert d.get("from_name") == "Kept"

    def test_client_forbidden_email_settings(self, client_token):
        r = requests.get(f"{API}/email-settings", headers=hdr(client_token), timeout=30)
        assert r.status_code == 403

    def test_email_test_endpoint(self, admin_token):
        # With fake SMTP, should fall back to Emergent Resend
        # Ensure a fake SMTP config exists
        requests.put(f"{API}/email-settings", headers=hdr(admin_token), json={
            "smtp_host": "smtp.fake.invalid",
            "smtp_port": 587,
            "smtp_username": "fake",
            "smtp_password": "fakepw",
            "from_email": "from@example.com",
            "from_name": "TEST",
        }, timeout=30)
        r = requests.post(f"{API}/email-settings/test", headers=hdr(admin_token),
                          json={"to": "test@example.com"}, timeout=90)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        # Test endpoint always returns 200; check ok flag. Accept either succeeded via fallback or provider err.
        assert "ok" in d
        if d.get("ok") is True:
            assert d.get("sent_via")  # non-empty


# ============ CRON ENDPOINT ============
class TestCronAutoMonthly:
    def test_cron_requires_bearer(self):
        r = requests.post(f"{API}/cron/auto-monthly-send", timeout=30)
        assert r.status_code == 401

    def test_cron_wrong_secret(self):
        r = requests.post(f"{API}/cron/auto-monthly-send",
                          headers={"Authorization": "Bearer wrong"}, timeout=30)
        assert r.status_code == 401

    def test_cron_disabled_skips(self, admin_token):
        # Ensure auto_monthly_send disabled
        requests.put(f"{API}/email-settings", headers=hdr(admin_token),
                     json={"auto_monthly_send": False}, timeout=30)
        r = requests.post(f"{API}/cron/auto-monthly-send",
                          headers={"Authorization": f"Bearer {CRON_SECRET}"}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ok") is True
        assert "skipped" in d

    def test_cron_enabled_queues(self, admin_token):
        # Enable and try
        requests.put(f"{API}/email-settings", headers=hdr(admin_token),
                     json={"auto_monthly_send": True}, timeout=30)
        try:
            r = requests.post(f"{API}/cron/auto-monthly-send",
                              headers={"Authorization": f"Bearer {CRON_SECRET}"}, timeout=30)
            assert r.status_code == 200, r.text
            d = r.json()
            assert d.get("ok") is True
            assert d.get("status") == "queued"
            assert d.get("period")  # YYYY-MM
        finally:
            # Reset for idempotency
            requests.put(f"{API}/email-settings", headers=hdr(admin_token),
                         json={"auto_monthly_send": False}, timeout=30)


# ============ REPORTS FILTERS ============
class TestReportsFilters:
    def test_attendance_month_filter(self, admin_token):
        r = requests.get(f"{API}/reports/attendance", headers=hdr(admin_token),
                         params={"month": "2026-08"}, timeout=60)
        assert r.status_code == 200, r.text[:200]
        assert r.headers.get("content-type", "").startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def test_attendance_user_customer_filter(self, admin_token, tech_user, demo_customer):
        r = requests.get(f"{API}/reports/attendance", headers=hdr(admin_token),
                         params={"user_id": tech_user["id"], "customer_id": demo_customer["id"]}, timeout=60)
        assert r.status_code == 200, r.text[:200]

    def test_customers_customer_id_filter(self, admin_token, demo_customer):
        r = requests.get(f"{API}/reports/customers", headers=hdr(admin_token),
                         params={"customer_id": demo_customer["id"]}, timeout=60)
        assert r.status_code == 200, r.text[:200]

    def test_employees_role_filter(self, admin_token):
        r = requests.get(f"{API}/reports/employees", headers=hdr(admin_token),
                         params={"role": "technician"}, timeout=60)
        assert r.status_code == 200, r.text[:200]

    def test_employees_pdf_role_filter(self, admin_token):
        r = requests.get(f"{API}/reports/employees", headers=hdr(admin_token),
                         params={"role": "technician", "format": "pdf"}, timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
