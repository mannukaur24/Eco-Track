# Security Audit – EcoTrack

## 1. Audit Overview

This security audit reviews the EcoTrack application for common web application
vulnerabilities. Findings are based on code inspection and the executed test
suite (106 tests passed as of the latest run). Identified issues were remediated
as described in sections 2–12.

## 2. Password Hashing

| Control | Implementation | Status |
|---------|---------------|--------|
| Hashing algorithm | Werkzeug `generate_password_hash` (scrypt method by default) | PASS |
| Password storage | `password_hash` column (VARCHAR 255), never plain text | PASS |
| Password verification | `check_password_hash` constant-time comparison | PASS |
| Password policy | Minimum 8 characters, maximum 128 characters (WTForms validation) | PASS |
| Password confirmation | Required on registration and change password | PASS |
| Current password verification | Required before changing password | PASS |

## 3. Authentication Bypass

| Control | Implementation | Status |
|---------|---------------|--------|
| Session-based auth | Flask-Login with `UserMixin` | PASS |
| Login required decorator | `@login_required` on all protected routes | PASS |
| Session protection | `login_manager.session_protection = "strong"` | PASS |
| Inactive account rejection | Login route checks `user.is_active` before login | PASS |
| Login redirect | Authenticated users redirected from login/register pages | PASS |
| Next URL validation | `next` must be a relative local path; absolute and protocol-relative URLs (e.g. `//example.com`, `http://example.com`) are rejected | PASS |

## 4. Role-Based Access Control (RBAC)

| Control | Implementation | Status |
|---------|---------------|--------|
| Role constants | `Role.CITIZEN`, `Role.ADMINISTRATOR`, `Role.STAFF` | PASS |
| Role decorators | `citizen_required`, `administrator_required`, `staff_required`, `admin_or_staff_required` | PASS |
| Server-side enforcement | Role checks on every protected route, not just UI | PASS |
| Administrator provisioning | Admin accounts not available in public registration; created via `flask create-admin` CLI or directly by an administrator | PASS |
| Public registration roles | Only Citizen; Collection Staff is not offered | PASS |
| Staff profile provisioning | Every administrator-created staff account receives a valid `Staff` profile | PASS |
| 403 on unauthorized | Authenticated users without correct role receive HTTP 403 | PASS |

## 5. CSRF Protection

| Control | Implementation | Status |
|---------|---------------|--------|
| CSRF protection | Flask-WTF `CSRFProtect` initialized on app | PASS |
| CSRF on forms | All WTForms include `{{ form.hidden_tag() }}` / `{{ csrf_token() }}` | PASS |
| CSRF in tests | Disabled only in TestingConfig for test convenience | PASS |
| State-changing forms | All POST/PUT/DELETE routes protected | PASS |
| Logout | POST-only, CSRF-protected | PASS |

## 6. SQL Injection Risks

| Control | Implementation | Status |
|---------|---------------|--------|
| ORM usage | SQLAlchemy ORM for all database queries | PASS |
| Parameterized queries | No raw SQL string concatenation | PASS |
| ILike with bound parameters | `Report.reference.ilike(f"%{search}%")` uses SQLAlchemy binding | PASS |
| Legacy API warnings | Fixed all `Query.get()` → `db.session.get()` for SQLAlchemy 2.0 | PASS |

## 7. XSS Risks

| Control | Implementation | Status |
|---------|---------------|--------|
| Template autoescaping | Jinja2 autoescaping enabled by default for `.html` templates | PASS |
| No `|safe` filter | No usage of `|safe` on user-controlled data | PASS |
| `|tojson` filter | Used in analytics template for Chart.js data; Jinja2 escapes for HTML context | PASS |
| Flash messages | User input displayed via Flask flash, autoescaped in templates | PASS |

## 8. Session Configuration

| Control | Implementation | Status |
|---------|---------------|--------|
| Session cookie HttpOnly | `SESSION_COOKIE_HTTPONLY = True` | PASS |
| Session cookie SameSite | `SESSION_COOKIE_SAMESITE = "Lax"` | PASS |
| Remember cookie HttpOnly | `REMEMBER_COOKIE_HTTPONLY = True` | PASS |
| Remember cookie SameSite | `REMEMBER_COOKIE_SAMESITE = "Lax"` | PASS |
| Secure cookies in production | `SESSION_COOKIE_SECURE = True` in ProductionConfig | PASS |
| Secret key from env | `SECRET_KEY` loaded from environment variable | PASS |
| Production secret required | Production fails to start if `SECRET_KEY` is missing or shorter than 16 characters | PASS |
| Development fallback | Development may use a fallback secret with a logged warning; never used in production | PASS |

## 9. Insecure Direct Object References (IDOR)

| Control | Implementation | Status |
|---------|---------------|--------|
| Citizen complaint ownership | `get_report_by_reference` filters by `user_id=user.id` | PASS |
| Staff task ownership | `get_task_by_id` filters by `staff_id=staff_user.id` | PASS |
| Staff task list | `get_staff_tasks` filters by `staff_id=staff_user.id` | PASS |
| Admin complaint access | Admin can access all complaints (by design) | PASS |
| Complaint image access | Image route allows owner, administrator, or assigned staff only | PASS |

## 10. File Upload Vulnerabilities

| Control | Implementation | Status |
|---------|---------------|--------|
| Extension validation | Allowed: png, jpg, jpeg, gif, webp | PASS |
| Magic byte detection | Validates file content type from header bytes | PASS |
| Size limit | 5 MB maximum (`MAX_CONTENT_LENGTH`) | PASS |
| Safe filenames | Server-generated `secrets.token_hex(16)` + extension | PASS |
| Path traversal prevention | Image-serving route rejects `..`, absolute paths, backslashes, and resolves inside the upload folder | PASS |
| Upload folder | `instance/uploads` by default, outside the public `static/` directory | PASS |
| Empty file rejection | Zero-byte files rejected | PASS |
| Authorized image serving | `/uploads/<filename>` requires login + ownership/staff-assignment/admin | PASS |

## 11. Environment Secret Exposure

| Control | Implementation | Status |
|---------|---------------|--------|
| .env file | `.env.example` with placeholders, real `.env` gitignored | PASS |
| No hardcoded passwords | All secrets via `os.environ.get()` | PASS |
| Production secret enforced | `SECRET_KEY` mandatory in production; application refuses to start otherwise | PASS |

## 12. Sensitive Data Leakage

| Control | Implementation | Status |
|---------|---------------|--------|
| Error handlers | 403/404/500 render templates without exception details | PASS |
| Server error logging | 500 errors logged server-side only | PASS |
| Health endpoint | Returns 503 without raw exception details when DB is unreachable; details logged server-side | PASS |
| Map data privacy | Complaint map shows reference, category, status, location only – no citizen PII | PASS |
| CSV exports | Admin-only; citizen name/email included in complaint register (admin-only access) | PASS |
| Flash messages | No sensitive data in flash messages | PASS |

## 13. Unauthorized Database Operations

| Control | Implementation | Status |
|---------|---------------|--------|
| Foreign key constraints | ON DELETE CASCADE/SET NULL defined on all relationships | PASS |
| Unique constraints | Email, reference, category_name unique | PASS |
| Category deletion guard | Cannot delete category in use by complaints | PASS |
| Role-based write access | All write operations protected by role decorators | PASS |

## 14. Complaint Status Audit Trail

| Control | Implementation | Status |
|---------|---------------|--------|
| Status history table | `report_status_history` records report ID, previous status, new status, updated-by user ID, timestamp, remarks | PASS |
| Recorded events | Submission, verification, rejection, assignment, progress, completion | PASS |
| No fabricated records | History is written only when a real transition occurs | PASS |
| Citizen timeline | Complaint detail page displays the actual status history | PASS |

## 15. Summary

| Severity | Findings | Count |
|----------|----------|-------|
| Critical | None remediated; open redirect, insecure production secret fallback, public staff registration, and unprotected complaint images were fixed | 0 open |
| High | None open | 0 open |
| Medium | None open | 0 open |
| Low | CSRF disabled in test config (test-only) | 1 |

All identified security issues have been remediated and verified by the executed
test suite. The application is an academic prototype and is not claimed to be
production-ready for deployment handling sensitive municipal data without
further review (HTTPS, WAF, penetration testing, and MySQL 8 deployment
validation).
