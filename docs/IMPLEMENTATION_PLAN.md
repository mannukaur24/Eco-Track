# Implementation Plan – EcoTrack

This plan follows the eight-week schedule defined in the synopsis (Section 3.4). Each phase lists objectives, deliverables, and entry/exit criteria.

## Phase 1 – Requirement Analysis (Week 1)
**Objective:** Finalize problem definition, user roles and requirements list.
**Deliverables:**
- Problem statement and objectives
- Functional requirements FR1–FR12
- Non-functional requirements
- User roles and permissions matrix
**Exit criteria:** Requirements baseline approved; all FR/NFR documented.

## Phase 2 – System and Database Design (Week 2)
**Objective:** Architecture, wireframes, DFDs and ER design.
**Deliverables:**
- Application architecture (factory pattern, blueprints)
- ER diagram and data dictionary
- DFDs (Level 0, 1, 2)
- Class, use case, activity and sequence diagrams
- Wireframes for key pages
**Exit criteria:** Design reviewed; database schema finalized.

## Phase 3 – Frontend and Authentication (Week 3)
**Objective:** Responsive interface, login and role checks.
**Deliverables:**
- Base layout (Bootstrap 5) and navigation
- Register / login / logout / profile pages
- Role-based access decorators
- Role-specific landing redirects
**Exit criteria:** Auth workflow verified end-to-end; unauthorized access blocked.

## Phase 4 – Backend and Database Modules (Weeks 3–4)
**Objective:** Report, user, category and task operations.
**Deliverables:**
- SQLAlchemy models + migrations (all 8 entities)
- Citizen report submission with image upload (validated, 5 MB, safe filenames)
- Waste category and location reference data
- Unique report reference generation
**Exit criteria:** Citizens can submit and view own reports; file-upload security validated.

## Phase 5 – Integration (Week 5)
**Objective:** Connected citizen, administrator and staff workflows.
**Deliverables:**
- Administrator review: verify / reject with reason / update status
- Administrator task assignment (staff + due date)
- Staff task progress updates (status, remarks, completion)
- Citizen tracking of own reports
- Dashboard charts (Chart.js) and summary tables
- Awareness article listing
**Exit criteria:** Full end-to-end workflow verified across all three roles.

## Phase 6 – Testing and Security Checks (Week 6)
**Objective:** Test cases, resolved defects and validation checks.
**Deliverables:**
- Pytest suite covering FR workflows
- Role-based access tests (positive + negative)
- File-upload validation tests
- Input validation / CSRF tests
- Security review (no hardcoded secrets, hashed passwords)
**Exit criteria:** All tests pass; no critical defects.

## Phase 7 – Documentation (Week 7)
**Objective:** Project report, user guide and presentation material.
**Deliverables:**
- Final project report per BCA guidelines format
- User guide for each role
- This architecture document set
- Diagrams exported from Mermaid sources
**Exit criteria:** Documentation complete and consistent with implemented code.

## Phase 8 – Deployment and Viva Preparation (Week 8)
**Objective:** Demonstrable build, final review and viva preparation.
**Deliverables:**
- Deployable build with setup instructions (README)
- Database seed script (categories, default admin)
- Demo script covering all three roles
- Viva preparation notes
**Exit criteria:** Application demonstrable; build verified on clean environment.

---

## Assumptions and Proposed Decisions

Where the synopsis does not prescribe exact implementation details, the following decisions are proposed:

1. **Database:** MySQL 8 via PyMySQL driver; tests use in-memory SQLite (TestingConfig) for speed, with schema parity via SQLAlchemy models.
2. **Authentication:** Flask-Login session-based authentication; passwords hashed with Werkzeug (bcrypt method). Administrator accounts are provisioned via a seed script (not self-registered) to satisfy "administrator accounts shall be provisioned securely" (FR1).
3. **Roles:** Registration is open to Citizen and Collection Staff only. The Administrator role is created by seed/admin provisioning, not public registration, to prevent privilege escalation.
4. **Status transitions:**
   - Report: `Pending` → `Verified` → `Assigned` → `In Progress` → `Completed`; `Pending`/`Verified` → `Rejected` (terminal).
   - Task: `Pending` → `In Progress` → `Completed`; task becomes `Overdue` if `due_date` passes while not Completed.
5. **File uploads:** Stored under `app/static/uploads/` with server-generated safe filenames; validated by extension, detected content type and `MAX_CONTENT_LENGTH` (5 MB). Files are not served as executable content.
6. **CSRF:** Flask-WTF protects all state-changing forms; CSRF disabled only in TestingConfig for test convenience.
7. **No real municipal integration:** Per project limitations, no external authority, payment, AI, IoT, GPS or mobile integration is implemented or claimed.
8. **Environment:** Secrets and DB credentials loaded from `.env` via python-dotenv; never hardcoded.
