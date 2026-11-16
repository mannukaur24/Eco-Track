# Testing Strategy – EcoTrack

## 1. Overview

This document defines the testing strategy for the EcoTrack – Smart Waste Management System, a BCA final-year project. Testing is performed using **Pytest** with **Flask-TestClient** against an in-memory/file-based SQLite database (TestingConfig). All 77 tests pass as of the latest test run.

## 2. Test Environment

| Component | Value |
|-----------|-------|
| Test runner | Pytest 8.3.3 |
| Flask test client | Flask-Testing via pytest-flask 1.3.0 |
| Test database | SQLite (file-based: `ecotrack_test.db`) |
| CSRF in tests | Disabled (TestingConfig) |
| App config | `TestingConfig` (in-memory SQLite, `SERVER_NAME=localhost.localdomain`) |

## 3. Test Pyramid

### Unit Tests (Service Layer)
Test individual service methods in isolation:
- `ComplaintService` – report creation, validation, user report retrieval
- `AdminService` – complaint verify/reject, task assignment, staff/category/awareness CRUD
- `StaffService` – task progress updates, status transitions, complaint sync
- `AnalyticsService` – dashboard stats, chart data queries (by category, status, monthly, staff performance, pending vs completed, location-wise)
- `ReportsService` – CSV export headers and content

### Integration Tests (Routes)
Test full HTTP request/response cycles through Flask test client:
- Auth routes: register, login, logout, profile, change password
- Citizen routes: dashboard, submit complaint, history, detail
- Admin routes: dashboard, complaints, verify, reject, assign task, staff, categories, awareness
- Staff routes: dashboard, tasks, task detail, task update
- Analytics routes: analytics dashboard, map, all CSV report exports

### Authorization Tests
Verify role-based access control at the route level:
- Citizen cannot access admin routes (403)
- Staff cannot access admin routes (403)
- Admin cannot access staff routes (403)
- Unauthenticated users redirected to login
- Citizens cannot access other citizens' complaints
- Staff cannot access tasks assigned to other staff

## 4. Test Coverage by Module

| Module | Test File | Tests |
|--------|-----------|-------|
| Authentication | `tests/test_auth.py` | 14 |
| Citizen portal | `tests/test_citizen.py` | 10 |
| Database models | `tests/test_database.py` | 11 |
| Administrator panel | `tests/test_admin.py` | 13 |
| Staff portal | `tests/test_staff.py` | 9 |
| Analytics & reports | `tests/test_analytics.py` | 20 |
| **Total** | | **77** |

## 5. Test Fixtures

`tests/conftest.py` provides:
- `app` – creates Flask app with TestingConfig, creates all tables, seeds waste categories
- `client` – Flask test client
- `citizen` – registered citizen user
- `staff_user` – registered staff user
- `admin_user` – directly created administrator user

## 6. Test Execution

```bash
cd C:\ARRU CODES\projects\EcoTrack
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pytest
```

Expected result: all tests pass (77 passed as of latest run).

## 7. Test Naming Convention

Test functions are named `test_<scenario>_<expected_outcome>`, e.g.:
- `test_login_success`
- `test_login_invalid_credentials`
- `test_staff_cannot_access_other_staff_task`
- `test_csv_complaint_register`

## 8. Continuous Testing

Tests should be run after every code change and before any phase completion. The test database (`ecotrack_test.db`) is created fresh per test session and is gitignored.

## 9. What Is NOT Tested

- PDF export (CSV exports are tested instead)
- JavaScript/Chart.js rendering (frontend charts verified via code inspection)
- Browser-based UI testing (responsive layout verified via template inspection)
- MySQL 8 integration (tests use SQLite for speed; production uses MySQL 8)
