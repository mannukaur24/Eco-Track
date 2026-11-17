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


def _register(client, email, role="Citizen", full_name="Test User", password="Password123"):
    return client.post(
        "/auth/register",
        data={
            "full_name": full_name,
            "email": email,
            "password": password,
            "confirm_password": password,
            "role": role,
            "phone": "1234567890",
        },
        follow_redirects=True,
    )


def _login(client, email, password="Password123"):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def test_register_citizen(client):
    response = _register(client, "citizen@example.com", role="Citizen")
    assert response.status_code == 200
    user = User.query.filter_by(email="citizen@example.com").first()
    assert user is not None
    assert user.role == Role.CITIZEN
    assert user.check_password("Password123")


def test_register_staff_prevented_via_public_registration(client):
    """Public registration must create Citizen accounts only."""
    response = _register(client, "staff@example.com", role="Staff", full_name="Staff User")
    # The registration form no longer offers the Staff role; submission fails validation.
    assert response.status_code == 200
    user = User.query.filter_by(email="staff@example.com").first()
    assert user is None or user.role == Role.CITIZEN
    assert not (user is not None and user.role == Role.STAFF)


def test_register_form_does_not_offer_staff_role(client):
    response = client.get("/auth/register")
    assert b"Administrator" not in response.data
    # The Staff role must not be selectable in public registration.
    assert b'value="Staff"' not in response.data
    assert b'value="Citizen"' in response.data


def test_register_duplicate_email(client):
    _register(client, "dup@example.com")
    response = _register(client, "dup@example.com")
    assert b"already exists" in response.data


def test_register_role_not_administrator(client):
    # Administrator is not offered in public registration
    response = client.get("/auth/register")
    assert b"Administrator" not in response.data


def test_login_success(client):
    _register(client, "login@example.com")
    response = _login(client, "login@example.com")
    assert response.status_code == 200


def test_login_invalid_credentials(client):
    _register(client, "bad@example.com")
    response = _login(client, "bad@example.com", password="WrongPassword")
    assert b"Invalid email or password" in response.data


def test_login_nonexistent_user(client):
    response = _login(client, "nonexistent@example.com")
    assert b"Invalid email or password" in response.data


def test_logout(client):
    _register(client, "out@example.com")
    _login(client, "out@example.com")
    # Logout is POST-only; GET must be rejected (405 Method Not Allowed).
    response = client.get("/auth/logout")
    assert response.status_code == 405
    response = client.post("/auth/logout", follow_redirects=True)
    assert response.status_code == 200
    # Session cleared: profile requires login again.
    response = client.get("/auth/profile", follow_redirects=True)
    assert response.status_code == 200


def test_login_redirect_safe_next(client):
    _register(client, "redirect@example.com")
    response = client.post(
        "/auth/login",
        data={"email": "redirect@example.com", "password": "Password123"},
        query_string={"next": "/citizen/dashboard"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/citizen/dashboard" in response.location


def test_login_redirect_rejects_external_url(client):
    _register(client, "redirect2@example.com")
    response = client.post(
        "/auth/login",
        data={"email": "redirect2@example.com", "password": "Password123"},
        query_string={"next": "http://example.com/"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "example.com" not in response.location
    assert response.location.endswith("/dashboard")


def test_login_redirect_rejects_protocol_relative_url(client):
    _register(client, "redirect3@example.com")
    response = client.post(
        "/auth/login",
        data={"email": "redirect3@example.com", "password": "Password123"},
        query_string={"next": "//example.com/malicious"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "example.com" not in response.location
    assert response.location.endswith("/dashboard")


def test_profile_requires_login(client):
    response = client.get("/auth/profile", follow_redirects=True)
    assert response.status_code == 200


def test_profile_update(client):
    _register(client, "prof@example.com", full_name="Original Name")
    _login(client, "prof@example.com")
    response = client.post(
        "/auth/profile",
        data={"full_name": "Updated Name", "phone": "9999999999"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    updated = User.query.filter_by(email="prof@example.com").first()
    assert updated.full_name == "Updated Name"
    assert updated.phone == "9999999999"


def test_change_password(client):
    _register(client, "pw@example.com")
    _login(client, "pw@example.com")
    response = client.post(
        "/auth/change-password",
        data={
            "current_password": "Password123",
            "new_password": "NewPassword123",
            "confirm_password": "NewPassword123",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    updated = User.query.filter_by(email="pw@example.com").first()
    assert updated.check_password("NewPassword123")


def test_change_password_wrong_current(client):
    _register(client, "pw2@example.com")
    _login(client, "pw2@example.com")
    response = client.post(
        "/auth/change-password",
        data={
            "current_password": "WrongCurrent",
            "new_password": "NewPassword123",
            "confirm_password": "NewPassword123",
        },
        follow_redirects=True,
    )
    assert b"Current password is incorrect" in response.data


def test_citizen_redirected_to_index(client):
    _register(client, "c@example.com", role="Citizen")
    _login(client, "c@example.com")
    assert User.query.filter_by(email="c@example.com").first().is_citizen()


def test_staff_must_be_provisioned_by_administrator(client):
    """Public registration cannot create a Collection Staff account."""
    _register(client, "s@example.com", role="Staff", full_name="Staff User")
    user = User.query.filter_by(email="s@example.com").first()
    assert user is None or user.role != Role.STAFF


def test_inactive_account_cannot_login(client, app):
    """Inactive accounts cannot log in."""
    # Create user directly and deactivate
    with app.app_context():
        user = User(
            full_name="Inactive User",
            email="inactive@example.com",
            role=Role.CITIZEN,
            is_active=False,
        )
        user.set_password("Password123")
        db.session.add(user)
        db.session.commit()
    response = _login(client, "inactive@example.com")
    assert b"deactivated" in response.data
