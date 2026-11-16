"""Analytics, maps, and reporting tests."""

import io
import csv
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User, Role, ReportStatus
from app.models.report import Report
from app.models.waste_category import WasteCategory


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


def _login_admin(client, app, email="admin@example.com", password="AdminPass123"):
    with app.app_context():
        admin = User.query.filter_by(email=email).first()
        if admin is None:
            admin = User(
                full_name="Admin User",
                email=email,
                role=Role.ADMINISTRATOR,
                is_active=True,
            )
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
    client.post("/auth/logout", follow_redirects=True)
    client.post(
        "/auth/login", data={"email": email, "password": password}, follow_redirects=True
    )
    return admin


def test_analytics_dashboard_requires_admin(client, app):
    # Citizen denied
    client.post(
        "/auth/register",
        data={
            "full_name": "Citizen", "email": "c@example.com",
            "password": "Password123", "confirm_password": "Password123",
            "role": "Citizen", "phone": "1234567890",
        },
        follow_redirects=True,
    )
    client.post(
        "/auth/login", data={"email": "c@example.com", "password": "Password123"},
        follow_redirects=True,
    )
    response = client.get("/admin/analytics", follow_redirects=True)
    assert response.status_code == 403 or b"permission" in response.data.lower()


def test_staff_cannot_access_analytics(client, app):
    with app.app_context():
        staff = User(
            full_name="Staff", email="staff@example.com", role=Role.STAFF, is_active=True
        )
        staff.set_password("StaffPass123")
        db.session.add(staff)
        db.session.commit()
    client.post("/auth/logout", follow_redirects=True)
    client.post(
        "/auth/login", data={"email": "staff@example.com", "password": "StaffPass123"},
        follow_redirects=True,
    )
    response = client.get("/admin/analytics", follow_redirects=True)
    assert response.status_code == 403 or b"permission" in response.data.lower()


def test_analytics_dashboard_access(client, app):
    _login_admin(client, app)
    response = client.get("/admin/analytics", follow_redirects=True)
    assert response.status_code == 200
    assert b"Analytics" in response.data


def test_analytics_chart_data(client, app):
    _login_admin(client, app)
    # Create some complaints with categories and statuses
    with app.app_context():
        cat = WasteCategory.query.filter_by(category_name="Plastic Waste").first()
        citizen = User(
            full_name="Citizen", email="citizen@example.com", role=Role.CITIZEN
        )
        citizen.set_password("Password123")
        db.session.add(citizen)
        db.session.flush()
        r1 = Report(
            user_id=citizen.id, category_id=cat.id,
            description="d1", reference="ET-CAT01", status=ReportStatus.PENDING,
        )
        r2 = Report(
            user_id=citizen.id, category_id=cat.id,
            description="d2", reference="ET-CAT02", status=ReportStatus.COMPLETED,
        )
        db.session.add_all([r1, r2])
        db.session.commit()
    response = client.get("/admin/analytics", follow_redirects=True)
    assert response.status_code == 200


def test_analytics_date_filter_presets(client, app):
    _login_admin(client, app)
    for preset in ["7days", "30days", "3months", "custom"]:
        response = client.get(
            f"/admin/analytics?preset={preset}", follow_redirects=True
        )
        assert response.status_code == 200


def test_map_requires_admin(client, app):
    client.post(
        "/auth/register",
        data={
            "full_name": "Citizen", "email": "c2@example.com",
            "password": "Password123", "confirm_password": "Password123",
            "role": "Citizen", "phone": "1234567890",
        },
        follow_redirects=True,
    )
    client.post(
        "/auth/login", data={"email": "c2@example.com", "password": "Password123"},
        follow_redirects=True,
    )
    response = client.get("/admin/map", follow_redirects=True)
    assert response.status_code == 403 or b"permission" in response.data.lower()


def test_map_access(client, app):
    _login_admin(client, app)
    response = client.get("/admin/map", follow_redirects=True)
    assert response.status_code == 200
    assert b"Complaint Location Map" in response.data


def test_csv_complaint_register(client, app):
    _login_admin(client, app)
    response = client.get("/admin/reports/complaint-register", follow_redirects=True)
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")
    content = response.data.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    assert rows[0] == [
        "Reference", "Citizen Name", "Citizen Email", "Category",
        "Location", "Description", "Status", "Reference", "Submitted At",
    ]


def test_csv_pending_complaints(client, app):
    _login_admin(client, app)
    response = client.get("/admin/reports/pending-complaints", follow_redirects=True)
    assert response.status_code == 200
    content = response.data.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    assert rows[0] == [
        "Reference", "Citizen Name", "Category", "Location",
        "Description", "Submitted At",
    ]


def test_csv_category_wise(client, app):
    _login_admin(client, app)
    response = client.get("/admin/reports/category-wise", follow_redirects=True)
    assert response.status_code == 200
    content = response.data.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    assert rows[0] == ["Category", "Complaint Count"]


def test_csv_location_wise(client, app):
    _login_admin(client, app)
    response = client.get("/admin/reports/location-wise", follow_redirects=True)
    assert response.status_code == 200
    content = response.data.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    assert rows[0] == ["Location", "Latitude", "Longitude", "Complaint Count"]


def test_csv_staff_workload(client, app):
    _login_admin(client, app)
    response = client.get("/admin/reports/staff-workload", follow_redirects=True)
    assert response.status_code == 200
    content = response.data.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    assert rows[0] == ["Staff Name", "Email", "Total Tasks", "Completed", "Active"]


def test_csv_task_completion(client, app):
    _login_admin(client, app)
    response = client.get("/admin/reports/task-completion", follow_redirects=True)
    assert response.status_code == 200
    content = response.data.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    assert rows[0] == ["Task Status", "Task Count"]


def test_csv_monthly_activity(client, app):
    _login_admin(client, app)
    response = client.get(
        "/admin/reports/monthly-activity?months=6", follow_redirects=True
    )
    assert response.status_code == 200
    content = response.data.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    assert rows[0] == ["Month", "Complaints Submitted", "Complaints Resolved"]


# ---------- Analytics service unit tests ----------

def test_dashboard_summary_with_data(app):
    with app.app_context():
        from app.models.user import User
        from app.models.report import Report
        from app.models.waste_category import WasteCategory
        from app.services.analytics_service import AnalyticsService

        cat = WasteCategory.query.filter_by(category_name="Plastic Waste").first()
        citizen = User(
            full_name="Citizen", email="citizen@example.com", role="Citizen"
        )
        citizen.set_password("Password123")
        db.session.add(citizen)
        db.session.flush()
        r1 = Report(
            user_id=citizen.id, category_id=cat.id,
            description="d1", reference="ET-SUM01", status="Pending",
        )
        r2 = Report(
            user_id=citizen.id, category_id=cat.id,
            description="d2", reference="ET-SUM02", status="Completed",
        )
        db.session.add_all([r1, r2])
        db.session.commit()

        summary = AnalyticsService.dashboard_summary()
        assert summary["total"] == 2
        assert summary["pending"] == 1
        assert summary["completed"] == 1


def test_complaints_by_category(app):
    with app.app_context():
        from app.models.waste_category import WasteCategory
        from app.models.report import Report
        from app.models.user import User
        from app.services.analytics_service import AnalyticsService

        cat = WasteCategory.query.filter_by(category_name="Plastic Waste").first()
        citizen = User(
            full_name="Citizen", email="citizen2@example.com", role="Citizen"
        )
        citizen.set_password("Password123")
        db.session.add(citizen)
        db.session.flush()
        r1 = Report(
            user_id=citizen.id, category_id=cat.id,
            description="d1", reference="ET-CAT01", status="Pending",
        )
        r2 = Report(
            user_id=citizen.id, category_id=cat.id,
            description="d2", reference="ET-CAT02", status="Completed",
        )
        db.session.add_all([r1, r2])
        db.session.commit()

        result = AnalyticsService.complaints_by_category()
        assert "Plastic Waste" in result["labels"]
        assert result["data"][result["labels"].index("Plastic Waste")] == 2


def test_complaints_by_status(app):
    with app.app_context():
        from app.models.report import Report
        from app.models.user import User
        from app.services.analytics_service import AnalyticsService

        citizen = User(
            full_name="Citizen", email="citizen3@example.com", role="Citizen"
        )
        citizen.set_password("Password123")
        db.session.add(citizen)
        db.session.flush()
        r1 = Report(
            user_id=citizen.id, description="d1", reference="ET-ST01", status="Pending",
        )
        r2 = Report(
            user_id=citizen.id, description="d2", reference="ET-ST02", status="Completed",
        )
        db.session.add_all([r1, r2])
        db.session.commit()

        result = AnalyticsService.complaints_by_status()
        assert "Pending" in result["labels"]
        assert "Completed" in result["labels"]


def test_staff_performance(app):
    with app.app_context():
        from app.models.user import User, Role
        from app.models.report import Report
        from app.models.waste_category import WasteCategory
        from app.models.collection_task import CollectionTask, TaskStatus
        from app.services.analytics_service import AnalyticsService

        staff = User(
            full_name="Staff Perf", email="staffperf@example.com", role=Role.STAFF
        )
        staff.set_password("Password123")
        db.session.add(staff)
        db.session.flush()
        citizen = User(
            full_name="Citizen", email="citizenperf@example.com", role="Citizen"
        )
        citizen.set_password("Password123")
        db.session.add(citizen)
        db.session.flush()
        cat = WasteCategory.query.filter_by(category_name="Plastic Waste").first()
        report = Report(
            user_id=citizen.id, category_id=cat.id,
            description="d", reference="ET-PERF01", status="Verified",
        )
        db.session.add(report)
        db.session.flush()
        task = CollectionTask(
            report_id=report.id, staff_id=staff.id, assigned_by=staff.id,
            task_status=TaskStatus.COMPLETED,
        )
        db.session.add(task)
        db.session.commit()

        result = AnalyticsService.staff_performance()
        assert "Staff Perf" in result["labels"]
        idx = result["labels"].index("Staff Perf")
        assert result["total"][idx] == 1
        assert result["completed"][idx] == 1


def test_pending_vs_completed_tasks(app):
    with app.app_context():
        from app.models.user import User, Role
        from app.models.report import Report
        from app.models.waste_category import WasteCategory
        from app.models.collection_task import CollectionTask, TaskStatus
        from app.services.analytics_service import AnalyticsService

        staff = User(
            full_name="Staff PV", email="staffpv@example.com", role=Role.STAFF
        )
        staff.set_password("Password123")
        db.session.add(staff)
        db.session.flush()
        citizen = User(
            full_name="Citizen", email="citizenpv@example.com", role="Citizen"
        )
        citizen.set_password("Password123")
        db.session.add(citizen)
        db.session.flush()
        cat = WasteCategory.query.filter_by(category_name="Plastic Waste").first()
        report = Report(
            user_id=citizen.id, category_id=cat.id,
            description="d", reference="ET-PV01", status="Verified",
        )
        db.session.add(report)
        db.session.flush()
        task = CollectionTask(
            report_id=report.id, staff_id=staff.id, assigned_by=staff.id,
            task_status=TaskStatus.COMPLETED,
        )
        db.session.add(task)
        db.session.commit()

        result = AnalyticsService.pending_vs_completed_tasks()
        assert "Completed" in result["labels"]
        assert result["data"][result["labels"].index("Completed")] == 1
