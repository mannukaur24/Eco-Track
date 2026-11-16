# Application Architecture – EcoTrack

## 1. Architectural Style

Layered, modular monolithic web application built with Python Flask. The application uses the **application factory pattern** and **Flask Blueprints** to separate concerns and keep the codebase maintainable and testable.

Layers:
- **Presentation layer** – Jinja2 HTML templates with Bootstrap 5, Chart.js and Leaflet.js (CDN).
- **Controller / routing layer** – Flask blueprints (auth, citizen, admin, staff, main).
- **Business logic layer** – service-style functions in route modules and decorators.
- **Data access layer** – Flask-SQLAlchemy ORM over MySQL 8 (PyMySQL driver).
- **Configuration layer** – environment-variable-driven config classes.

## 2. Application Factory

`app/__init__.py` exports `create_app(config_name)`. It:
1. Creates the Flask instance and loads configuration from `app/config.py`.
2. Initializes extensions: `db`, `migrate`, `login_manager`, `csrf`.
3. Registers the Flask-Login user loader.
4. Registers blueprints: `auth`, `main`, `citizen`, `admin`, `staff`.
5. Returns the configured app.

Entry point: `run.py` calls `create_app()` and runs the development server.

## 3. Blueprint Structure

| Blueprint | URL Prefix | Responsibility |
|-----------|------------|----------------|
| `auth` | `/auth` | Registration, login, logout, profile |
| `main` | `/` | Home page, dashboard routing, awareness listing |
| `citizen` | `/citizen` | Citizen dashboard, report submission, tracking |
| `admin` | `/admin` | Admin dashboard, report review, task assignment |
| `staff` | `/staff` | Staff dashboard, task progress updates |

Each blueprint package contains `__init__.py` (blueprint object + route import) and `routes.py` (view functions). `auth` additionally has `forms.py` (WTForms).

## 4. Configuration

`app/config.py` defines `Config`, `DevelopmentConfig`, `TestingConfig`, `ProductionConfig`. Settings are sourced from environment variables via `python-dotenv`:
- `SECRET_KEY`, `DATABASE_URL` / individual `DB_*` variables.
- `MAX_CONTENT_LENGTH` (default 5 MB).
- `UPLOAD_FOLDER`.
- Session cookie security flags (`HttpOnly`, `SameSite=Lax`, `Secure` in production).

A `.env.example` file documents required variables; real secrets live in `.env` (gitignored) and are never hardcoded.

## 5. Extensions

`app/extensions.py` instantiates and configures:
- `SQLAlchemy` – ORM and session.
- `Migrate` – database migrations (Flask-Migrate / Alembic).
- `LoginManager` – session-based authentication; login view set to `auth.login`; session protection `strong`.
- `CSRFProtect` – CSRF protection for all state-changing forms.

## 6. Models

`app/models.py` defines all domain entities with SQLAlchemy:
- `User` (with `UserMixin` for Flask-Login), `Staff`, `WasteCategory`, `Location`, `Report`, `CollectionTask`, `TaskUpdate`, `AwarenessArticle`.
- Constants: `Role`, `ReportStatus`, `TaskStatus`.
- Password hashing via `werkzeug.security`.

Relationships and constraints follow `docs/DATABASE_DESIGN.md`.

## 7. Authorization

`app/decorators.py` provides role-based access control enforced on the server for every protected route:
- `roles_required(*roles)` – generic decorator.
- `citizen_required`, `administrator_required`, `staff_required`, `admin_or_staff_required`.

Decorators check `current_user.role`; non-authenticated users are redirected to login; unauthorized authenticated users receive a 403.

## 8. Security Controls

| Control | Implementation |
|---------|----------------|
| Password storage | Salted hash via Werkzeug (`generate_password_hash` / `check_password_hash`) |
| Session auth | Flask-Login; session cookies HttpOnly, SameSite=Lax; Secure in production |
| CSRF | Flask-WTF `CSRFProtect` on all POST/PUT/DELETE forms |
| Input validation | WTForms server-side validation on all forms |
| File upload | Extension + content-type + size (5 MB) validation; server-generated safe filenames |
| Secrets | Environment variables (`.env`), never in source code |
| Access control | Server-side role checks on every protected route |
| Error handling | Flash messages shown on failure; no silent error swallowing |

## 9. Frontend

- Base template `templates/base.html` provides Bootstrap 5 navigation, flash-message area, role-aware user menu and footer.
- Role-specific templates under `templates/auth/`, `templates/citizen/`, `templates/admin/`, `templates/staff/`, `templates/main/`.
- Custom styles in `static/css/style.js`.
- Chart.js for dashboard visualizations; Leaflet.js + OpenStreetMap for location display.

### Analytics and Reporting Layer

The analytics and reporting module (`app/services/analytics_service.py`, `app/services/reports_service.py`, `app/routes/admin_analytics.py`) provides administrator-facing data insights:

- **AnalyticsService** – aggregated SQLAlchemy queries for seven Chart.js visualizations (complaints by category/status, monthly submissions/resolutions, staff performance, pending vs completed tasks, location-wise summaries) plus date-range filtering (7 days, 30 days, 3 months, custom).
- **ReportsService** – CSV export generators for seven report types (complaint register, pending complaints, category-wise, location-wise, staff workload, task completion, monthly activity).
- **Routes** – `/admin/analytics` (dashboard), `/admin/map` (Leaflet map), `/admin/reports/*` (CSV downloads). All secured with `@administrator_required`.
- Map templates display complaint markers with reference, category, status, and location popups; citizen PII is excluded. Missing coordinates are handled gracefully.

## 10. Testing

- Pytest with `pytest-flask`.
- `TestingConfig` uses in-memory SQLite; CSRF disabled for tests.
- `tests/conftest.py` provides app/client fixtures and seeded users.
- `tests/test_auth.py` covers registration, login, logout, profile and role-based access.

## 11. Deployment

- Development: `flask run` or `python run.py`.
- Production: Python-compatible hosting with HTTPS; `SECRET_KEY` and DB credentials via environment variables; `SESSION_COOKIE_SECURE` enabled.
- Database initialized via `flask db init`, `flask db migrate`, `flask db upgrade`.
- Uploaded files stored outside executable code paths where hosting permits.

## 12. Limitations (Academic Prototype)

- Not integrated with actual municipal authorities or live waste collection services.
- No AI waste classification, IoT bins, GPS vehicle tracking, reward system or mobile app.
- Local development database is MySQL 8; tests run on SQLite.
