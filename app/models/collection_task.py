from app.models.user import TaskStatus
from app.extensions import db
from app.utils.datetime import utc_now


class CollectionTask(db.Model):
    __tablename__ = "collection_tasks"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(
        db.Integer, db.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
    )
    staff_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_date = db.Column(db.DateTime, nullable=True)
    task_status = db.Column(db.String(20), nullable=False, default=TaskStatus.ASSIGNED)
    instructions = db.Column(db.Text, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(
        db.DateTime,
        default=utc_now,
        onupdate=utc_now,
    )

    report = db.relationship("Report", back_populates="tasks", foreign_keys=[report_id])
    staff = db.relationship("User", back_populates="tasks_assigned", foreign_keys=[staff_id])
    assigning_admin = db.relationship(
        "User", back_populates="tasks_assigned_by", foreign_keys=[assigned_by]
    )
    updates = db.relationship(
        "TaskUpdate", back_populates="task", lazy=True, foreign_keys="TaskUpdate.task_id"
    )

    def __repr__(self):
        return f"<CollectionTask {self.id}>"
