# Requirements Traceability Matrix – EcoTrack

Maps each Functional Requirement (FR) and Non-Functional Requirement (NFR) from the synopsis to the responsible application component/module and verification approach. This document is used to confirm that every requirement is covered by design, implementation and tests.

## Traceability: Functional Requirements

| FR ID | Requirement (summary) | Responsible Component | Design Artifact | Verification (test) |
|-------|----------------------|----------------------|-----------------|---------------------|
| FR1 | User registration and login; admin accounts provisioned securely | `app/auth` (register, login), `app/models.User` | User entity; registration/login flows | Auth tests: registration, login success/failure, logout |
| FR2 | Role-based access (Citizen / Administrator / Staff) | `app/decorators.roles_required`, route guards | Role-based access decorators | Role-based access tests: citizen denied admin routes |
| FR3 | Profile management | `app/auth.profile`, `app/models.User` | Profile form/routes | Profile update test |
| FR4 | Waste report submission (category, description, date, location) | `app/citizen` report module, `Report` entity | Report submission form + service | Report submission tests (planned Phase 4) |
| FR5 | Photograph upload (type & size validation, 5 MB limit) | Upload service, `Report.image_path` | File-upload validation rules | Image upload tests (planned Phase 4) |
| FR6 | Report acknowledgement + unique reference | `Report.reference`, acknowledgement page | Unique reference generation | Acknowledgement tests (planned Phase 4) |
| FR7 | Complaint review: verify / reject with reason / update status | `app/admin` review module, `Report.status` | Admin review workflow | Review/reject tests (planned Phase 5) |
| FR8 | Task assignment to staff with target date | `app/admin` assignment module, `CollectionTask` | Assignment form + service | Assignment tests (planned Phase 5) |
| FR9 | Staff task progress: progress, completion status, remarks | `app/staff` task module, `TaskUpdate`, `CollectionTask.task_status` | Staff task update form | Task progress tests (planned Phase 5) |
| FR10 | Citizen tracking: status & history of own reports | `app/citizen` tracking module | Citizen report list + history | Tracking tests (planned Phase 5) |
| FR11 | Dashboard & reports: counts/summaries by status, category, date, staff | `app/admin.dashboard`, Chart.js | Dashboard queries + charts | Dashboard analytics tests (planned Phase 5) |
| FR12 | Awareness content (segregation, recycling, disposal) | `app/main` awareness module, `AwarenessArticle` | Articles list/detail pages | Awareness content tests (planned Phase 5) |

## Traceability: Non-Functional Requirements

| NFR ID | Requirement | Implementation Approach | Verification |
|--------|-------------|------------------------|--------------|
| Perf-1 | Pages/DB ops respond within ~3 seconds | Efficient SQLAlchemy queries, indexed fields | Manual performance check / load sample |
| Use-1 | Clear labels, validation messages, mobile-usable | Bootstrap 5 responsive forms, WTForms messages | UI review / manual testing |
| Sec-1 | Salted password hashes | `werkzeug.security.generate_password_hash` | Auth tests confirm password not stored plain |
| Sec-2 | Role checks + server-side validation on protected routes | `roles_required` decorator on every protected route | Role-based access tests |
| File-1 | Image restricted by extension, content type, size (5 MB) | Upload validation service, `MAX_CONTENT_LENGTH` | Image upload tests |
| Rel-1 | Validate fields & relationships before saving; clear errors | WTForms server-side validation + flash messages | Form validation tests |
| Maint-1 | Separate routes, models, templates, config | Flask blueprints, factory pattern, `config.py` | Code review |
| Scal-1 | Add staff/locations/reports without redesign | Relational FK model, modular blueprints | Design review |
| Comp-1 | Responsive desktop + mobile browsers | Bootstrap 5 grid, CDN assets | Manual responsive check |

## Traceability: Diagrams (University Guidelines)

| Guideline Diagram | File | Location |
|-------------------|------|----------|
| Level 0 DFD | `level0_dfd.mmd` | `docs/diagrams/` |
| Level 1 DFD | `level1_dfd.mmd` | `docs/diagrams/` |
| Level 2 DFD (complaint submission) | `level2_dfd.mmd` | `docs/diagrams/` |
| ER Diagram | `er_diagram.mmd` | `docs/diagrams/` |
| Class Diagram | `class_diagram.mmd` | `docs/diagrams/` |
| Use Case Diagram | `use_case_diagram.mmd` | `docs/diagrams/` |
| Activity Diagram (citizen complaint submission) | `activity_citizen_complaint.mmd` | `docs/diagrams/` |
| Activity Diagram (complaint assignment) | `activity_complaint_assignment.mmd` | `docs/diagrams/` |
| Sequence Diagram (complaint submission) | `seq_complaint_submission.mmd` | `docs/diagrams/` |
| Sequence Diagram (task completion) | `seq_task_completion.mmd` | `docs/diagrams/` |
