# User Roles and Permissions – EcoTrack

## 1. Roles Overview

EcoTrack defines three user roles, each with a distinct set of permissions:

| Role | Typical user | Primary responsibilities |
|------|--------------|--------------------------|
| Citizen | Resident / community member | Report waste issues, upload evidence, track own reports |
| Administrator | Municipal / system administrator | Review reports, assign tasks, manage dashboards and awareness content |
| Collection Staff | Waste collection worker | View assigned tasks, update progress and completion status |

## 2. Role Provisioning

Per the synopsis (FR1), citizen and staff accounts may register themselves. **Administrator accounts are not open to public registration** — they are provisioned securely (e.g. via a database seed script or direct database insert) to prevent privilege escalation. This is a proposed design decision documented in `docs/IMPLEMENTATION_PLAN.md`.

## 3. Permissions Matrix

| Permission | Citizen | Administrator | Collection Staff |
|------------|---------|---------------|------------------|
| Register account | ✅ | ❌ (provisioned) | ✅ |
| Log in / log out | ✅ | ✅ | ✅ |
| View/update own profile | ✅ | ✅ | ✅ |
| Submit waste report | ✅ | ❌ | ❌ |
| Upload report photograph | ✅ | ❌ | ❌ |
| View own reports & status | ✅ | ❌ | ❌ |
| View all reports (queue) | ❌ | ✅ | ❌ |
| Verify / reject report | ❌ | ✅ | ❌ |
| Update report status | ❌ | ✅ | ❌ |
| Assign collection task | ❌ | ✅ | ❌ |
| View assigned tasks | ❌ | ❌ | ✅ |
| Update task progress / completion | ❌ | ❌ | ✅ (own tasks only) |
| View dashboard & analytics | ❌ | ✅ | ❌ |
| Browse awareness articles | ✅ | ✅ | ✅ |
| Maintain awareness articles | ❌ | ✅ | ❌ |
| Access other users' records | ❌ | ❌ | ❌ |

## 4. Access Control Rules

1. **Server-side enforcement** – Role checks are applied on every protected route via `app/decorators.roles_required`, not only hidden in the UI.
2. **Ownership restriction** –
   - Citizens may view/update only their own reports (`Reports.user_id == current_user.id`).
   - Staff may view/update only tasks assigned to them (`CollectionTasks.staff_id == current_user.id`).
   - No user may access another user's records.
3. **Authentication required** – All protected routes require a valid session; unauthenticated requests redirect to `/auth/login`.
4. **Authorization failure** – An authenticated user attempting an unauthorized action receives an HTTP 403 with a flash message.
5. **Admin scope** – Administrators may perform all management functions but cannot access another citizen's private data beyond what the report workflow exposes.

## 5. Role-Based Navigation

The base template renders navigation conditionally:
- **Unauthenticated**: Home, Log in, Register.
- **Authenticated**: Home, Profile (dropdown), Log out; the user's name and role are shown.
- After login, users are redirected to their role-specific dashboard:
  - Citizen → `/citizen/dashboard`
  - Administrator → `/admin/dashboard`
  - Collection Staff → `/staff/dashboard`

## 6. Role Constants

Defined in `app/models.py`:

```python
class Role:
    CITIZEN = "Citizen"
    ADMINISTRATOR = "Administrator"
    STAFF = "Staff"
    choices = [(CITIZEN, "Citizen"), (ADMINISTRATOR, "Administrator"), (STAFF, "Collection Staff")]
```

The `User.role` column stores one of these values. Helper methods `is_admin()`, `is_staff()`, `is_citizen()` provide readable role checks.

## 7. Registration Role Constraints

The public registration form offers only the `Citizen` role. The `Administrator` and
`Collection Staff` roles are excluded from public registration and are provisioned
separately by an administrator (see Section 2), which prevents privilege escalation
via public registration. Every administrator-created staff account receives a valid
`Staff` profile. This satisfies FR1 ("administrator accounts shall be provisioned
securely").
