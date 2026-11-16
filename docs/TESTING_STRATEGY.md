# Testing Strategy – EcoTrack

## 1. Overview

This document defines the testing strategy for the EcoTrack – Smart Waste Management System, a BCA final-year project. Testing is performed using **Pytest** with the Flask test client against a SQLite database (TestingConfig). All **106 tests pass** as of the latest test run.

Test results reported here reflect tests that were actually executed; no results are claimed for untested areas.

## 2. Test Environment

| Component | Value |
|-----------|-------|
| Test runner | Pytest 8.3.3 |
| Flask test client | pytest-flask 1.3.0 |
| Test database | SQLite (file-based: `instance/ecotrack_test.db`) |
| CSRF in tests | Disabled (TestingConfig) |
| App config | `TestingConfig` (SQLite, `SERVER_NAME=localhost.localdomain`) |
| Upload folder in tests | Temporary directory per test session |

## 3. Test Pyramid

### Unit Tests (Service Layer)
Test individual service methods in isolation:
- `ComplaintService` – report creation, validation, user report retrieval, status-history recording
- `AdminService` – complaint verify/reject, task assignment, staff/category/awareness CRUD, dashboard stats (SQL aggregates)
- `StaffService` – task progress updates, status transitions, complaint sync, complaint status history
- `AnalyticsService` – dashboard stats, chart data queries (by category, status, monthly, staff performance, pending vs completed, location-wise)
- `ReportsService` – CSV export headers and content

### Integration Tests (Routes)
Test full HTTP request/response cycles through the Flask test client:
- Auth routes: register, login, logout (POST-only), profile, change password, open redirect
- Citizen routes: dashboard, submit complaint, history, detail, image access
- Admin routes: dashboard, complaints, verify, reject, assign task, staff, categories, awareness, date filtering
- Staff routes: dashboard, tasks, task detail, task update, image access
- Analytics routes: analytics dashboard, map, all CSV report exports
- Main routes: health check (OK and DB-failure 503)

### Authorization Tests
Verify role-based access control at the route level:
- Citizen cannot access admin routes (403)
- Staff cannot access admin routes (403)
- Admin cannot access staff routes (403)
- Unauthenticated users redirected to login
- Citizens cannot access other citizens' complaints
- Staff cannot access tasks assigned to other staff
- Citizens/admins/assigned staff can access complaint images; others receive 403

### Configuration Tests
- Production requires a strong `SECRET_KEY`; missing or weak secret fails safely
- Development works without a production secret (fallback with warning)

## 4. Test Coverage by Module

| Module | Test File | Tests |
|--------|-----------|-------|
| Authentication | `tests/test_auth.py` | 16 |
| Configuration | `tests/test_config.py` | 4 |
| Citizen portal | `tests/test_citizen.py` | 10 |
| Database models | `tests/test_database.py` | 11 |
| Administrator panel | `tests/test_admin.py` | 18 |
| Staff portal | `tests/test_staff.py` | 11 |
| Security (images, health) | `tests/test_security.py` | 8 |
| Status history | `tests/test_status_history.py` | 7 |
| Migrations | `tests/test_migration.py` | 2 |
| Analytics & reports | `tests/test_analytics.py` | 19 |
| **Total** | | **106** |

## 5. Test Fixtures

`tests/conftest.py` provides:
- `app` – creates Flask app with TestingConfig, creates all tables, seeds waste categories
- `client` – Flask test client
- `citizen` – registered citizen user
- `staff_user` – staff user provisioned directly (administrator-controlled, with a valid `Staff` profile)

## 6. Test Execution

```bash
cd C:\ARRU CODES\projects\EcoTrack
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pytest
```

Expected result: all tests pass (106 passed as of latest run).

## 7. Test Naming Convention

Test functions are named `test_<scenario>_<expected_outcome>`, e.g.:
- `test_login_success`
- `test_login_invalid_credentials`
- `test_staff_cannot_access_other_staff_task`
- `test_production_requires_secret_key`
- `test_owner_can_view_own_complaint_image`
- `test_other_citizen_cannot_view_image`
- `test_assigned_staff_can_view_image`
- `test_task_progress_and_completion_record_history`
- `test_admin_complaints_date_filter_inclusive_end_date`
- `test_initial_migration_upgrades_fresh_database`
- `test_health_endpoint_db_failure`

## 8. Continuous Testing

Tests should be run after every code change and before any phase completion. The
test database is created fresh per test session and is gitignored.

## 9. What Is NOT Tested

- PDF export (CSV exports are tested instead)
- JavaScript/Chart.js rendering (frontend charts verified via code inspection)
- Browser-based UI testing (responsive layout verified via template inspection)
- MySQL 8 integration (tests use SQLite for speed; production uses MySQL 8; schema parity is maintained via SQLAlchemy models and the committed migration)
- Load/performance testing (not performed; suitable for academic prototype scale)
- Production deployment over HTTPS (secure cookies require HTTPS; not exercised in tests)
