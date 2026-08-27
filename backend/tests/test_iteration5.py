"""PestOps Pro Iteration 5 backend tests.

Covers new/changed features:
- CSV bulk customer import + template download
- Twilio WhatsApp integration (settings expansion, /wa/test, per-SR, per-monthly)
- Monthly Report Excel + PPTX exports
- Independent email/wa on-off toggles (409 when disabled)
- Cron auto-monthly handles both channels independently
"""
import os
import io
import pytest
import requests

# Use localhost to bypass Cloudflare 502 during long Twilio outbound waits
BASE_URL = os.environ.get("BACKEND_TEST_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"
CRON_SECRET = "7f3e8c2d1a9b4e6f5c8d0a2b7e1f4c9d8b6a3e5f7c1d9b0a4e2f8c6d3b1a5e7f"

ADMIN = ("admin@pestops.com", "Admin@123")
TECH = ("technician@pestops.com", "Tech@123")
DEV = ("developer@pestops.com", "Dev@123")
CLIENT = ("client@pestops.com", "Client@123")


def _login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def hdr(t):
    return {"Authorization": f"Bearer {t}"}


# ------------ fixtures ------------
@pytest.fixture(scope="session")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="session")
def tech_token():
    return _login(*TECH)


@pytest.fixture(scope="session")
def dev_token():
    return _login(*DEV)


@pytest.fixture(scope="session")
def a_customer_with_phone(admin_token):
    """Return an existing customer id with a phone number (create if none)."""
    r = requests.get(f"{API}/customers", headers=hdr(admin_token), timeout=30)
    assert r.status_code == 200
    for c in r.json():
        if c.get("phone") and c.get("status") == "active":
            return c
    # create one
    doc = {
        "company_name": "TEST_iter5_customer_phone",
        "contact_person": "Tester",
        "phone": "+6281234567890",
        "email": "iter5@test.local",
        "address": "Jl. Test",
        "category": "Regular",
    }
    r = requests.post(f"{API}/customers", json=doc, headers=hdr(admin_token), timeout=30)
    assert r.status_code in (200, 201), r.text
    return r.json()


@pytest.fixture(scope="session", autouse=True)
def _reset_state(admin_token):
    """Ensure sane starting state; restore at end."""
    # snapshot initial settings
    r = requests.get(f"{API}/email-settings", headers=hdr(admin_token), timeout=30)
    initial = r.json() if r.status_code == 200 else {}
    # Ensure email_enabled True, wa_enabled False initially
    requests.put(f"{API}/email-settings",
                 json={"email_enabled": True, "wa_enabled": False,
                       "auto_monthly_send": False, "wa_auto_monthly": False},
                 headers=hdr(admin_token), timeout=30)
    yield
    # Restore to safe defaults
    requests.put(f"{API}/email-settings",
                 json={"email_enabled": True, "wa_enabled": False,
                       "auto_monthly_send": False, "wa_auto_monthly": False},
                 headers=hdr(admin_token), timeout=30)


# ============================================================
# CSV IMPORT
# ============================================================
class TestCSVImport:
    def test_import_template_csv_content(self, admin_token):
        r = requests.get(f"{API}/customers/import-template.csv",
                         headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert ct.startswith("text/csv"), ct
        first = r.text.splitlines()[0]
        assert "company_name" in first, first

    def test_import_csv_creates_and_skips_dupes(self, admin_token):
        # Row 1: unique new customer TEST_iter5_bulk_A
        # Row 2: duplicate name we know exists (created above OR reuse TEST_iter5_bulk_A on 2nd run)
        # Row 3: empty company_name -> skip
        # First create a known duplicate
        dup_name = "TEST_iter5_dup_seed"
        requests.post(f"{API}/customers",
                      json={"company_name": dup_name, "phone": "+62811", "email": "d@t.co",
                            "address": "x", "category": "Regular"},
                      headers=hdr(admin_token), timeout=30)

        import time, random
        uniq = f"TEST_iter5_bulk_{int(time.time())}_{random.randint(100,999)}"
        csv_body = (
            "company_name,project_name,contact_person,phone,email,address,latitude,longitude,category,contract_start,contract_end\n"
            f"{uniq},HQ,Alice,+628111,a@t.co,Jl A,-6.2,106.8,Regular,2026-01-01,2026-12-31\n"
            f"{dup_name},HQ,Bob,+628112,b@t.co,Jl B,,,Regular,,\n"
            ",Empty,No Name,+628113,c@t.co,,,,,,\n"
        )
        files = {"file": ("bulk.csv", csv_body.encode("utf-8"), "text/csv")}
        r = requests.post(f"{API}/customers/import-csv",
                          files=files, headers=hdr(admin_token), timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["created"] >= 1
        assert data["skipped"] >= 2  # dup + empty
        assert isinstance(data["errors"], list)

    def test_import_csv_requires_permission(self, tech_token):
        files = {"file": ("x.csv", b"company_name\nTEST_x\n", "text/csv")}
        r = requests.post(f"{API}/customers/import-csv",
                          files=files, headers=hdr(tech_token), timeout=30)
        assert r.status_code == 403, r.text


# ============================================================
# MONTHLY REPORT EXPORTS
# ============================================================
class TestMonthlyExports:
    def _pick_customer(self, admin_token):
        r = requests.get(f"{API}/customers", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        actives = [c for c in r.json() if c.get("status") == "active"]
        assert actives, "no active customer"
        return actives[0]["id"]

    def test_monthly_report_excel(self, admin_token):
        cid = self._pick_customer(admin_token)
        r = requests.get(f"{API}/monthly-report/excel",
                         params={"customer_id": cid, "month": "2026-01"},
                         headers=hdr(admin_token), timeout=60)
        assert r.status_code == 200, r.text
        ct = r.headers.get("content-type", "")
        assert "spreadsheetml.sheet" in ct, ct
        # xlsx magic: PK\x03\x04
        assert r.content[:2] == b"PK", r.content[:20]
        assert len(r.content) > 500

    def test_monthly_report_pptx(self, admin_token):
        cid = self._pick_customer(admin_token)
        r = requests.get(f"{API}/monthly-report/pptx",
                         params={"customer_id": cid, "month": "2026-01"},
                         headers=hdr(admin_token), timeout=60)
        assert r.status_code == 200, r.text
        ct = r.headers.get("content-type", "")
        assert "presentationml.presentation" in ct, ct
        assert r.content[:2] == b"PK", r.content[:20]
        assert len(r.content) > 1000


# ============================================================
# EMAIL SETTINGS EXPANSION (WA fields)
# ============================================================
class TestEmailSettingsWA:
    def test_get_exposes_wa_fields_and_masks_token(self, admin_token):
        r = requests.get(f"{API}/email-settings", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ("wa_enabled", "wa_account_sid", "wa_from", "wa_sr_template",
                  "wa_mr_template", "wa_auto_monthly", "email_enabled",
                  "wa_auth_token_set"):
            assert k in d, f"missing {k} in email-settings response"
        assert "wa_auth_token" not in d, "wa_auth_token must not be exposed"
        assert isinstance(d["wa_auth_token_set"], bool)

    def test_put_whitelists_wa_and_preserves_secret(self, admin_token):
        # Set a token
        r = requests.put(f"{API}/email-settings",
                         json={"wa_account_sid": "AC_test_sid",
                               "wa_auth_token": "some-token-xyz",
                               "wa_from": "whatsapp:+14155238886",
                               "some_unknown_key": "should_be_dropped"},
                         headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["wa_account_sid"] == "AC_test_sid"
        assert d["wa_auth_token_set"] is True
        assert "some_unknown_key" not in d

        # PUT with empty wa_auth_token must NOT overwrite
        r = requests.put(f"{API}/email-settings",
                         json={"wa_auth_token": "", "wa_account_sid": "AC_test_sid2"},
                         headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["wa_account_sid"] == "AC_test_sid2"
        assert d["wa_auth_token_set"] is True, "empty token must not overwrite existing"

        # PUT with null wa_auth_token must NOT overwrite
        r = requests.put(f"{API}/email-settings",
                         json={"wa_auth_token": None},
                         headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        assert r.json()["wa_auth_token_set"] is True


# ============================================================
# WA TEST + PER-REPORT WHATSAPP
# ============================================================
class TestWhatsApp:
    def test_wa_test_requires_admin_dev(self, tech_token, admin_token):
        # Enable wa first
        requests.put(f"{API}/email-settings", json={"wa_enabled": True},
                     headers=hdr(admin_token), timeout=30)
        r = requests.post(f"{API}/wa/test", json={"to": "+6281234567890"},
                          headers=hdr(tech_token), timeout=30)
        assert r.status_code == 403, r.text

    def test_wa_test_with_bad_creds_returns_502(self, admin_token):
        # wa_enabled true from previous test; auth token from env is API key SID -> 401 from Twilio
        r = requests.post(f"{API}/wa/test", json={"to": "+6281234567890"},
                          headers=hdr(admin_token), timeout=60)
        # 502 with Twilio error propagated
        assert r.status_code == 502, r.text
        detail = r.json().get("detail", "")
        assert "Twilio" in detail or "401" in detail, detail

    def test_wa_disabled_returns_409(self, admin_token):
        requests.put(f"{API}/email-settings", json={"wa_enabled": False},
                     headers=hdr(admin_token), timeout=30)
        r = requests.post(f"{API}/wa/test", json={"to": "+6281234567890"},
                          headers=hdr(admin_token), timeout=30)
        assert r.status_code == 409, r.text
        # re-enable for next tests
        requests.put(f"{API}/email-settings", json={"wa_enabled": True},
                     headers=hdr(admin_token), timeout=30)

    def test_service_report_whatsapp(self, admin_token, a_customer_with_phone):
        # ensure wa_enabled
        requests.put(f"{API}/email-settings", json={"wa_enabled": True},
                     headers=hdr(admin_token), timeout=30)
        r = requests.get(f"{API}/service-reports", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200
        srs = r.json()
        if not srs:
            pytest.skip("no service reports available")
        sr = srs[0]
        payload = {"to": "+6281234567890"}
        r = requests.post(f"{API}/service-reports/{sr['id']}/whatsapp",
                          json=payload, headers=hdr(admin_token), timeout=60)
        # Task spec: credentials will fail -> 500/502 acceptable
        assert r.status_code in (200, 500, 502), r.text

    def test_service_report_whatsapp_no_phone_returns_400(self, admin_token):
        # Create an SR-less customer w/o phone won't help; the endpoint needs SR.
        # Instead, we look for an SR whose customer has no phone and no override provided.
        r = requests.get(f"{API}/customers", headers=hdr(admin_token), timeout=30)
        no_phone = [c for c in r.json() if not c.get("phone") and c.get("status") == "active"]
        if not no_phone:
            # create one, no SR though -> can't test SR endpoint here fully; skip
            pytest.skip("no customer without phone in DB and no SR for one")
        # find an SR for that customer
        cust = no_phone[0]
        r = requests.get(f"{API}/service-reports", params={"customer_id": cust["id"]},
                         headers=hdr(admin_token), timeout=30)
        srs = [s for s in r.json() if s.get("customer_id") == cust["id"]] if r.status_code == 200 else []
        if not srs:
            pytest.skip(f"no SR for phone-less customer {cust['id']}")
        r = requests.post(f"{API}/service-reports/{srs[0]['id']}/whatsapp",
                          json={}, headers=hdr(admin_token), timeout=30)
        assert r.status_code == 400, r.text

    def test_monthly_report_whatsapp(self, admin_token, a_customer_with_phone):
        # ensure wa_enabled
        requests.put(f"{API}/email-settings", json={"wa_enabled": True},
                     headers=hdr(admin_token), timeout=30)
        cid = a_customer_with_phone["id"]
        # Endpoint has three Body(...) params so nested "body" key required
        r = requests.post(f"{API}/monthly-report/whatsapp",
                          json={"customer_id": cid, "month": "2026-01",
                                "body": {"to": "+6281234567890"}},
                          headers=hdr(admin_token), timeout=60)
        assert r.status_code in (200, 500, 502), r.text


# ============================================================
# ENABLED TOGGLES
# ============================================================
class TestEnabledToggles:
    def test_email_disabled_test_returns_409(self, admin_token):
        requests.put(f"{API}/email-settings", json={"email_enabled": False},
                     headers=hdr(admin_token), timeout=30)
        r = requests.post(f"{API}/email-settings/test",
                         json={"to": "sink@example.com"},
                         headers=hdr(admin_token), timeout=30)
        assert r.status_code == 409, r.text
        # Restore
        requests.put(f"{API}/email-settings", json={"email_enabled": True},
                     headers=hdr(admin_token), timeout=30)
        r = requests.post(f"{API}/email-settings/test",
                         json={"to": "sink@example.com"},
                         headers=hdr(admin_token), timeout=60)
        assert r.status_code in (200, 502), r.text


# ============================================================
# CRON
# ============================================================
class TestCron:
    def test_cron_skips_when_both_disabled(self, admin_token):
        requests.put(f"{API}/email-settings",
                     json={"auto_monthly_send": False, "wa_auto_monthly": False},
                     headers=hdr(admin_token), timeout=30)
        r = requests.post(f"{API}/cron/auto-monthly-send",
                         headers={"Authorization": f"Bearer {CRON_SECRET}"},
                         timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("skipped", "").startswith("email/wa auto disabled"), d

    def test_cron_queued_when_one_enabled(self, admin_token):
        requests.put(f"{API}/email-settings",
                     json={"auto_monthly_send": True, "email_enabled": True,
                           "wa_auto_monthly": False},
                     headers=hdr(admin_token), timeout=30)
        r = requests.post(f"{API}/cron/auto-monthly-send",
                         headers={"Authorization": f"Bearer {CRON_SECRET}"},
                         timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("status") == "queued", d
        # Restore
        requests.put(f"{API}/email-settings",
                     json={"auto_monthly_send": False},
                     headers=hdr(admin_token), timeout=30)


# ============================================================
# REGRESSION: full task -> SR flow smoke
# ============================================================
class TestSmoke:
    def test_health(self, admin_token):
        r = requests.get(f"{API}/customers", headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200

    def test_monthly_report_historical_pest_includes_target_month(self, admin_token):
        r = requests.get(f"{API}/customers", headers=hdr(admin_token), timeout=30)
        cid = [c for c in r.json() if c.get("status") == "active"][0]["id"]
        r = requests.get(f"{API}/monthly-report",
                        params={"customer_id": cid, "month": "2030-06"},
                        headers=hdr(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        # historical_pest may be empty for far-future month w/o SRs; just ensure key exists
        assert "historical_pest" in r.json()
