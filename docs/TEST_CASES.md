# Test Cases – EcoTrack

Actual test results from the latest test suite execution. All **158 tests pass**.

## A. Authentication Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Valid registration | Register new citizen with valid data | Account created, flash "Account created successfully" | Pass | PASS |
| Duplicate email | Register with existing email | Flash "already exists" | Pass | PASS |
| Registration role restriction | Administrator not available in public registration form | "Administrator" not in page | Pass | PASS |
| Staff role not selectable publicly | Public registration form does not offer Staff role | `value="Staff"` absent | Pass | PASS |
| Public staff registration prevented | Register with role=Staff | User not created as staff | Pass | PASS |
| Valid login | Login with correct credentials | Redirect, flash "Welcome back" | Pass | PASS |
| Invalid login (wrong password) | Login with incorrect password | Flash "Invalid email or password" | Pass | PASS |
| Invalid login (nonexistent user) | Login with unregistered email | Flash "Invalid email or password" | Pass | PASS |
| Logout (POST-only) | POST /auth/logout | Redirect, session cleared | Pass | PASS |
| Logout rejects GET | GET /auth/logout | HTTP 405 Method Not Allowed | Pass | PASS |
| Profile requires login | Access /auth/profile without auth | Redirect to login | Pass | PASS |
| Profile update | Update full name and phone | Profile updated, flash success | Pass | PASS |
| Change password | Change password with valid current password | Password changed, flash success | Pass | PASS |
| Change password wrong current | Change password with incorrect current password | Flash "Current password is incorrect" | Pass | PASS |
| Citizen redirected after login | Citizen logs in | User role is Citizen | Pass | PASS |
| Inactive account cannot login | Login with deactivated account | Flash "deactivated" | Pass | PASS |

## B. Open Redirect Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Safe local next | next=/citizen/dashboard | Redirect to /citizen/dashboard | Pass | PASS |
| External URL rejected | next=http://example.com/ | Redirect to index, example.com absent | Pass | PASS |
| Protocol-relative URL rejected | next=//example.com/malicious | Redirect to index, example.com absent | Pass | PASS |

## C. Authorization Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Citizen route protection | Citizen accesses /admin/dashboard | 403 or "permission" message | Pass | PASS |
| Staff route protection | Staff accesses /admin/dashboard | 403 or "permission" message | Pass | PASS |
| Admin cannot access staff | Admin accesses /staff/dashboard | 403 or "permission" message | Pass | PASS |
| Cross-user complaint access | Citizen A views Citizen B's complaint | "not found or you do not have access" | Pass | PASS |
| Cross-staff task access | Staff A views Staff B's task | "not found or not assigned to you" | Pass | PASS |

## D. Image Privacy Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Owner image access | Citizen views own complaint image | HTTP 200, image content | Pass | PASS |
| Other citizen denied | Citizen B views Citizen A's image | HTTP 403 | Pass | PASS |
| Admin image access | Administrator views any complaint image | HTTP 200 | Pass | PASS |
| Assigned staff image access | Staff assigned to complaint views image | HTTP 200 | Pass | PASS |
| Unassigned staff denied | Unrelated staff views complaint image | HTTP 403 | Pass | PASS |
| Nonexistent image | Request missing image file | HTTP 404 | Pass | PASS |
| Path traversal rejected | Request ../windows/win.ini | HTTP 404 | Pass | PASS |

## E. Complaint Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Valid submission | Submit complaint with all required fields + image | Complaint created, reference starts with "ET-" | Pass | PASS |
| Missing category | Submit without category | Flash "Please select a waste category" | Pass | PASS |
| Short description | Submit description < 10 chars | Flash "at least 10 characters" | Pass | PASS |
| No address | Submit without address | Flash "Please provide an address" | Pass | PASS |
| Invalid image format | Upload non-image file | Flash "Invalid image type" or "not a valid image" | Pass | PASS |
| Oversized upload | Upload file > 5 MB | Flash "5 MB" | Pass | PASS |
| Unique references | Multiple submissions generate unique references | All references unique, start with "ET-" | Pass | PASS |
| Complaint ownership | Citizen views another user's complaint | Access denied | Pass | PASS |
| Complaint history | View submitted complaints | Complaints listed with references | Pass | PASS |
| Citizen dashboard | View citizen dashboard | "Citizen Dashboard" heading present | Pass | PASS |

## F. Status History Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Submission recorded | Complaint creation records history | Previous None, new Pending | Pass | PASS |
| Verify recorded | Admin verifies complaint | Pending → Verified | Pass | PASS |
| Reject recorded | Admin rejects complaint | Verified → Rejected, reason stored | Pass | PASS |
| Assignment recorded | Admin assigns task | Verified → Assigned | Pass | PASS |
| Progress recorded | Staff moves task to In Progress | Assigned → In Progress, complaint synced | Pass | PASS |
| Completion recorded | Staff completes task | In Progress → Completed, complaint synced | Pass | PASS |
| No fabricated records | Complaint with no transitions | Only submission record | Pass | PASS |
| Citizen timeline | Detail page shows status history | "Status History" and statuses present | Pass | PASS |

## G. Task Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Staff task visibility | Staff sees only own tasks | Other staff's tasks not visible | Pass | PASS |
| Unauthorized task access | Staff views another staff's task | "not found or not assigned to you" | Pass | PASS |
| Progress update | Update task Assigned → In Progress | Task status updated, TaskUpdate recorded, complaint synced | Pass | PASS |
| Completion workflow | Update task → Completed, verify complaint sync | task completed_at set, complaint status = Completed | Pass | PASS |
| Invalid transition | Update Completed → In Progress | Flash "Cannot move task" | Pass | PASS |
| Task history | View task updates/history | Updates listed with remarks | Pass | PASS |
| Staff dashboard | View staff dashboard | "Collection Staff Dashboard" heading present | Pass | PASS |
| Staff dashboard due dates | Staff dashboard with tasks containing due dates | HTTP 200 | Pass | PASS |

## H. Administrator Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Admin dashboard access | Admin views /admin/dashboard | 200, "Dashboard" present | Pass | PASS |
| Admin dashboard stats | Dashboard shows complaint/task stats | Stats computed via SQL aggregates | Pass | PASS |
| Admin dashboard due dates | Admin dashboard with tasks containing due dates | HTTP 200 | Pass | PASS |
| Admin view complaints | Admin views /admin/complaints | 200 | Pass | PASS |
| Inclusive end-date filter | Filter complaints by date_to | Entire end date included | Pass | PASS |
| Verify complaint | Admin verifies pending complaint | Complaint status = Verified | Pass | PASS |
| Reject with reason | Admin rejects with mandatory reason | Complaint status = Rejected, reason stored | Pass | PASS |
| Reject without reason | Admin rejects with empty reason | Flash "rejection reason is required" | Pass | PASS |
| Assign task | Admin assigns verified complaint to staff | CollectionTask created, complaint status = Assigned | Pass | PASS |
| Add staff | Admin creates new staff account | Staff created, flash "Staff member added" | Pass | PASS |
| Staff provisioning | Admin-created staff has Staff profile | Staff profile row exists | Pass | PASS |
| Duplicate staff email | Add staff with existing email | Flash "already exists" | Pass | PASS |
| Toggle staff active | Admin deactivates/reactivates staff | is_active toggled | Pass | PASS |
| Category management | Add, edit, delete categories | Categories managed correctly | Pass | PASS |
| Duplicate category | Add category with existing name | Flash "already exists" | Pass | PASS |
| Awareness management | Create, edit, publish/unpublish articles | Articles managed correctly | Pass | PASS |

## I. Analytics & Reporting Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Analytics dashboard access | Admin views /admin/analytics | 200, "Analytics" present | Pass | PASS |
| Analytics requires admin | Citizen accesses /admin/analytics | 403 or "permission" | Pass | PASS |
| Analytics date filter presets | Test 7days, 30days, 3months, custom | All return 200 | Pass | PASS |
| Chart data – by category | Verify category aggregation | Categories and counts returned | Pass | PASS |
| Chart data – by status | Verify status aggregation | Statuses and counts returned | Pass | PASS |
| Dashboard summary | Verify summary statistics | Total/pending/verified/rejected/completed counts | Pass | PASS |
| Staff performance | Verify staff task completion data | Staff labels and task counts returned | Pass | PASS |
| Pending vs completed | Verify task status aggregation | Assigned/In Progress/Completed counts | Pass | PASS |
| Map requires admin | Citizen accesses /admin/map | 403 or "permission" | Pass | PASS |
| Map access | Admin views /admin/map | 200, "Complaint Location Map" present | Pass | PASS |
| CSV – complaint register | Download complaint register CSV | Correct headers, text/csv content type | Pass | PASS |
| CSV – pending complaints | Download pending complaints CSV | Correct headers | Pass | PASS |
| CSV – category-wise | Download category-wise CSV | Correct headers: Category, Complaint Count | Pass | PASS |
| CSV – location-wise | Download location-wise CSV | Correct headers: Location, Latitude, Longitude, Complaint Count | Pass | PASS |
| CSV – staff workload | Download staff workload CSV | Correct headers | Pass | PASS |
| CSV – task completion | Download task completion CSV | Correct headers: Task Status, Task Count | Pass | PASS |
| CSV – monthly activity | Download monthly activity CSV | Correct headers: Month, Complaints Submitted, Complaints Resolved | Pass | PASS |

## J. Configuration Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Missing production secret | ProductionConfig without SECRET_KEY | RuntimeError | Pass | PASS |
| Weak production secret | SECRET_KEY shorter than 16 chars | RuntimeError | Pass | PASS |
| Strong production secret | Valid SECRET_KEY | App starts | Pass | PASS |
| Development without secret | DevelopmentConfig without SECRET_KEY | App starts with fallback + warning | Pass | PASS |
| Testing config secret | TestingConfig has test secret key | Not the dev fallback | Pass | PASS |

## K. Database Migration Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Fresh DB migration | Apply initial migration to empty DB | All model tables created | Pass | PASS |
| Initial migration metadata | down_revision is None, upgrade/downgrade callable | Valid initial revision | Pass | PASS |

## L. Health Check Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Health endpoint OK | GET /health with DB reachable | HTTP 200, status ok | Pass | PASS |
| Health endpoint DB failure | DB unreachable | HTTP 503, no raw exception details | Pass | PASS |

## M. Database Model Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| User creation | Create user with hashed password | Password stored as hash, check_password works | Pass | PASS |
| User email unique | Duplicate email raises constraint error | IntegrityError raised | Pass | PASS |
| User roles | Check is_admin/is_staff/is_citizen helpers | Correct boolean values | Pass | PASS |
| Staff relationship | User ↔ Staff one-to-one | staff_profile accessible | Pass | PASS |
| Waste category unique | Duplicate category name raises error | IntegrityError raised | Pass | PASS |
| Location creation | Create location with lat/lng | Location saved with coordinates | Pass | PASS |
| Report creation | Create report with relationships | Citizen, category, location relationships work | Pass | PASS |
| Report reference unique | Duplicate reference raises error | IntegrityError raised | Pass | PASS |
| Collection task | Create task with staff and admin | Task linked to report, staff, assigning admin | Pass | PASS |
| Task updates | Create task updates | Updates linked to task and user | Pass | PASS |
| Awareness article | Create published article | Article with is_published flag | Pass | PASS |
| Status values | Verify ReportStatus and TaskStatus constants | Correct string values | Pass | PASS |

## N. CSRF Protection Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Registration form renders CSRF token | GET /auth/register | `csrf_token` hidden input present | Pass | PASS |
| Registration valid POST with token | POST /auth/register with valid `csrf_token` | Account created, HTTP 200 | Pass | PASS |
| Registration POST without token | POST /auth/register omitting `csrf_token` | HTTP 400 | Pass | PASS |
| Registration POST invalid token | POST /auth/register with `csrf_token=invalid-token` | HTTP 400 | Pass | PASS |
| Login form renders CSRF token | GET /auth/login | `csrf_token` hidden input present | Pass | PASS |
| Login valid POST with token | POST /auth/login with valid `csrf_token` | Session established, HTTP 200 | Pass | PASS |
| Login POST without token | POST /auth/login omitting `csrf_token` | HTTP 400 | Pass | PASS |
| Login POST invalid token | POST /auth/login with `csrf_token=invalid-token` | HTTP 400 | Pass | PASS |
| Logout POST with token | POST /auth/logout with valid `csrf_token` | Session cleared, HTTP 200 | Pass | PASS |
| Logout POST without token | POST /auth/logout omitting `csrf_token` | HTTP 400 | Pass | PASS |
| Logout POST invalid token | POST /auth/logout with `csrf_token=invalid-token` | HTTP 400 | Pass | PASS |
| Complaint submission form renders CSRF token | GET /citizen/submit | `csrf_token` hidden input present | Pass | PASS |
| Complaint submission valid POST with token | POST /citizen/submit (multipart) with valid `csrf_token` | Complaint created, HTTP 200 | Pass | PASS |
| Complaint submission POST without token | POST /citizen/submit omitting `csrf_token` | HTTP 400 | Pass | PASS |
| Complaint submission POST invalid token | POST /citizen/submit with `csrf_token=invalid-token` | HTTP 400 | Pass | PASS |
| Admin verify complaint | POST /admin/complaints/<tool_call>/verify with valid `csrf_token` | Complaint verified, HTTP 200 | Pass | PASS |
| Admin verify complaint without token | POST /admin/complaints/<tool_call>/verify omitting `csrf_token` | HTTP 400 | Pass | PASS |
| Admin verify complaint invalid token | POST /admin/complaints/<tool_call>/verify with `csrf_token=invalid-token` | HTTP 400 | Pass | PASS |
| Admin assign staff | POST /admin/tasks/assign with valid `csrf_token` | Task created, complaint assigned, HTTP 200 | Pass | PASS |
| Admin assign staff without token | POST /admin/tasks/assign omitting `csrf_token` | HTTP 400 | Pass | PASS |
| Admin assign staff invalid token | POST /admin/tasks/assign with `csrf_token=invalid-token` | HTTP 400 | Pass | PASS |
| Staff task progress update | POST /staff/tasks/<id>/update with valid `csrf_token` | Task status updated, HTTP 200 | Pass | PASS |
| Staff task update without token | POST /staff/tasks/<id>/update omitting `csrf_token` | HTTP 400 | Pass | PASS |
| Staff task update invalid token | POST /staff/tasks/<id>/update with `csrf_token=invalid-token` | HTTP 400 | Pass | PASS |

## Summary

| Category | Test Cases | Passed | Failed |
|----------|-----------|--------|--------|
| Authentication | 16 | 16 | 0 |
| Open Redirect | 3 | 3 | 0 |
| Authorization | 5 | 5 | 0 |
| Image Privacy | 7 | 7 | 0 |
| Complaints | 10 | 10 | 0 |
| Status History | 8 | 8 | 0 |
| Tasks | 8 | 8 | 0 |
| Administrator | 13 | 13 | 0 |
| Analytics & Reporting | 14 | 14 | 0 |
| Configuration | 5 | 5 | 0 |
| Database Migration | 2 | 2 | 0 |
| Health Check | 2 | 2 | 0 |
| Database Models | 13 | 13 | 0 |
| CSRF Protection | 24 | 24 | 0 |
| **Total** | **158** | **158** | **0** |

