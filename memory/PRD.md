# PestOps Pro — Field Operations Management Platform for Pest Control

## Original Problem Statement
Web-based Field Operations Management Platform untuk perusahaan Pest Control. Mengelola teknisi/operator lapangan, pelanggan, pekerjaan, jadwal, absensi, perjalanan, GPS tracking, service report, cuti, dan laporan operasional. Production-ready dengan Clean Architecture, RBAC + Granular User Permission, GPS Tracking, Real-time monitoring, mobile-first untuk teknisi, PDF/Excel reporting.

## User Choices
- Scope: all phases + enhancement iteration
- Auth: JWT (email + password) with bcrypt
- Map: OpenStreetMap + Leaflet
- Storage: Emergent Object Storage
- Email: Emergent-managed Resend
- Delivery: Build on Emergent platform

## Architecture
- Backend: FastAPI + Motor(MongoDB) — `server.py` (~1800 LOC), `auth.py`, `storage.py`, `reports.py`, `emailer.py`
- Frontend: React 19 + React Router + Tailwind + shadcn/ui + Leaflet + Recharts + react-signature-canvas
- 4 Roles: **admin**, **technician**, **client**, **developer** — each with granular per-user permission matrix (15 modules × 8 actions)
- Client role is data-scoped by `customer_id` at query level (hard 403 on cross-tenant queries)

## Test Credentials (also at /app/memory/test_credentials.md)
- **Admin**: `admin@pestops.com` / `Admin@123`
- **Technician**: `technician@pestops.com` / `Tech@123`
- **Client**: `client@pestops.com` / `Client@123` (scoped to PT. John Robert Powers)
- **Developer**: `developer@pestops.com` / `Dev@123`

## Implemented Features

### Iteration 1 (MVP)
- JWT authentication, RBAC + granular permissions
- Users/Members CRUD + permission editor
- Customers CRUD with contract auto-inactivation
- Tasks CRUD with auto-computed status (pending/overdue/in_progress/completed/cancelled)
- Attendance check-in/out with live camera + GPS + geofence
- GPS tracking (watchPosition + 30s heartbeat)
- Live Map (Leaflet + OSM) with tech markers
- Travel/Perjalanan summary
- Service Report + PDF export
- Leave requests + approve/reject flow
- Reports export (Attendance/Customer/Employee PDF+Excel)
- Dashboard + Audit log + Settings + Emergent Object Storage

### Iteration 2 (Enhancement — this iteration)
- **4-role model**: added `client` and `developer` roles + seeded demo accounts
- **Client scope isolation**: hard 403 on `?customer_id=` mismatches (tasks/service-reports/schedules)
- **Schedule model + Mass Create**: `/api/schedules/mass-create` generates recurring standby entries with weekday filter + time range + preview count
- **Address Autocomplete + Auto-Geocode**: `/api/geocode/search` + `/api/geocode/reverse` via Nominatim; Customer form uses `<AddressAutocomplete>` component with lat/lng lock-in
- **Reverse Geocode in Attendance**: check-in/out saves `address` (human-readable) alongside coords; **working_hours computed automatically** on check-out
- **Service Report multi-photo + captions + client signature**: new schema `{path, caption}`, both technician and client signature pads
- **Bulk ZIP export**: `/api/service-reports/export/zip` respects filters (customer_id + date range)
- **Monthly Report**: `/api/monthly-report` returns client info + `historical_pest` (contract_start → target month) + service_reports & attendance for target month; `/api/monthly-report/pdf` exports comprehensive PDF
- **Email via Emergent Resend**: `/api/service-reports/{id}/email` and `/api/monthly-report/email` — server-side templates only (G1–G5 compliant), attachments as PDF, recipient from client record with optional override
- **Branding**: `/api/branding` GET/PUT — developer role can update company logo/name/address; used in reports
- **Dark/Light theme toggle** persisted in localStorage
- **i18n (ID/EN)**: dictionary-backed hook, sidebar + top-level UI translations
- **Filters + Reset**: on Tasks, Service Reports, Attendance, Travel, Schedule
- **View on Map + Navigate**: buttons on attendance records + task detail + customer cards (open Google Maps directions)

## Backend Test Results
- **Iteration 1**: 23/23 passing
- **Iteration 2**: 33/33 passing (after fixes: duplicate photos field removed, client-scope 403 hard-enforced)
- **Total**: **56/56 (100%)**

## Backlog / Nice-to-Have (P1/P2)
- **P1** ELIGIBLE: Word (.docx) + PowerPoint exports for Monthly Report; Offline outbox (IndexedDB); Automated scheduled DB backup; Route replay animation on travel map; Notification bell wired to backend endpoint
- **P1**: Split server.py into feature routers (schedules/geocode/monthly_report/bulk_export/email/branding); Rate-limit/cache Nominatim proxy; Google Login (whitelist)
- **P2**: System health dashboard; Advanced analytics; Real signature verification; Native mobile app

## Known Limitations
- Email sending depends on Emergent-managed Resend key being active; if inactive, endpoint returns 502 (auth+ownership+validation still enforced correctly)
- GPS tracking is browser-limited when tab is in background (documented as `GPS Tracking Limited` status)
- Nominatim geocoding has 1 req/s TOS — should be cached for production scale
