# Test Cases – EcoTrack

Actual test results from the latest test suite execution. All 77 tests pass.

## A. Authentication Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Valid registration | Register new citizen with valid data | Account created, flash "Account created successfully" | Pass | PASS |
| Duplicate email | Register with existing email | Flash "already exists" | Pass | PASS |
| Registration role restriction | Administrator not available in public registration form | "Administrator" not in page | Pass | PASS |
| Valid login | Login with correct credentials | Redirect, flash "Welcome back" | Pass | PASS |
| Invalid login (wrong password) | Login with incorrect password | Flash "Invalid email or password" | Pass | PASS |
| Invalid login (nonexistent user) | Login with unregistered email | Flash "Invalid email or password" | Pass | PASS |
| Logout | Log out authenticated user | Redirect, session cleared | Pass | PASS |
| Profile requires login | Access /auth/profile without auth | Redirect to login | Pass | PASS |
| Profile update | Update full name and phone | Profile updated, flash success | Pass | PASS |
| Change password | Change password with valid current password | Password changed, flash success | Pass | PASS |
| Change password wrong current | Change password with incorrect current password | Flash "Current password is incorrect" | Pass | PASS |
| Citizen redirected after login | Citizen logs in | User role is Citizen | Pass | PASS |
| Staff redirected after login | Staff logs in | User role is Staff | Pass | PASS |
| Inactive account cannot login | Login with deactivated account | Flash "deactivated" | Pass | PASS |

## B. Authorization Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Citizen route protection | Citizen accesses /admin/dashboard | 403 or "permission" message | Pass | PASS |
| Staff route protection | Staff accesses /admin/dashboard | 403 or "permission" message | Pass | PASS |
| Admin cannot access staff | Admin accesses /staff/dashboard | 403 or "permission" message | Pass | PASS |
| Cross-user complaint access | Citizen A views Citizen B's complaint | "not found or you do not have access" | Pass | PASS |
| Cross-staff task access | Staff A views Staff B's task | "not found or not assigned to you" | Pass | PASS |

## C. Complaint Tests

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

## D. Task Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Staff task visibility | Staff sees only own tasks | Other staff's tasks not visible | Pass | PASS |
| Unauthorized task access | Staff views another staff's task | "not found or not assigned to you" | Pass | PASS |
| Progress update | Update task Assigned → In Progress | Task status updated, TaskUpdate recorded | Pass | PASS |
| Completion workflow | Update task → Completed, verify complaint sync | Task completed_at set, complaint status = Completed | Pass | PASS |
| Invalid transition | Update Completed → In Progress | Flash "Cannot move task" | Pass | PASS |
| Task history | View task updates/history | Updates listed with remarks | Pass | PASS |
| Staff dashboard | View staff dashboard | "Collection Staff Dashboard" heading present | Pass | PASS |

## E. Administrator Tests

| Test Case | Description | Expected | Actual | Status |
|-----------|-------------|----------|--------|--------|
| Admin dashboard access | Admin views /admin/dashboard | 200, "Dashboard" present | Pass | PASS |
| Admin dashboard stats | Dashboard shows complaint/task stats | Stats computed from DB, not hardcoded | Pass | PASS |
| Admin view complaints | Admin views /admin/complaints | 200 | Pass | PASS |
| Verify complaint | Admin verifies pending complaint | Complaint status = Verified | Pass | PASS |
| Reject with reason | Admin rejects with mandatory reason | Complaint status = Rejected, reason stored | Pass | PASS |
| Reject without reason | Admin rejects with empty reason | Flash "rejection reason is required" | Pass | PASS |
| Assign task | Admin assigns verified complaint to staff | CollectionTask created, complaint status = Assigned | Pass | PASS |
| Add staff | Admin creates new staff account | Staff created, flash "Staff member added" | Pass | PASS |
| Duplicate staff email | Add staff with existing email | Flash "already exists" | Pass | PASS |
| Toggle staff active | Admin deactivates/reactivates staff | is_active toggled | Pass | PASS |
| Category management | Add, edit, delete categories | Categories managed correctly | Pass | PASS |
| Duplicate category | Add category with existing name | Flash "already exists" | Pass | PASS |
| Awareness management | Create, edit, publish/unpublish articles | Articles managed correctly | Pass | PASS |

## F. Analytics & Reporting Tests

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

## G. Database Model Tests

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

## Summary

| Category | Test Cases | Passed | Failed |
|----------|-----------|--------|--------|
| Authentication | 14 | 14 | 0 |
| Authorization | 5 | 5 | 0 |
| Complaints | 10 | 10 | 0 |
| Tasks | 6 | 6 | 0 |
| Administrator | 13 | 13 | 0 |
| Analytics & Reporting | 14 | 14 | 0 |
| Database Models | 11 | 11 | 0 |
| **Total** | **73** | **73** | **0** |
