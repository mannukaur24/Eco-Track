"""Security tests for EcoTrack image privacy and health endpoint."""

import io
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User, Role, ReportStatus
from app.models.report import Report
from app.models.staff import Staff
from app.models.waste_category import WasteCategory
from app.services.admin_service import AdminService
from werkzeug.datastructures import FileStorage


@pytest.fixture
def app(tmp_path):
    app = create_app("testing")
    app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
    with app.app_context():
        db.create_all()
        if not WasteCategory.query.filter_by(category_name="Organic Waste").first():
            db.session.add(WasteCategory(category_name="Organic Waste"))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _make_png(name="photo.png"):
    return FileStorage(
        stream=io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100),
        filename=name,
        content_type="image/png",
    )


def _register_and_login(client, email, full_name, role=Role.CITIZEN, password="Password123"):
    client.post(
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
    client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )
    return User.query.filter_by(email=email).first()


def _logout(client):
    client.post("/auth/logout", follow_redirects=True)


def _login(client, email, password="Password123"):
    return client.post(
        "/auth/login", data={"email": email, "password": password}, follow_redirects=True
    )


def _image_filename(report):
    return report.image_path.rsplit("/", 1)[-1]


def test_health_endpoint_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"


def test_health_endpoint_db_failure(client, app, monkeypatch):
    from app.extensions import db as _db

    def _raise(*args, **kwargs):
        raise RuntimeError("database connection failed")

    monkeypatch.setattr(_db.session.__class__, "execute", _raise)
    response = client.get("/health")
    assert response.status_code == 503
    data = response.get_json()
    assert data["status"] == "fail"
    assert data["database"] == "unavailable"
    body = response.data.decode("utf-8", errors="replace")
    assert "database connection failed" not in body


def test_owner_can_view_own_complaint_image(client, app):
    citizen = _register_and_login(client, "owner@example.com", "Owner User")
    client.post(
        "/citizen/submit",
        data={
            "category_id": "1",
            "description": "A pile of garbage has been here for weeks.",
            "address_text": "1 Owner Street",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "image": _make_png(),
        },
        follow_redirects=True,
    )
    with app.app_context():
        report = Report.query.filter_by(user_id=citizen.id).first()
        assert report is not None and report.image_path is not None
        filename = _image_filename(report)
    response = client.get(f"/uploads/{filename}")
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "").startswith("image/")


def test_other_citizen_cannot_view_image(client, app):
    owner = _register_and_login(client, "owner@example.com", "Owner User")
    client.post(
        "/citizen/submit",
        data={
            "category_id": "1",
            "description": "A pile of garbage has been here for weeks.",
            "address_text": "1 Owner Street",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "image": _make_png(),
        },
        follow_redirects=True,
    )
    with app.app_context():
        report = Report.query.filter_by(user_id=owner.id).first()
        filename = _image_filename(report)

    _logout(client)
    _register_and_login(client, "other@example.com", "Other User")
    response = client.get(f"/uploads/{filename}")
    assert response.status_code == 403


def test_admin_can_view_any_complaint_image(client, app):
    _register_and_login(client, "citizen@example.com", "Citizen User")
    client.post(
        "/citizen/submit",
        data={
            "category_id": "1",
            "description": "A pile of garbage has been here for weeks.",
            "address_text": "1 Citizen Street",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "image": _make_png(),
        },
        follow_redirects=True,
    )
    _logout(client)
    with app.app_context():
        citizen_user = User.query.filter_by(email="citizen@example.com").first()
        report = Report.query.filter_by(user_id=citizen_user.id).first()
        filename = _image_filename(report)
        admin = User(
            full_name="Admin",
            email="admin@example.com",
            role=Role.ADMINISTRATOR,
            is_active=True,
        )
        admin.set_password("AdminPass123")
        db.session.add(admin)
        db.session.commit()

    _login(client, "admin@example.com", "AdminPass123")
    response = client.get(f"/uploads/{filename}")
    assert response.status_code == 200


def test_assigned_staff_can_view_image(client, app):
    _register_and_login(client, "citizen@example.com", "Citizen User")
    client.post(
        "/citizen/submit",
        data={
            "category_id": "1",
            "description": "A pile of garbage has been here for weeks.",
            "address_text": "1 Citizen Street",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "image": _make_png(),
        },
        follow_redirects=True,
    )
    _logout(client)
    with app.app_context():
        report = Report.query.filter_by(
            user_id=User.query.filter_by(email="citizen@example.com").first().id
        ).first()
        report.status = ReportStatus.VERIFIED
        reference = report.reference
        filename = _image_filename(report)

        admin = User(
            full_name="Admin",
            email="admin@example.com",
            role=Role.ADMINISTRATOR,
            is_active=True,
        )
        admin.set_password("AdminPass123")
        db.session.add(admin)
        db.session.flush()
        staff_user = User(
            full_name="Staff",
            email="staff@example.com",
            role=Role.STAFF,
            is_active=True,
        )
        staff_user.set_password("StaffPass123")
        db.session.add(staff_user)
        db.session.flush()
        db.session.add(Staff(user_id=staff_user.id, availability="Mon-Fri", service_area="Zone A"))
        db.session.commit()
        staff_id = staff_user.id

    _login(client, "admin@example.com", "AdminPass123")
    client.post(
        f"/admin/complaints/{reference}/verify", follow_redirects=True
    )
    client.post(
        "/admin/tasks/assign",
        data={
            "reference": reference,
            "staff_id": staff_id,
            "due_date": "2026-12-01",
            "instructions": "Collect it.",
        },
        follow_redirects=True,
    )
    _logout(client)
    _login(client, "staff@example.com", "StaffPass123")
    response = client.get(f"/uploads/{filename}")
    assert response.status_code == 200


def test_unassigned_staff_cannot_view_image(client, app):
    _register_and_login(client, "citizen@example.com", "Citizen User")
    client.post(
        "/citizen/submit",
        data={
            "category_id": "1",
            "description": "A pile of garbage has been here for weeks.",
            "address_text": "1 Citizen Street",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "image": _make_png(),
        },
        follow_redirects=True,
    )
    _logout(client)
    with app.app_context():
        report = Report.query.filter_by(
            user_id=User.query.filter_by(email="citizen@example.com").first().id
        ).first()
        report.status = ReportStatus.VERIFIED
        filename = _image_filename(report)

        admin = User(
            full_name="Admin",
            email="admin@example.com",
            role=Role.ADMINISTRATOR,
            is_active=True,
        )
        admin.set_password("AdminPass123")
        db.session.add(admin)
        db.session.flush()
        staff_user = User(
            full_name="Other Staff",
            email="otherstaff@example.com",
            role=Role.STAFF,
            is_active=True,
        )
        staff_user.set_password("StaffPass123")
        db.session.add(staff_user)
        db.session.flush()
        db.session.add(Staff(user_id=staff_user.id))
        db.session.commit()

    _login(client, "otherstaff@example.com", "StaffPass123")
    response = client.get(f"/uploads/{filename}")
    assert response.status_code == 403


def test_nonexistent_image_returns_404(client):
    _register_and_login(client, "viewer@example.com", "Viewer User")
    response = client.get("/uploads/does-not-exist.png")
    assert response.status_code == 404


def test_path_traversal_image_request_rejected(client):
    _register_and_login(client, "viewer@example.com", "Viewer User")
    response = client.get("/uploads/../../../windows/win.ini")
    assert response.status_code == 404
