"""Collection Staff portal tests."""

import pytest
from app import create_app
from app.extensions import db
from app.models.user import User, Role, ReportStatus, TaskStatus
from app.models.report import Report
from app.models.waste_category import WasteCategory
from app.models.collection_task import CollectionTask
from app.models.task_update import TaskUpdate


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        cats = ["Organic Waste", "Plastic Waste", "Other"]
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
    client.get("/auth/logout", follow_redirects=True)
    _login(client, email, "AdminPass123")
    return admin


def _make_staff(app, client, email="staff@example.com", full_name="Staff Worker"):
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
            from app.models.staff import Staff
            db.session.add(Staff(user_id=user.id, availability="Mon-Fri", service_area="Zone A"))
            db.session.commit()
    client.get("/auth/logout", follow_redirects=True)
    _login(client, email, "StaffPass123")
    return user


def _make_verified_complaint(app, client, email="citizen@example.com", reference_override=None):
    """Create a citizen, submit a complaint, verify it as admin. Returns (citizen_user, report)."""
    # Register citizen
    client.get("/auth/logout", follow_redirects=True)
    _register(client, email, "Citizen User", role="Citizen")
    _login(client, email)
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
        user = User.query.filter_by(email=email).first()
        report = Report.query.filter_by(user_id=user.id).first()
        report.status = ReportStatus.VERIFIED
        db.session.commit()
        return user, report


def test_staff_dashboard_requires_staff(client, app):
    # Citizen should be denied
    _register(client, "citizen@example.com", "Citizen User", role="Citizen")
    _login(client, "citizen@example.com")
    response = client.get("/staff/dashboard", follow_redirects=True)
    assert response.status_code == 403 or b"permission" in response.data.lower()


def test_admin_cannot_access_staff(client, app):
    _make_admin(app, client)
    response = client.get("/staff/dashboard", follow_redirects=True)
    assert response.status_code == 403 or b"permission" in response.data.lower()


def test_staff_dashboard_access(client, app):
    _make_staff(app, client)
    response = client.get("/staff/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"Collection Staff Dashboard" in response.data


def test_staff_task_visibility_own_tasks_only(client, app):
    """Staff A sees only their own tasks, not Staff B's."""
    # Create two staff members
    with app.app_context():
        staff_a = User(full_name="Staff A", email="staff_a@example.com", role=Role.STAFF)
        staff_a.set_password("Pass1234")
        db.session.add(staff_a)
        db.session.flush()
        from app.models.staff import Staff
        db.session.add(Staff(user_id=staff_a.id))
        staff_b = User(full_name="Staff B", email="staff_b@example.com", role=Role.STAFF)
        staff_b.set_password("Pass1234")
        db.session.add(staff_b)
        db.session.flush()
        db.session.add(Staff(user_id=staff_b.id))

        # Create a verified complaint
        citizen = User(full_name="Citizen", email="citizen@example.com", role=Role.CITIZEN)
        citizen.set_password("Pass1234")
        db.session.add(citizen)
        db.session.flush()
        cat = WasteCategory.query.filter_by(category_name="Organic Waste").first()
        report = Report(
            user_id=citizen.id,
            category_id=cat.id,
            description="d",
            reference="ET-VISIB01",
            status=ReportStatus.VERIFIED,
        )
        db.session.add(report)
        db.session.flush()

        # Assign task to staff_a
        task_a = CollectionTask(
            report_id=report.id,
            staff_id=staff_a.id,
            assigned_by=staff_a.id,
            task_status=TaskStatus.ASSIGNED,
        )
        db.session.add(task_a)

        # Assign a different task to staff_b (different complaint)
        report_b = Report(
            user_id=citizen.id,
            category_id=cat.id,
            description="d2",
            reference="ET-VISIB02",
            status=ReportStatus.VERIFIED,
        )
        db.session.add(report_b)
        db.session.flush()
        task_b = CollectionTask(
            report_id=report_b.id,
            staff_id=staff_b.id,
            assigned_by=staff_b.id,
            task_status=TaskStatus.ASSIGNED,
        )
        db.session.add(task_b)
        db.session.commit()

    # Login as staff_a
    client.get("/auth/logout", follow_redirects=True)
    _login(client, "staff_a@example.com", "Pass1234")
    response = client.get("/staff/tasks", follow_redirects=True)
    assert response.status_code == 200
    assert b"ET-VISIB01" in response.data
    assert b"ET-VISIB02" not in response.data


def test_staff_cannot_access_other_staff_task(client, app):
    """Staff A cannot view/update a task assigned to Staff B."""
    with app.app_context():
        staff_a = User(full_name="Staff A", email="staff_a2@example.com", role=Role.STAFF)
        staff_a.set_password("Pass1234")
        db.session.add(staff_a)
        db.session.flush()
        from app.models.staff import Staff
        db.session.add(Staff(user_id=staff_a.id))
        staff_b = User(full_name="Staff B", email="staff_b2@example.com", role=Role.STAFF)
        staff_b.set_password("Pass1234")
        db.session.add(staff_b)
        db.session.flush()
        db.session.add(Staff(user_id=staff_b.id))

        citizen = User(full_name="Citizen", email="citizen2@example.com", role=Role.CITIZEN)
        citizen.set_password("Pass1234")
        db.session.add(citizen)
        db.session.flush()
        cat = WasteCategory.query.filter_by(category_name="Organic Waste").first()
        report = Report(
            user_id=citizen.id,
            category_id=cat.id,
            description="d",
            reference="ET-OTHER01",
            status=ReportStatus.VERIFIED,
        )
        db.session.add(report)
        db.session.flush()
        task_b = CollectionTask(
            report_id=report.id,
            staff_id=staff_b.id,
            assigned_by=staff_b.id,
            task_status=TaskStatus.ASSIGNED,
        )
        db.session.add(task_b)
        db.session.commit()
        task_b_id = task_b.id

    # Login as staff_a and try to access staff_b's task
    client.get("/auth/logout", follow_redirects=True)
    _login(client, "staff_a2@example.com", "Pass1234")
    response = client.get(f"/staff/tasks/{task_b_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"not found or not assigned to you" in response.data.lower()


def test_staff_progress_update_assigned_to_in_progress(client, app):
    """Staff can update task from Assigned to In Progress."""
    _make_staff(app, client, email="staff_prog@example.com", full_name="Staff Prog")
    staff_user = User.query.filter_by(email="staff_prog@example.com").first()

    with app.app_context():
        admin = User.query.filter_by(email="admin@example.com").first()
        if admin is None:
            admin = User(full_name="Admin", email="admin@example.com", role=Role.ADMINISTRATOR)
            admin.set_password("AdminPass123")
            db.session.add(admin)
            db.session.flush()
        citizen = User(full_name="Citizen", email="citizen_prog@example.com", role=Role.CITIZEN)
        citizen.set_password("Pass1234")
        db.session.add(citizen)
        db.session.flush()
        cat = WasteCategory.query.filter_by(category_name="Organic Waste").first()
        report = Report(
            user_id=citizen.id,
            category_id=cat.id,
            description="Garbage piled up for many days.",
            reference="ET-PROG01",
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

    response = client.post(
        f"/staff/tasks/{task_id}/update",
        data={"status": "In Progress", "remarks": "Started collection."},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Task #" in response.data
    with app.app_context():
        updated = db.session.get(CollectionTask, task_id)
        assert updated.task_status == TaskStatus.IN_PROGRESS
        # TaskUpdate recorded
        update = TaskUpdate.query.filter_by(task_id=task_id).first()
        assert update is not None
        assert update.status == TaskStatus.IN_PROGRESS
        assert update.updated_by == staff_user.id


def test_staff_completion_workflow_and_complaint_sync(client, app):
    """Completing a task updates complaint status to Completed."""
    _make_staff(app, client, email="staff_complete@example.com", full_name="Staff Complete")
    staff_user = User.query.filter_by(email="staff_complete@example.com").first()

    with app.app_context():
        admin = User.query.filter_by(email="admin@example.com").first()
        if admin is None:
            admin = User(full_name="Admin", email="admin@example.com", role=Role.ADMINISTRATOR)
            admin.set_password("AdminPass123")
            db.session.add(admin)
            db.session.flush()
        citizen = User(full_name="Citizen", email="citizen_complete@example.com", role=Role.CITIZEN)
        citizen.set_password("Pass1234")
        db.session.add(citizen)
        db.session.flush()
        cat = WasteCategory.query.filter_by(category_name="Organic Waste").first()
        report = Report(
            user_id=citizen.id,
            category_id=cat.id,
            description="Garbage piled up for many days.",
            reference="ET-COMP01",
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
        report_id = report.id

    # Move to In Progress
    client.post(
        f"/staff/tasks/{task_id}/update",
        data={"status": "In Progress", "remarks": "On the way."},
        follow_redirects=True,
    )
    # Complete
    response = client.post(
        f"/staff/tasks/{task_id}/update",
        data={"status": "Completed", "remarks": "Collected all garbage."},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        updated_task = db.session.get(CollectionTask, task_id)
        assert updated_task.task_status == TaskStatus.COMPLETED
        assert updated_task.completed_at is not None
        # Complaint synced to Completed
        updated_report = db.session.get(Report, report_id)
        assert updated_report.status == ReportStatus.COMPLETED
        # TaskUpdate recorded for completion
        updates = TaskUpdate.query.filter_by(task_id=task_id).all()
        assert len(updates) == 2
        assert updates[-1].status == TaskStatus.COMPLETED


def test_staff_invalid_transition(client, app):
    """Staff cannot skip from Assigned directly... actually they can to Completed per service.
    Test that Completed -> anything is blocked."""
    _make_staff(app, client, email="staff_transition@example.com", full_name="Staff Transition")
    staff_user = User.query.filter_by(email="staff_transition@example.com").first()

    with app.app_context():
        admin = User.query.filter_by(email="admin@example.com").first()
        if admin is None:
            admin = User(full_name="Admin", email="admin@example.com", role=Role.ADMINISTRATOR)
            admin.set_password("AdminPass123")
            db.session.add(admin)
            db.session.flush()
        citizen = User(
            full_name="Citizen", email="citizen_transition@example.com", role=Role.CITIZEN
        )
        citizen.set_password("Pass1234")
        db.session.add(citizen)
        db.session.flush()
        cat = WasteCategory.query.filter_by(category_name="Organic Waste").first()
        report = Report(
            user_id=citizen.id,
            category_id=cat.id,
            description="d",
            reference="ET-TRANS01",
            status=ReportStatus.VERIFIED,
        )
        db.session.add(report)
        db.session.flush()
        task = CollectionTask(
            report_id=report.id,
            staff_id=staff_user.id,
            assigned_by=admin.id,
            task_status=TaskStatus.COMPLETED,
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    # Try to move Completed -> In Progress (should fail)
    response = client.post(
        f"/staff/tasks/{task_id}/update",
        data={"status": "In Progress", "remarks": "Trying to reopen."},
        follow_redirects=True,
    )
    assert b"Cannot move task" in response.data


def test_staff_task_history(client, app):
    """Staff can view task history/updates."""
    _make_staff(app, client, email="staff_history@example.com", full_name="Staff History")
    staff_user = User.query.filter_by(email="staff_history@example.com").first()

    with app.app_context():
        admin = User.query.filter_by(email="admin@example.com").first()
        if admin is None:
            admin = User(full_name="Admin", email="admin@example.com", role=Role.ADMINISTRATOR)
            admin.set_password("AdminPass123")
            db.session.add(admin)
            db.session.flush()
        citizen = User(full_name="Citizen", email="citizen_history@example.com", role=Role.CITIZEN)
        citizen.set_password("Pass1234")
        db.session.add(citizen)
        db.session.flush()
        cat = WasteCategory.query.filter_by(category_name="Organic Waste").first()
        report = Report(
            user_id=citizen.id,
            category_id=cat.id,
            description="d",
            reference="ET-HIST01",
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
        db.session.flush()
        # Add a manual update
        db.session.add(TaskUpdate(
            task_id=task.id,
            updated_by=staff_user.id,
            status=TaskStatus.IN_PROGRESS,
            remarks="Started work.",
        ))
        db.session.commit()
        task_id = task.id

    response = client.get(f"/staff/tasks/{task_id}", follow_redirects=True)
    assert response.status_code == 200
    assert b"Task History" in response.data
    assert b"Started work" in response.data
