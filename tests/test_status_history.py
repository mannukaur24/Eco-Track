"""Complaint status history tests for EcoTrack."""

import pytest
from app import create_app
from app.extensions import db
from app.models.user import User, Role, ReportStatus, TaskStatus
from app.models.report import Report
from app.models.report_status_history import ReportStatusHistory
from app.models.collection_task import CollectionTask
from app.models.waste_category import WasteCategory
from app.models.staff import Staff
from app.services.admin_service import AdminService


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        for name in ["Organic Waste", "Plastic Waste"]:
            if not WasteCategory.query.filter_by(category_name=name).first():
                db.session.add(WasteCategory(category_name=name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client, email, password="Password123"):
    return client.post(
        "/auth/login", data={"email": email, "password": password}, follow_redirects=True
    )


def _logout(client):
    client.post("/auth/logout", follow_redirects=True)


def _history(app, report):
    return (
        ReportStatusHistory.query.filter_by(report_id=report.id)
        .order_by(ReportStatusHistory.created_at)
        .all()
    )


def _create_users(app):
    with app.app_context():
        citizen = User(
            full_name="Citizen", email="citizen@example.com", role=Role.CITIZEN
        )
        citizen.set_password("Password123")
        admin = User(
            full_name="Admin", email="admin@example.com", role=Role.ADMINISTRATOR
        )
        admin.set_password("AdminPass123")
        staff_user = User(
            full_name="Staff", email="staff@example.com", role=Role.STAFF
        )
        staff_user.set_password("StaffPass123")
        db.session.add_all([citizen, admin, staff_user])
        db.session.flush()
        db.session.add(Staff(user_id=staff_user.id, availability="Mon-Fri", service_area="Zone A"))
        db.session.commit()
        return (
            citizen.id,
            admin.id,
            staff_user.id,
        )


def test_submission_records_status_history(client, app):
    _create_users(app)
    _login(client, "citizen@example.com")
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
        citizen_id = User.query.filter_by(email="citizen@example.com").first().id
        report = Report.query.filter_by(user_id=citizen_id).first()
        history = _history(app, report)
        assert len(history) == 1
        assert history[0].previous_status is None
        assert history[0].new_status == ReportStatus.PENDING
        assert history[0].updated_by == citizen_id


def test_verify_and_reject_record_history(client, app):
    _create_users(app)
    _login(client, "citizen@example.com")
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
        citizen = User.query.filter_by(email="citizen@example.com").first()
        report = Report.query.filter_by(user_id=citizen.id).first()
        reference = report.reference

    _logout(client)
    _login(client, "admin@example.com", "AdminPass123")
    client.post(f"/admin/complaints/{reference}/verify", follow_redirects=True)
    client.post(
        f"/admin/complaints/{reference}/reject",
        data={"rejection_reason": "Not valid."},
        follow_redirects=True,
    )

    with app.app_context():
        report = Report.query.filter_by(reference=reference).first()
        history = _history(app, report)
        assert len(history) == 3
        assert history[0].new_status == ReportStatus.PENDING
        assert history[1].previous_status == ReportStatus.PENDING
        assert history[1].new_status == ReportStatus.VERIFIED
        assert history[2].previous_status == ReportStatus.VERIFIED
        assert history[2].new_status == ReportStatus.REJECTED
        assert "Not valid" in (history[2].remarks or "")


def test_assignment_records_history(client, app):
    citizen_id, admin_id, staff_id = _create_users(app)
    _login(client, "citizen@example.com")
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
        citizen = User.query.filter_by(email="citizen@example.com").first()
        report = Report.query.filter_by(user_id=citizen.id).first()
        report.status = ReportStatus.VERIFIED
        reference = report.reference
        admin = User.query.filter_by(email="admin@example.com").first()
        db.session.commit()

    _logout(client)
    _login(client, "admin@example.com", "AdminPass123")
    client.post(f"/admin/complaints/{reference}/verify", follow_redirects=True)
    with app.app_context():
        report = Report.query.filter_by(reference=reference).first()
        admin = User.query.filter_by(email="admin@example.com").first()
        AdminService.assign_task(
            reference=reference,
            staff_id=staff_id,
            due_date="2026-12-01",
            instructions="Collect it.",
            admin_user=admin,
        )
        history = _history(app, report)
        assigned = [h for h in history if h.new_status == ReportStatus.ASSIGNED]
        assert len(assigned) == 1
        assert assigned[0].updated_by == admin.id


def test_task_progress_and_completion_record_history(client, app):
    citizen_id, admin_id, staff_id = _create_users(app)
    with app.app_context():
        citizen = User.query.filter_by(email="citizen@example.com").first()
        admin = User.query.filter_by(email="admin@example.com").first()
        staff_user = User.query.filter_by(email="staff@example.com").first()
        cat = WasteCategory.query.filter_by(category_name="Organic Waste").first()
        report = Report(
            user_id=citizen.id, category_id=cat.id,
            description="Garbage piled up for many days.",
            reference="ET-HIST01", status=ReportStatus.VERIFIED,
        )
        db.session.add(report)
        db.session.flush()
        task = CollectionTask(
            report_id=report.id, staff_id=staff_user.id,
            assigned_by=admin.id, task_status=TaskStatus.ASSIGNED,
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id
        report_id = report.id

    _login(client, "staff@example.com", "StaffPass123")
    client.post(
        f"/staff/tasks/{task_id}/update",
        data={"status": "In Progress", "remarks": "Started collection."},
        follow_redirects=True,
    )
    client.post(
        f"/staff/tasks/{task_id}/update",
        data={"status": "Completed", "remarks": "Collected all garbage."},
        follow_redirects=True,
    )

    with app.app_context():
        report = db.session.get(Report, report_id)
        assert report.status == ReportStatus.COMPLETED
        history = _history(app, report)
        new_statuses = [h.new_status for h in history]
        assert ReportStatus.IN_PROGRESS in new_statuses
        assert ReportStatus.COMPLETED in new_statuses
        completed = [h for h in history if h.new_status == ReportStatus.COMPLETED][0]
        assert completed.updated_by == staff_id
        assert "Collected" in (completed.remarks or "")


def test_history_not_fabricated(client, app):
    _create_users(app)
    _login(client, "citizen@example.com")
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
        report = Report.query.filter_by(
            user_id=User.query.filter_by(email="citizen@example.com").first().id
        ).first()
        history = _history(app, report)
        assert len(history) == 1
        assert history[0].new_status == ReportStatus.PENDING


def test_citizen_detail_timeline_shows_history(client, app):
    _create_users(app)
    _login(client, "citizen@example.com")
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
        report = Report.query.filter_by(
            user_id=User.query.filter_by(email="citizen@example.com").first().id
        ).first()
        reference = report.reference

    response = client.get(f"/citizen/complaint/{reference}", follow_redirects=True)
    assert response.status_code == 200
    assert b"Status History" in response.data
    assert b"Pending" in response.data
