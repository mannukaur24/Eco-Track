"""Waste category seeding, filtering, and administration tests.

Runs against the existing SQLite TestingConfig.
"""

import io

import pytest
from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.waste_category import WasteCategory
from app.models.report import Report
from app.models.location import Location
from app.services.admin_service import AdminService
from werkzeug.datastructures import FileStorage

DEFAULT_CATEGORIES = [
    "Plastic Waste",
    "Organic Waste",
    "Electronic Waste",
    "Household Waste",
    "Construction Waste",
    "Industrial Waste",
    "Other",
]


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


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


def _register(client, email, full_name, role="Citizen", password="Password123"):
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


def _make_image_file(name="test.png"):
    return FileStorage(
        stream=io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100),
        filename=name,
        content_type="image/png",
    )


def _make_admin(app, client, email="admin@example.com", full_name="Admin User"):
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
    client.post("/auth/logout", follow_redirects=True)
    _login(client, email, "AdminPass123")
    return admin


# ---------------------------------------------------------------------------
# 1. Default category seeding
# ---------------------------------------------------------------------------


def test_seed_categories_creates_defaults(app, runner):
    result = runner.invoke(args=["seed-categories"])
    assert result.exit_code == 0
    with app.app_context():
        rows = WasteCategory.query.all()
        names = {c.category_name for c in rows}
        assert set(DEFAULT_CATEGORIES) <= names
        for name in DEFAULT_CATEGORIES:
            cat = WasteCategory.query.filter_by(category_name=name).first()
            assert cat is not None
            assert cat.is_active is True


def test_seed_categories_is_idempotent(app, runner):
    first = runner.invoke(args=["seed-categories"])
    second = runner.invoke(args=["seed-categories"])
    third = runner.invoke(args=["seed-categories"])
    assert first.exit_code == 0
    assert second.exit_code == 0
    assert third.exit_code == 0
    with app.app_context():
        assert WasteCategory.query.count() == len(DEFAULT_CATEGORIES)
        assert len({c.category_name for c in WasteCategory.query.all()}) == len(
            DEFAULT_CATEGORIES
        )


def test_seed_categories_preserves_existing(app, runner):
    with app.app_context():
        db.session.add(
            WasteCategory(
                category_name="Medical Waste", description="Medical waste items.",
                is_active=False,
            )
        )
        db.session.commit()
        medical = WasteCategory.query.filter_by(category_name="Medical Waste").first()
        medical_id = medical.id

    runner.invoke(args=["seed-categories"])

    with app.app_context():
        medical = db.session.get(WasteCategory, medical_id)
        assert medical is not None
        assert medical.is_active is False
        assert medical.description == "Medical waste items."
        assert WasteCategory.query.count() == len(DEFAULT_CATEGORIES) + 1


# ---------------------------------------------------------------------------
# 2. Category retrieval
# ---------------------------------------------------------------------------


def test_category_retrieval_returns_all(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["seed-categories"])
    with app.app_context():
        cats = AdminService.get_categories()
        assert len(cats) == len(DEFAULT_CATEGORIES)
        assert [c.category_name for c in cats] == sorted(DEFAULT_CATEGORIES)


# ---------------------------------------------------------------------------
# 3. Active / inactive category filtering
# ---------------------------------------------------------------------------


def test_citizen_form_excludes_inactive_categories(client, app):
    runner = app.test_cli_runner()
    runner.invoke(args=["seed-categories"])
    _register(client, "citizen@example.com", "Citizen User")
    _login(client, "citizen@example.com")

    with app.app_context():
        inactive = WasteCategory.query.filter_by(
            category_name="Industrial Waste"
        ).first()
        inactive.is_active = False
        db.session.commit()

    response = client.get("/citizen/submit", follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode("utf-8", errors="replace")
    assert "Select Waste Category" in html
    assert "Plastic Waste" in html
    assert "Organic Waste" in html
    assert "Industrial Waste" not in html


def test_citizen_form_shows_error_when_no_categories(client, app):
    _register(client, "citizen@example.com", "Citizen User")
    _login(client, "citizen@example.com")
    response = client.get("/citizen/submit", follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode("utf-8", errors="replace")
    assert "No waste categories are available" in html
    assert "Select Waste Category" in html


# ---------------------------------------------------------------------------
# 4. Complaint submission with a selected category
# ---------------------------------------------------------------------------


def test_submit_complaint_with_selected_category(client, app):
    runner = app.test_cli_runner()
    runner.invoke(args=["seed-categories"])
    _register(client, "citizen@example.com", "Citizen User")
    _login(client, "citizen@example.com")

    with app.app_context():
        category = WasteCategory.query.filter_by(category_name="Plastic Waste").first()
        category_id = category.id

    response = client.post(
        "/citizen/submit",
        data={
            "category_id": str(category_id),
            "description": "A pile of plastic bottles has been here for weeks.",
            "address_text": "1 Sub Street",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "image": _make_image_file("photo.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Complaint submitted successfully" in response.data
    with app.app_context():
        user = User.query.filter_by(email="citizen@example.com").first()
        report = Report.query.filter_by(user_id=user.id).first()
        assert report is not None
        assert report.category_id == category_id
        assert report.category.category_name == "Plastic Waste"


# ---------------------------------------------------------------------------
# 5. Invalid category ID rejection
# ---------------------------------------------------------------------------


def test_submit_complaint_invalid_category_id(client, app):
    runner = app.test_cli_runner()
    runner.invoke(args=["seed-categories"])
    _register(client, "citizen@example.com", "Citizen User")
    _login(client, "citizen@example.com")

    response = client.post(
        "/citizen/submit",
        data={
            "category_id": "99999",
            "description": "A pile of garbage has been here for weeks.",
            "address_text": "1 Sub Street",
            "latitude": "28.6139",
            "longitude": "77.2090",
            "image": _make_image_file("photo.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid waste category selected" in response.data
    with app.app_context():
        assert Report.query.count() == 0


# ---------------------------------------------------------------------------
# 6. Administrator category creation
# ---------------------------------------------------------------------------


def test_admin_category_creation_appears_in_citizen_form(client, app):
    _make_admin(app, client)
    response = client.post(
        "/admin/categories/add",
        data={
            "category_name": "Medical Waste",
            "description": "Medical waste items.",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Category added" in response.data
    with app.app_context():
        cat = WasteCategory.query.filter_by(category_name="Medical Waste").first()
        assert cat is not None
        assert cat.is_active is True

    client.post("/auth/logout", follow_redirects=True)
    _register(client, "citizen@example.com", "Citizen User", role="Citizen")
    _login(client, "citizen@example.com")
    response = client.get("/citizen/submit", follow_redirects=True)
    assert response.status_code == 200
    assert b"Medical Waste" in response.data


# ---------------------------------------------------------------------------
# 7. Existing complaint relationship preservation
# ---------------------------------------------------------------------------


def test_category_in_use_by_complaint_cannot_be_deleted(client, app):
    runner = app.test_cli_runner()
    runner.invoke(args=["seed-categories"])
    _make_admin(app, client)
    client.post("/auth/logout", follow_redirects=True)
    _register(client, "citizen@example.com", "Citizen User", role="Citizen")
    _login(client, "citizen@example.com")

    with app.app_context():
        category = WasteCategory.query.filter_by(category_name="Plastic Waste").first()
        user = User.query.filter_by(email="citizen@example.com").first()
        location = Location(address_text="1 Street")
        db.session.add(location)
        db.session.flush()
        report = Report(
            user_id=user.id,
            category_id=category.id,
            location_id=location.id,
            description="Plastic waste complaint.",
            reference="ET-PRESERVE",
            status="Pending",
        )
        db.session.add(report)
        db.session.commit()
        category_id = category.id

    client.post("/auth/logout", follow_redirects=True)
    _login(client, "admin@example.com", "AdminPass123")
    response = client.post(
        f"/admin/categories/{category_id}/delete", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"in use by complaints" in response.data.lower()
    with app.app_context():
        assert db.session.get(WasteCategory, category_id) is not None
        assert Report.query.filter_by(reference="ET-PRESERVE").first() is not None


def test_deactivated_category_keeps_existing_complaints(client, app):
    runner = app.test_cli_runner()
    runner.invoke(args=["seed-categories"])
    _make_admin(app, client)
    client.post("/auth/logout", follow_redirects=True)
    _register(client, "citizen@example.com", "Citizen User", role="Citizen")
    _login(client, "citizen@example.com")

    with app.app_context():
        category = WasteCategory.query.filter_by(category_name="Plastic Waste").first()
        user = User.query.filter_by(email="citizen@example.com").first()
        location = Location(address_text="1 Street")
        db.session.add(location)
        db.session.flush()
        report = Report(
            user_id=user.id,
            category_id=category.id,
            location_id=location.id,
            description="Plastic waste complaint.",
            reference="ET-TOGGLE",
            status="Pending",
        )
        db.session.add(report)
        db.session.commit()
        category_id = category.id

    client.post("/auth/logout", follow_redirects=True)
    _login(client, "admin@example.com", "AdminPass123")
    response = client.post(
        f"/admin/categories/{category_id}/toggle", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"deactivated" in response.data.lower()
    with app.app_context():
        assert db.session.get(WasteCategory, category_id).is_active is False
        assert Report.query.filter_by(reference="ET-TOGGLE").first() is not None
