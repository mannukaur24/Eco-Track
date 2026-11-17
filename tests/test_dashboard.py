"""Dashboard redirection tests for all user roles."""

import pytest
from app import create_app
from app.extensions import db
from app.models.user import User, Role


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _register(client, email, full_name="Test User", password="Password123"):
    return client.post(
        "/auth/register",
        data={
            "full_name": full_name,
            "email": email,
            "password": password,
            "confirm_password": password,
            "role": "Citizen",
            "phone": "1234567890",
        },
        follow_redirects=True,
    )


def _login(client, email, password="Password123"):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def _make_user(app, email, role, full_name, password="Password123", is_active=True):
    with app.app_context():
        user = User(
            full_name=full_name,
            email=email,
            role=role,
            is_active=is_active,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user


def _dashboard_location(client):
    response = client.get("/dashboard", follow_redirects=False)
    return response


# ---------------------------------------------------------------------------
# 1. Dashboard while logged out
# ---------------------------------------------------------------------------


def test_dashboard_logged_out_redirects_to_login(client):
    response = _dashboard_location(client)
    assert response.status_code == 302
    assert "/auth/login" in response.location
    assert "next=" in response.location  # next param preserved


# ---------------------------------------------------------------------------
# 2. Dashboard redirection after login (default, no next)
# ---------------------------------------------------------------------------


def test_login_redirects_to_dashboard_by_default(client, app):
    _register(client, "citizen@example.com", "Citizen User")
    response = _login(client, "citizen@example.com")
    assert response.status_code == 302
    assert response.location.endswith("/dashboard")


# ---------------------------------------------------------------------------
# 3. Role-based dashboard destinations
# ---------------------------------------------------------------------------


def test_dashboard_citizen_destination(client, app):
    _register(client, "citizen@example.com", "Citizen User")
    _login(client, "citizen@example.com")
    response = _dashboard_location(client)
    assert response.status_code == 302
    assert response.location.endswith("/citizen/dashboard")


def test_dashboard_citizen_destination_renders(client):
    _register(client, "citizen2@example.com", "Citizen Two")
    _login(client, "citizen2@example.com")
    response = client.get("/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"Citizen Dashboard" in response.data


def test_dashboard_administrator_destination(client, app):
    _make_user(app, "admin@example.com", Role.ADMINISTRATOR, "Admin User")
    client.post("/auth/logout", follow_redirects=True)
    _login(client, "admin@example.com")
    response = _dashboard_location(client)
    assert response.status_code == 302
    assert response.location.endswith("/admin/dashboard")


def test_dashboard_administrator_destination_renders(client, app):
    _make_user(app, "admin2@example.com", Role.ADMINISTRATOR, "Admin Two")
    client.post("/auth/logout", follow_redirects=True)
    _login(client, "admin2@example.com")
    response = client.get("/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_dashboard_staff_destination(client, app):
    _make_user(app, "staff@example.com", Role.STAFF, "Staff User")
    client.post("/auth/logout", follow_redirects=True)
    _login(client, "staff@example.com")
    response = _dashboard_location(client)
    assert response.status_code == 302
    assert response.location.endswith("/staff/dashboard")


def test_dashboard_staff_destination_renders(client, app):
    _make_user(app, "staff2@example.com", Role.STAFF, "Staff Two")
    client.post("/auth/logout", follow_redirects=True)
    _login(client, "staff2@example.com")
    response = client.get("/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"Staff Dashboard" in response.data


# ---------------------------------------------------------------------------
# 4. Invalid / unknown role handling
# ---------------------------------------------------------------------------


def test_dashboard_unknown_role_forbidden(client, app):
    with app.app_context():
        user = User(
            full_name="Unknown Role",
            email="unknown@example.com",
            role="UnknownRole",
            is_active=True,
        )
        user.set_password("Password123")
        db.session.add(user)
        db.session.commit()
    _login(client, "unknown@example.com")
    response = _dashboard_location(client)
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# 5. Inactive user handling
# ---------------------------------------------------------------------------


def test_inactive_user_cannot_login(client, app):
    _make_user(app, "inactive@example.com", Role.CITIZEN, "Inactive User", is_active=False)
    response = _login(client, "inactive@example.com")
    assert response.status_code == 302  # login redirects back to login page on failure
    assert b"deactivated" in client.get(response.location, follow_redirects=True).data


def test_dashboard_requires_active_account(client, app):
    _make_user(app, "inactive2@example.com", Role.CITIZEN, "Inactive Two", is_active=False)
    # Inactive users cannot authenticate, so dashboard is unreachable.
    response = _login(client, "inactive2@example.com")
    assert response.status_code == 302
    assert b"deactivated" in client.get(response.location, follow_redirects=True).data


# ---------------------------------------------------------------------------
# 6. Unauthorized dashboard access (citizen accessing admin dashboard directly)
# ---------------------------------------------------------------------------


def test_citizen_cannot_access_admin_dashboard(client, app):
    _register(client, "citizen3@example.com", "Citizen Three")
    _login(client, "citizen3@example.com")
    response = client.get("/admin/dashboard", follow_redirects=False)
    assert response.status_code == 403 or b"permission" in response.data.lower()


def test_staff_cannot_access_admin_dashboard(client, app):
    _make_user(app, "staff3@example.com", Role.STAFF, "Staff Three")
    _login(client, "staff3@example.com")
    response = client.get("/admin/dashboard", follow_redirects=False)
    assert response.status_code == 403 or b"permission" in response.data.lower()
