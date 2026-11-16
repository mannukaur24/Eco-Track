# Known Limitations – EcoTrack

## 1. Project Scope Limitations (by Design)

The following limitations are explicitly defined in the project synopsis and are **not** part of the initial release:

| Limitation | Reason |
|------------|--------|
| AI waste classification | Future scope, not in initial release |
| IoT smart bins | Future scope |
| Vehicle GPS tracking | Future scope |
| Reward systems | Future scope |
| Mobile applications | Future scope |
| Municipal authority integration | Academic prototype; not connected to live services |
| Live waste collection service | Academic prototype |

## 2. Technical Limitations

| Limitation | Details | Workaround / Mitigation |
|------------|---------|------------------------|
| No PDF export | Reports are CSV-only; PDF export not implemented | CSV files can be opened in Excel/Sheets and printed |
| MySQL 8 required locally | Development requires MySQL 8 installation and configuration | Tests use SQLite; production deploys to MySQL 8 |
| No email/SMS notifications | Status changes are not automatically notified to citizens/staff | Users must log in to check status |
| No real-time updates | Page refresh required to see latest status | Standard web application behavior |
| No file type conversion | Uploaded images stored as-is; no thumbnail generation | Images displayed at original resolution |
| Single-server deployment | No load balancing or clustering configured | Suitable for academic prototype scale |
| No API endpoints | Web application only; no REST API for external integration | All functionality accessed via browser |

## 3. Testing Limitations

| Limitation | Details |
|------------|---------|
| SQLite for tests | Tests run on SQLite, not MySQL 8; schema parity maintained via SQLAlchemy models and the committed migration |
| No browser automation | UI responsiveness verified via template inspection, not automated browser tests |
| No Chart.js rendering tests | Charts verified via code inspection (Chart.js config present, `responsive: true`) |
| No load/performance testing | Not performed; suitable for academic prototype scale |
| No HTTPS testing | Secure cookies require HTTPS; development and tests use HTTP |

## 4. Feature Limitations

| Limitation | Details |
|------------|---------|
| Citizens cannot edit/delete submitted complaints | Complaints can only be viewed and tracked; modification requires administrator intervention |
| Citizens cannot delete verified/assigned complaints | By design – maintains audit integrity |
| Staff cannot reassign tasks | Tasks are assigned by administrators only; staff can only update progress |
| No bulk operations | Reports and tasks managed individually |
| No advanced search | Search by complaint reference only (complaints) |
| No export filtering by date for CSV | Monthly activity report has month filter; other CSV exports are full exports |
| Status history coverage | `report_status_history` records transitions made after this change; records are not fabricated for complaints that predate the mechanism |

## 5. Deployment Limitations

| Limitation | Details |
|------------|---------|
| HTTPS required in production | Secure cookies only work over HTTPS; development uses HTTP |
| Environment variables required | `SECRET_KEY` and DB credentials must be set via `.env` |
| Production secret mandatory | The application refuses to start in production if `SECRET_KEY` is missing or shorter than 16 characters |
| Upload directory write access | Application needs write access to `instance/uploads/` |
| Database migrations | Flask-Migrate required for schema updates; not automatic. An initial migration is committed under `migrations/versions/` |
| Not claimed production-ready | The application is an academic prototype. Security hardening (penetration testing, WAF, MySQL 8 deployment validation, dependency auditing) is recommended before any production use handling sensitive municipal data |

## 6. Data Limitations

| Limitation | Details |
|------------|---------|
| No data retention policy | Complaints and tasks are retained indefinitely |
| No soft delete | Deleted records (categories, articles) are permanently removed |
| Audit log scope | Task updates record staff actions, and complaint status changes are audited, but other admin actions are not separately logged |
| Location data optional | Reports can be submitted without latitude/longitude; map markers only for reports with coordinates |

## 7. Documentation Limitations

| Limitation | Details |
|------------|---------|
| No screenshots | Documentation references UI but does not include screenshots |
| No video demo | No recorded demonstration of the application |
| No user manuals | Role-based user manuals not created (future scope) |

## 8. Future Scope Items

The following are planned for future releases (not part of this submission):

- AI-based waste classification from uploaded images
- IoT bin integration for smart waste monitoring
- GPS tracking for collection vehicles
- Reward/points system for citizens
- Mobile applications (Android/iOS)
- Email/SMS notifications for status changes
- PDF export for reports
- Real-time notifications via WebSockets
- Municipal authority API integration
- Advanced analytics with predictive insights
- Multi-language support
