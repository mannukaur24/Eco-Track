"""Administrator panel tests."""

import pytest
from datetime import datetime
from app import create_app
from app.extensions import db
from app.models.user import User, Role, ReportStatus, TaskStatus
from app.models.report import Report
from app.models.waste_category import WasteCategory
from app.models.collection_task import CollectionTask


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        cats = [
            "Organic Waste", "Plastic Waste", "Electronic Waste",
            "Household Waste", "Construction Waste", "Industrial Waste", "Other",
        ]
        for name in cats:
            if not WasteCategory.query.filter_by(category_name=name).first():
                db.session.add(WasteCategory(category_name=name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


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


def _make_admin(app, client, email="admin@example.com", full_name="Admin User"):
    """Create an admin user directly in the DB and log in."""
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


def test_admin_dashboard_requires_admin(client, app):
    # Citizen should be denied
    _register(client, "citizen@example.com", "Citizen User", role="Citizen")
    _login(client, "citizen@example.com")
    response = client.get("/admin/dashboard", follow_redirects=True)
    assert response.status_code == 403 or b"permission" in response.data.lower()


def test_staff_cannot_access_admin(client, app):
    # Staff accounts are provisioned by an administrator, not via public
    # registration, so create the staff user directly with a Staff profile.
    with app.app_context():
        staff_user = User(
            full_name="Staff User", email="staff@example.com", role=Role.STAFF
        )
        staff_user.set_password("Password123")
        db.session.add(staff_user)
        db.session.flush()
        from app.models.staff import Staff

        db.session.add(Staff(user_id=staff_user.id))
        db.session.commit()
    _login(client, "staff@example.com", "Password123")
    response = client.get("/admin/dashboard", follow_redirects=True)
    assert response.status_code == 403 or b"permission" in response.data.lower()


def test_admin_dashboard_access(client, app):
    _make_admin(app, client)
    response = client.get("/admin/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_admin_dashboard_stats(client, app):
    _make_admin(app, client)
    # Create a complaint as citizen
    client.post("/auth/logout", follow_redirects=True)
    _register(client, "c@example.com", "Citizen C", role="Citizen")
    _login(client, "c@example.com")
    client.post(
        "/citizen/submit",
        data={
            "category_id": "1",
            "description": "Garbage piled up on the street for many days now.",
            "address_text": "1 Main Street",
            "latitude": "28.6139",
            "longitude": "77.2090",
        },
        follow_redirects=True,
    )
    # Log back in as admin
    client.post("/auth/logout", follow_redirects=True)
    _login(client, "admin@example.com")
    response = client.get("/admin/dashboard", follow_redirects=True)
    assert response.status_code == 200


def test_admin_view_complaints(client, app):
    _make_admin(app, client)
    response = client.get("/admin/complaints", follow_redirects=True)
    assert response.status_code == 200


def test_admin_verify_complaint(client, app):
    _make_admin(app, client)
    # Create complaint as citizen
    client.post("/auth/logout", follow_redirects=True)
    _register(client, "c@example.com", "Citizen C", role="Citizen")
    _login(client, "c@example.com")
    client.post(
        "/citizen/submit",
        data={
            "category_id": "1",
            "description": "Garbage piled up on the street for many days now.",
            "address_text": "1 Main Street",
            "latitude": "28.6139",
            "longitude": "77.2090",
        },
        follow_redirects=True,
    )
    with app.app_context():
        user = User.query.filter_by(email="c@example.com").first()
        report = Report.query.filter_by(user_id=user.id).first()
        reference = report.reference
    # Login as admin and verify
    client.post("/auth/logout", follow_redirects=True)
    _login(client, "admin@example.com", "AdminPass123")
    response = client.post(
        f"/admin/complaints/{reference}/verify", follow_redirects=True
    )
    assert response.status_code == 200
    with app.app_context():
        updated = Report.query.filter_by(reference=reference).first()
        assert updated.status == ReportStatus.VERIFIED


def test_admin_reject_complaint_with_reason(client, app):
    _make_admin(app, client)
    client.post("/auth/logout", follow_redirects=True)
    _register(client, "c@example.com", "Citizen C", role="Citizen")
    _login(client, "c@example.com")
    client.post(
        "/citizen/submit",
        data={
            "category_id": "1",
            "description": "Garbage piled up on the street for many days now.",
            "address_text": "1 Main Street",
            "latitude": "28.6139",
            "longitude": "77.2090",
        },
        follow_redirects=True,
    )
    with app.app_context():
        user = User.query.filter_by(email="c@example.com").first()
        report = Report.query.filter_by(user_id=user.id).first()
        reference = report.reference
    client.post("/auth/logout", follow_redirects=True)
    _login(client, "admin@example.com", "AdminPass123")
    # Reject without reason should fail
    response = client.post(
        f"/admin/complaints/{reference}/reject",
        data={"rejection_reason": ""},
        follow_redirects=True,
    )
    assert b"rejection reason is required" in response.data.lower()
    # Reject with reason should succeed
    response = client.post(
        f"/admin/complaints/{reference}/reject",
        data={"rejection_reason": "Invalid complaint, no evidence."},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        updated = Report.query.filter_by(reference=reference).first()
        assert updated.status == ReportStatus.REJECTED
        assert updated.rejection_reason == "Invalid complaint, no evidence."


def test_admin_assign_task(client, app):
    _make_admin(app, client)
    # Create staff user via DB
    with app.app_context():
        staff_user = User(
            full_name="Staff Worker", email="staff@example.com", role=Role.STAFF
        )
        staff_user.set_password("Password123")
        db.session.add(staff_user)
        db.session.flush()
        from app.models.staff import Staff
        db.session.add(Staff(user_id=staff_user.id, availability="Mon-Fri", service_area="Zone A"))
        db.session.commit()
        staff_id = staff_user.id

    # Create verified complaint as citizen
    client.post("/auth/logout", follow_redirects=True)
    _register(client, "c@example.com", "Citizen C", role="Citizen")
    _login(client, "c@example.com")
    client.post(
        "/citizen/submit",
        data={
            "category_id": "1",
            "description": "Garbage piled up on the street for many days now.",
            "address_text": "1 Main Street",
            "latitude": "28.6139",
            "longitude": "77.2090",
        },
        follow_redirects=True,
    )
    with app.app_context():
        user = User.query.filter_by(email="c@example.com").first()
        report = Report.query.filter_by(user_id=user.id).first()
        reference = report.reference
        report.status = ReportStatus.VERIFIED
        db.session.commit()

    # Login as admin and assign task
    client.post("/auth/logout", follow_redirects=True)
    _login(client, "admin@example.com", "AdminPass123")
    response = client.post(
        "/admin/tasks/assign",
        data={
            "reference": reference,
            "staff_id": staff_id,
            "due_date": "2026-12-01",
            "instructions": "Collect garbage promptly.",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="c@example.com").first()
        report = Report.query.filter_by(user_id=user.id).first()
        task = CollectionTask.query.filter_by(report_id=report.id).first()
        assert task is not None
        assert task.staff_id == staff_id
        assert task.assigned_by == User.query.filter_by(email="admin@example.com").first().id
        assert report.status == ReportStatus.ASSIGNED


def test_admin_add_staff(client, app):
    _make_admin(app, client)
    response = client.post(
        "/admin/staff/add",
        data={
            "full_name": "New Staff",
            "email": "newstaff@example.com",
            "phone": "5551234",
            "availability": "Mon-Fri",
            "service_area": "Zone B",
            "password": "StaffPass123",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Staff member added" in response.data
    with app.app_context():
        user = User.query.filter_by(email="newstaff@example.com").first()
        assert user is not None
        assert user.role == Role.STAFF
        from app.models.staff import Staff
        assert Staff.query.filter_by(user_id=user.id).first() is not None


def test_admin_add_staff_duplicate_email(client, app):
    _make_admin(app, client)
    # Create staff first via DB
    with app.app_context():
        user = User(full_name="Existing", email="dup@example.com", role=Role.STAFF)
        user.set_password("Password123")
        db.session.add(user)
        db.session.flush()
        from app.models.staff import Staff
        db.session.add(Staff(user_id=user.id))
        db.session.commit()
    response = client.post(
        "/admin/staff/add",
        data={
            "full_name": "Dup Staff",
            "email": "dup@example.com",
            "phone": "555",
            "availability": "Mon-Fri",
            "service_area": "Zone",
            "password": "StaffPass123",
        },
        follow_redirects=True,
    )
    assert b"already exists" in response.data.lower()


def test_admin_toggle_staff_active(client, app):
    _make_admin(app, client)
    with app.app_context():
        staff_user = User(full_name="Toggle", email="toggle@example.com", role=Role.STAFF)
        staff_user.set_password("Password123")
        db.session.add(staff_user)
        db.session.flush()
        from app.models.staff import Staff
        db.session.add(Staff(user_id=staff_user.id))
        db.session.commit()
        staff_id = staff_user.id
    response = client.post(
        f"/admin/staff/{staff_id}/toggle", follow_redirects=True
    )
    assert response.status_code == 200
    with app.app_context():
        user = db.session.get(User, staff_id)
        assert user.is_active is False


def test_admin_category_management(client, app):
    _make_admin(app, client)
    # Add category
    response = client.post(
        "/admin/categories/add",
        data={"category_name": "Medical Waste", "description": "Medical waste items."},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Category added" in response.data
    # Duplicate
    response = client.post(
        "/admin/categories/add",
        data={"category_name": "Medical Waste", "description": "Dup."},
        follow_redirects=True,
    )
    assert b"already exists" in response.data.lower()
    with app.app_context():
        cat = WasteCategory.query.filter_by(category_name="Medical Waste").first()
        # Edit
        response = client.post(
            f"/admin/categories/{cat.id}/edit",
            data={"category_name": "Medical Waste Updated", "description": "Updated."},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert cat.category_name == "Medical Waste Updated"


def test_admin_awareness_management(client, app):
    _make_admin(app, client)
    response = client.post(
        "/admin/awareness/add",
        data={
            "title": "Recycling Guide",
            "content": "Learn to recycle properly.",
            "topic": "Recycling",
            "is_published": "y",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Article created" in response.data
    with app.app_context():
        from app.models.awareness_article import AwarenessArticle
        article = AwarenessArticle.query.filter_by(title="Recycling Guide").first()
        assert article is not None
        assert article.is_published is True
        # Toggle publish
        response = client.post(
            f"/admin/awareness/{article.id}/toggle", follow_redirects=True
        )
        assert response.status_code == 200
        assert article.is_published is False
        # Edit
        response = client.post(
            f"/admin/awareness/{article.id}/edit",
            data={
                "title": "Recycling Guide Updated",
                "content": "New content.",
                "topic": "Recycling",
                "is_published": "y",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert article.title == "Recycling Guide Updated"


def test_admin_dashboard_with_due_dates(client, app):
    _make_admin(app, client)
    with app.app_context():
        staff_user = User(
            full_name="Staff Worker", email="staff_due@example.com", role=Role.STAFF
        )
        staff_user.set_password("Password123")
        db.session.add(staff_user)
        db.session.flush()
        from app.models.staff import Staff

        db.session.add(Staff(user_id=staff_user.id))
        citizen = User(
            full_name="Citizen", email="citizen_due@example.com", role=Role.CITIZEN
        )
        citizen.set_password("Pass1234")
        db.session.add(citizen)
        db.session.flush()
        cat = WasteCategory.query.filter_by(category_name="Organic Waste").first()
        report = Report(
            user_id=citizen.id,
            category_id=cat.id,
            description="Due date complaint.",
            reference="ET-DUE01",
            status=ReportStatus.VERIFIED,
        )
        db.session.add(report)
        db.session.flush()
        task = CollectionTask(
            report_id=report.id,
            staff_id=staff_user.id,
            assigned_by=User.query.filter_by(email="admin@example.com").first().id,
            due_date=datetime(2026, 12, 1),
            task_status=TaskStatus.ASSIGNED,
        )
        db.session.add(task)
        db.session.commit()
    response = client.get("/admin/dashboard", follow_redirects=True)
    assert response.status_code == 200


def test_admin_complaints_date_filter_inclusive_end_date(client, app):
    _make_admin(app, client)
    from datetime import datetime

    with app.app_context():
        citizen = User(
            full_name="Citizen", email="citizen_date@example.com", role=Role.CITIZEN
        )
        citizen.set_password("Pass1234")
        db.session.add(citizen)
        db.session.flush()
        cat = WasteCategory.query.filter_by(category_name="Organic Waste").first()
        # One complaint mid-day on the end date.
        report_same_day = Report(
            user_id=citizen.id,
            category_id=cat.id,
            description="Same day complaint.",
            reference="ET-DATE01",
            status=ReportStatus.PENDING,
            created_at=datetime(2026, 6, 10, 15, 30, 0),
        )
        # One complaint the day after the end date (must be excluded).
        report_next_day = Report(
            user_id=citizen.id,
            category_id=cat.id,
            description="Next day complaint.",
            reference="ET-DATE02",
            status=ReportStatus.PENDING,
            created_at=datetime(2026, 6, 11, 8, 0, 0),
        )
        db.session.add_all([report_same_day, report_next_day])
        db.session.commit()

    response = client.get(
        "/admin/complaints?date_from=2026-06-10&date_to=2026-06-10",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"ET-DATE01" in response.data
    assert b"ET-DATE02" not in response.data

