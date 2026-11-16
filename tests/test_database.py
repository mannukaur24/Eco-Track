"""Database tests for EcoTrack models.

These run against the in-memory SQLite TestingConfig and verify:
- record creation
- relationships
- constraints
- foreign keys
- unique fields
- status values
"""

import pytest
from app.extensions import db
from app.models.user import User, Role, ReportStatus, TaskStatus
from app.models.staff import Staff
from app.models.waste_category import WasteCategory
from app.models.location import Location
from app.models.report import Report
from app.models.collection_task import CollectionTask
from app.models.task_update import TaskUpdate
from app.models.awareness_article import AwarenessArticle


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield


def _add_user(email, role=Role.CITIZEN, full_name="User", password="Pass1234"):
    user = User(full_name=full_name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    return user


def test_user_creation(app_ctx):
    user = _add_user("alice@example.com", Role.CITIZEN, "Alice Citizen", "SecurePass123")
    assert user.id is not None
    assert user.created_at is not None
    assert user.is_active is True
    fetched = User.query.filter_by(email="alice@example.com").first()
    assert fetched is not None
    assert fetched.check_password("SecurePass123")
    assert not fetched.check_password("wrong")


def test_user_email_unique(app_ctx):
    db.session.add(User(full_name="One", email="unique@example.com", role=Role.CITIZEN))
    db.session.add(User(full_name="Two", email="unique@example.com", role=Role.CITIZEN))
    with pytest.raises(Exception):
        db.session.commit()


def test_user_roles(app_ctx):
    citizen = _add_user("c@example.com", Role.CITIZEN, "C")
    admin = _add_user("a@example.com", Role.ADMINISTRATOR, "A")
    staff = _add_user("s@example.com", Role.STAFF, "S")
    assert citizen.is_citizen() and not citizen.is_admin()
    assert admin.is_admin() and not admin.is_citizen()
    assert staff.is_staff() and not staff.is_admin()


def test_staff_relationship(app_ctx):
    user = _add_user("staffperson@example.com", Role.STAFF, "Staff Person")
    staff = Staff(user_id=user.id, availability="Mon-Fri", service_area="Zone A")
    db.session.add(staff)
    db.session.commit()
    assert staff.user.id == user.id
    assert user.staff_profile is not None


def test_waste_category_unique(app_ctx):
    db.session.add(WasteCategory(category_name="Plastic Waste", description="Plastic"))
    db.session.add(WasteCategory(category_name="Plastic Waste", description="Dup"))
    with pytest.raises(Exception):
        db.session.commit()


def test_location_creation(app_ctx):
    loc = Location(
        address_text="123 Main Street",
        latitude=28.6139,
        longitude=77.2090,
    )
    db.session.add(loc)
    db.session.commit()
    assert loc.id is not None


def test_report_creation_and_relationships(app_ctx):
    user = _add_user("r@example.com", Role.CITIZEN, "Reporter")
    category = WasteCategory.query.filter_by(category_name="Organic Waste").first()
    location = Location(address_text="456 Park Ave")
    db.session.add(location)
    db.session.flush()

    report = Report(
        user_id=user.id,
        category_id=category.id,
        location_id=location.id,
        description="Overflowing bin",
        status=ReportStatus.PENDING,
        reference="RT-0001",
    )
    db.session.add(report)
    db.session.commit()

    assert report.id is not None
    assert report.reference == "RT-0001"
    assert report.citizen.id == user.id
    assert report.category.category_name == "Organic Waste"
    assert report.location.address_text == "456 Park Ave"
    assert report.status == ReportStatus.PENDING


def test_report_reference_unique(app_ctx):
    user = _add_user("r2@example.com", Role.CITIZEN, "R")
    db.session.add(Report(
        user_id=user.id, description="One", reference="REF-UNIQUE",
    ))
    db.session.add(Report(
        user_id=user.id, description="Two", reference="REF-UNIQUE",
    ))
    with pytest.raises(Exception):
        db.session.commit()


def test_collection_task_and_updates(app_ctx):
    user = _add_user("rt@example.com", Role.CITIZEN, "Reporter")
    staff_user = _add_user("w@example.com", Role.STAFF, "Worker")
    admin_user = _add_user("ad@example.com", Role.ADMINISTRATOR, "Admin")
    report = Report(user_id=user.id, description="d", reference="T-001")
    db.session.add(report)
    db.session.flush()

    task = CollectionTask(
        report_id=report.id,
        staff_id=staff_user.id,
        assigned_by=admin_user.id,
        task_status=TaskStatus.PENDING,
        instructions="Collect by Friday",
    )
    db.session.add(task)
    db.session.flush()

    update = TaskUpdate(
        task_id=task.id,
        updated_by=staff_user.id,
        status=TaskStatus.IN_PROGRESS,
        remarks="On the way",
    )
    db.session.add(update)
    db.session.commit()

    assert task.id is not None
    assert task.report.id == report.id
    assert task.staff.id == staff_user.id
    assert task.assigning_admin.id == admin_user.id
    assert len(task.updates) == 1
    assert task.updates[0].status == TaskStatus.IN_PROGRESS


def test_awareness_article(app_ctx):
    article = AwarenessArticle(
        title="Recycling Tips",
        content="Recycle paper and plastic.",
        topic="Recycling",
        is_published=True,
    )
    db.session.add(article)
    db.session.commit()
    assert article.id is not None
    assert article.is_published is True
    assert article.created_at is not None


def test_status_values(app_ctx):
    assert ReportStatus.PENDING == "Pending"
    assert ReportStatus.COMPLETED == "Completed"
    assert TaskStatus.OVERDUE == "Overdue"
    assert TaskStatus.COMPLETED == "Completed"
