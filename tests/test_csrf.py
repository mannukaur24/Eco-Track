"""CSRF-protected end-to-end tests for EcoTrack state-changing forms.

These tests run with CSRF protection enabled (WTF_CSRF_ENABLED=True) to prove
that every POST form renders and accepts a valid CSRF token, and rejects
missing or invalid tokens with HTTP 400. The shared TestingConfig disables
CSRF for test convenience, so this module overrides the flag on a dedicated
application fixture without weakening the production/test default.
"""

import re

import pytest
from app import create_app
from app.extensions import db
from app.models.user import User, Role, ReportStatus, TaskStatus
from app.models.report import Report
from app.models.waste_category import WasteCategory
from app.models.collection_task import CollectionTask
from app.models.staff import Staff
from werkzeug.datastructures import FileStorage
import io


@pytest.fixture
def app():
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = True
    with app.app_context():
        db.create_all()
        categories = [
            "Organic Waste",
            "Plastic Waste",
            "Paper Waste",
            "Glass Waste",
            "Metal Waste",
            "E-Waste",
            "Hazardous Waste",
            "General Waste",
        ]
        for name in categories:
            if not WasteCategory.query.filter_by(category_name=name).first():
                db.session.add(WasteCategory(category_name=name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _csrf_token(html):
    """Extract the rendered csrf_token hidden input value from form HTML."""
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return match.group(1) if match else None


def _token_from(client, url):
    response = client.get(url)
    assert response.status_code == 200, f"GET {url} returned {response.status_code}"
    return _csrf_token(response.data.decode("utf-8", errors="replace"))


def _assert_has_csrf_token(client, url):
    token = _token_from(client, url)
    assert token is not None, f"GET {url} form does not render a csrf_token hidden input"
    return token


def _register(client, email, full_name, role="Citizen", password="Password123"):
    token = _assert_has_csrf_token(client, "/auth/register")
    return client.post(
        "/auth/register",
        data={
            "csrf_token": token,
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
    token = _assert_has_csrf_token(client, "/auth/login")
    return client.post(
        "/auth/login",
        data={"csrf_token": token, "email": email, "password": password},
        follow_redirects=True,
    )


def _logout(client):
    token = _assert_has_csrf_token(client, "/")
    return client.post(
        "/auth/logout",
        data={"csrf_token": token},
        follow_redirects=True,
    )


def _make_image_file(name="test.png"):
    return FileStorage(
        stream=io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100),
        filename=name,
        content_type="image/png",
    )


def _make_admin(app, email="admin@example.com", full_name="Admin User"):
    with app.app_context():
        admin = User.query.filter_by(email=email).first()
        if admin is None:
            admin = User(
                full_name=full_name,
                email=email,
                role=Role.ADMINISTRATOR,
                is_active=True,
            )
            admin.set_password("AdminPass123")
            db.session.add(admin)
            db.session.commit()
    return admin


def _make_staff(app, email="staff@example.com", full_name="Staff Worker"):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(
                full_name=full_name,
                email=email,
                role=Role.STAFF,
                is_active=True,
            )
            user.set_password("StaffPass123")
            db.session.add(user)
            db.session.flush()
            db.session.add(Staff(user_id=user.id, availability="Mon-Fri", service_area="Zone A"))
            db.session.commit()
    return user


def _submit_complaint(client, email, full_name, reference_expect=True):
    _register(client, email, full_name)
    _login(client, email)
    token = _assert_has_csrf_token(client, "/citizen/submit")
    response = client.post(
        "/citizen/submit",
        data={
            "csrf_token": token,
            "category_id": "1",
            "description": "A pile of garbage has been here for weeks.",
            "address_text": "1 Sub Street",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "additional_info": "Near the bus stop.",
            "image": _make_image_file("photo.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Complaint submitted successfully" in response.data
    _logout(client)
    with client.application.app_context():
        user = User.query.filter_by(email=email).first()
        report = Report.query.filter_by(user_id=user.id).first()
        assert report is not None
    return report


# ---------------------------------------------------------------------------
# 1. Citizen registration
# ---------------------------------------------------------------------------


def test_csrf_register_get_contains_token(client):
    _assert_has_csrf_token(client, "/auth/register")


def test_csrf_register_valid_post_succeeds(client):
    response = _register(client, "reg@example.com", "Reg User")
    assert response.status_code == 200
    assert b"Account created successfully" in response.data
    assert User.query.filter_by(email="reg@example.com").first() is not None


def test_csrf_register_post_without_token_returns_400(client):
    response = client.post(
        "/auth/register",
        data={
            "full_name": "No Token",
            "email": "notoken@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
            "role": "Citizen",
            "phone": "1234567890",
        },
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_csrf_register_post_with_invalid_token_returns_400(client):
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": "invalid-token",
            "full_name": "Bad Token",
            "email": "badtoken@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
            "role": "Citizen",
            "phone": "1234567890",
        },
        follow_redirects=False,
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 2. Login
# ---------------------------------------------------------------------------


def test_csrf_login_get_contains_token(client):
    _register(client, "login@example.com", "Login User")
    _assert_has_csrf_token(client, "/auth/login")


def test_csrf_login_valid_post_succeeds(client):
    _register(client, "login@example.com", "Login User")
    response = _login(client, "login@example.com")
    assert response.status_code == 200
    assert b"Welcome back" in response.data


def test_csrf_login_post_without_token_returns_400(client):
    _register(client, "login2@example.com", "Login User 2")
    response = client.post(
        "/auth/login",
        data={"email": "login2@example.com", "password": "Password123"},
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_csrf_login_post_with_invalid_token_returns_400(client):
    _register(client, "login3@example.com", "Login User 3")
    response = client.post(
        "/auth/login",
        data={"csrf_token": "invalid-token", "email": "login3@example.com", "password": "Password123"},
        follow_redirects=False,
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 3. Logout
# ---------------------------------------------------------------------------


def test_csrf_logout_post_succeeds(client):
    _register(client, "out@example.com", "Out User")
    _login(client, "out@example.com")
    token = _assert_has_csrf_token(client, "/")
    response = client.post(
        "/auth/logout",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_csrf_logout_post_without_token_returns_400(client):
    _register(client, "out2@example.com", "Out User 2")
    _login(client, "out2@example.com")
    response = client.post("/auth/logout", follow_redirects=False)
    assert response.status_code == 400


def test_csrf_logout_post_with_invalid_token_returns_400(client):
    _register(client, "out3@example.com", "Out User 3")
    _login(client, "out3@example.com")
    response = client.post(
        "/auth/logout",
        data={"csrf_token": "invalid-token"},
        follow_redirects=False,
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 4. Complaint submission (multipart image upload)
# ---------------------------------------------------------------------------


def test_csrf_complaint_submit_get_contains_token(client):
    _register(client, "sub@example.com", "Sub User")
    _login(client, "sub@example.com")
    _assert_has_csrf_token(client, "/citizen/submit")


def test_csrf_complaint_submit_valid_post_succeeds(client, app):
    _register(client, "sub@example.com", "Sub User")
    _login(client, "sub@example.com")
    token = _assert_has_csrf_token(client, "/citizen/submit")
    response = client.post(
        "/citizen/submit",
        data={
            "csrf_token": token,
            "category_id": "1",
            "description": "A pile of garbage has been here for weeks.",
            "address_text": "1 Sub Street",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "additional_info": "Near the bus stop.",
            "image": _make_image_file("photo.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Complaint submitted successfully" in response.data
    with app.app_context():
        user = User.query.filter_by(email="sub@example.com").first()
        report = Report.query.filter_by(user_id=user.id).first()
        assert report is not None
        assert report.reference.startswith("ET-")


def test_csrf_complaint_submit_post_without_token_returns_400(client):
    _register(client, "sub2@example.com", "Sub User 2")
    _login(client, "sub2@example.com")
    response = client.post(
        "/citizen/submit",
        data={
            "category_id": "1",
            "description": "A pile of garbage has been here for weeks.",
            "address_text": "1 Sub Street",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "image": _make_image_file("photo.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_csrf_complaint_submit_post_with_invalid_token_returns_400(client):
    _register(client, "sub3@example.com", "Sub User 3")
    _login(client, "sub3@example.com")
    response = client.post(
        "/citizen/submit",
        data={
            "csrf_token": "invalid-token",
            "category_id": "1",
            "description": "A pile of garbage has been here for weeks.",
            "address_text": "1 Sub Street",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "image": _make_image_file("photo.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 5. Administrator complaint verification
# ---------------------------------------------------------------------------


def _setup_verified_complaint(client, app, email="verify@example.com"):
    _submit_complaint(client, email, "Verify Citizen")
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        report = Report.query.filter_by(user_id=user.id).first()
        report.status = ReportStatus.VERIFIED
        db.session.commit()
        reference = report.reference
    return reference


def test_csrf_admin_verify_complaint(client, app):
    _make_admin(app)
    reference = _setup_verified_complaint(client, app)
    _login(client, "admin@example.com", "AdminPass123")
    token = _assert_has_csrf_token(client, "/admin/complaints")
    response = client.post(
        f"/admin/complaints/{reference}/verify",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        updated = Report.query.filter_by(reference=reference).first()
        assert updated.status == ReportStatus.VERIFIED


def test_csrf_admin_verify_complaint_without_token_returns_400(client, app):
    _make_admin(app)
    reference = _setup_verified_complaint(client, app)
    _login(client, "admin@example.com", "AdminPass123")
    response = client.post(
        f"/admin/complaints/{reference}/verify", follow_redirects=False
    )
    assert response.status_code == 400


def test_csrf_admin_verify_complaint_with_invalid_token_returns_400(client, app):
    _make_admin(app)
    reference = _setup_verified_complaint(client, app)
    _login(client, "admin@example.com", "AdminPass123")
    response = client.post(
        f"/admin/complaints/{reference}/verify",
        data={"csrf_token": "invalid-token"},
        follow_redirects=False,
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 6. Administrator staff assignment
# ---------------------------------------------------------------------------


def _setup_assignable_complaint(client, app, email="assign@example.com"):
    _submit_complaint(client, email, "Assign Citizen")
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        report = Report.query.filter_by(user_id=user.id).first()
        report.status = ReportStatus.VERIFIED
        db.session.commit()
        reference = report.reference
    return reference


def test_csrf_admin_assign_staff(client, app):
    _make_admin(app)
    _make_staff(app)
    reference = _setup_assignable_complaint(client, app)
    with app.app_context():
        staff_user = User.query.filter_by(email="staff@example.com").first()
        staff_id = staff_user.id
    _login(client, "admin@example.com", "AdminPass123")
    token = _assert_has_csrf_token(client, "/admin/dashboard")
    response = client.post(
        "/admin/tasks/assign",
        data={
            "csrf_token": token,
            "reference": reference,
            "staff_id": staff_id,
            "due_date": "2026-12-01",
            "instructions": "Collect garbage promptly.",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="assign@example.com").first()
        report = Report.query.filter_by(user_id=user.id).first()
        task = CollectionTask.query.filter_by(report_id=report.id).first()
        assert task is not None
        assert task.staff_id == staff_id
        assert report.status == ReportStatus.ASSIGNED


def test_csrf_admin_assign_staff_without_token_returns_400(client, app):
    _make_admin(app)
    _make_staff(app)
    reference = _setup_assignable_complaint(client, app)
    _login(client, "admin@example.com", "AdminPass123")
    response = client.post(
        "/admin/tasks/assign",
        data={
            "reference": reference,
            "staff_id": 1,
            "due_date": "2026-12-01",
            "instructions": "Collect garbage promptly.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_csrf_admin_assign_staff_with_invalid_token_returns_400(client, app):
    _make_admin(app)
    _make_staff(app)
    reference = _setup_assignable_complaint(client, app)
    _login(client, "admin@example.com", "AdminPass123")
    response = client.post(
        "/admin/tasks/assign",
        data={
            "csrf_token": "invalid-token",
            "reference": reference,
            "staff_id": 1,
            "due_date": "2026-12-01",
            "instructions": "Collect garbage promptly.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 7. Staff task progress update
# ---------------------------------------------------------------------------


def _setup_staff_task(client, app, email="prog@example.com"):
    _make_admin(app)
    _make_staff(app, email=email, full_name="Staff Prog")
    _login(client, email, "StaffPass123")
    with app.app_context():
        staff_user = User.query.filter_by(email=email).first()
        admin = User.query.filter_by(email="admin@example.com").first()
        citizen = User(
            full_name="Citizen", email="citizen_prog@example.com", role=Role.CITIZEN
        )
        citizen.set_password("Pass1234")
        db.session.add(citizen)
        db.session.flush()
        cat = WasteCategory.query.filter_by(category_name="Organic Waste").first()
        report = Report(
            user_id=citizen.id,
            category_id=cat.id,
            description="Garbage piled up for many days.",
            reference="ET-PROGCSRF",
            status=ReportStatus.VERIFIED,
        )
        db.session.add(report)
        db.session.flush()
        task = CollectionTask(
            report_id=report.id,
            staff_id=staff_user.id,
            assigned_by=admin.id,
            task_status=TaskStatus.ASSIGNED,
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id
    return task_id


def test_csrf_staff_update_task(client, app):
    task_id = _setup_staff_task(client, app)
    token = _assert_has_csrf_token(client, f"/staff/tasks/{task_id}")
    response = client.post(
        f"/staff/tasks/{task_id}/update",
        data={"csrf_token": token, "status": "In Progress", "remarks": "Started collection."},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Task #" in response.data
    with app.app_context():
        updated = db.session.get(CollectionTask, task_id)
        assert updated.task_status == TaskStatus.IN_PROGRESS


def test_csrf_staff_update_task_without_token_returns_400(client, app):
    task_id = _setup_staff_task(client, app)
    response = client.post(
        f"/staff/tasks/{task_id}/update",
        data={"status": "In Progress", "remarks": "Started collection."},
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_csrf_staff_update_task_with_invalid_token_returns_400(client, app):
    task_id = _setup_staff_task(client, app)
    response = client.post(
        f"/staff/tasks/{task_id}/update",
        data={"csrf_token": "invalid-token", "status": "In Progress", "remarks": "Started collection."},
        follow_redirects=False,
    )
    assert response.status_code == 400
