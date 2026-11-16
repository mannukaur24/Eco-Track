from datetime import datetime, timezone
from app.extensions import db


class TaskUpdate(db.Model):
    __tablename__ = "task_updates"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer, db.ForeignKey("collection_tasks.id", ondelete="CASCADE"), nullable=False
    )
    updated_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status = db.Column(db.String(20), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    task = db.relationship("CollectionTask", back_populates="updates", foreign_keys=[task_id])
    updated_by_user = db.relationship(
        "User", back_populates="task_updates", foreign_keys=[updated_by]
    )

    def __repr__(self):
        return f"<TaskUpdate {self.id}>"
