from flask_login import UserMixin
from app.extensions import db
from app.utils.datetime import utc_now


class Role:
    CITIZEN = "Citizen"
    ADMINISTRATOR = "Administrator"
    STAFF = "Staff"
    choices = [(CITIZEN, "Citizen"), (ADMINISTRATOR, "Administrator"), (STAFF, "Collection Staff")]


class ReportStatus:
    PENDING = "Pending"
    VERIFIED = "Verified"
    REJECTED = "Rejected"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    choices = [
        (PENDING, "Pending"),
        (VERIFIED, "Verified"),
        (REJECTED, "Rejected"),
        (ASSIGNED, "Assigned"),
        (IN_PROGRESS, "In Progress"),
        (COMPLETED, "Completed"),
    ]


class TaskStatus:
    ASSIGNED = "Assigned"
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    OVERDUE = "Overdue"
    choices = [
        (ASSIGNED, "Assigned"),
        (PENDING, "Pending"),
        (IN_PROGRESS, "In Progress"),
        (COMPLETED, "Completed"),
        (OVERDUE, "Overdue"),
    ]


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.CITIZEN)
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(
        db.DateTime,
        default=utc_now,
        onupdate=utc_now,
    )

    reports = db.relationship(
        "Report", back_populates="citizen", lazy=True, foreign_keys="Report.user_id"
    )
    staff_profile = db.relationship(
        "Staff", back_populates="user", lazy=True, uselist=False, foreign_keys="Staff.user_id"
    )
    tasks_assigned = db.relationship(
        "CollectionTask", back_populates="staff", lazy=True, foreign_keys="CollectionTask.staff_id"
    )
    tasks_assigned_by = db.relationship(
        "CollectionTask",
        back_populates="assigning_admin",
        lazy=True,
        foreign_keys="CollectionTask.assigned_by",
    )
    task_updates = db.relationship(
        "TaskUpdate",
        back_populates="updated_by_user",
        lazy=True,
        foreign_keys="TaskUpdate.updated_by",
    )
    status_history_updates = db.relationship(
        "ReportStatusHistory",
        back_populates="updated_by_user",
        lazy=True,
        foreign_keys="ReportStatusHistory.updated_by",
    )

    def set_password(self, password):
        from werkzeug.security import generate_password_hash

        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash

        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == Role.ADMINISTRATOR

    def is_staff(self):
        return self.role == Role.STAFF

    def is_citizen(self):
        return self.role == Role.CITIZEN

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
