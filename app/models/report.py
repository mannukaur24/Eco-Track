from datetime import datetime, timezone
from app.extensions import db


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category_id = db.Column(
        db.Integer, db.ForeignKey("waste_categories.id", ondelete="SET NULL"), nullable=True
    )
    location_id = db.Column(
        db.Integer, db.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )
    description = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Pending")
    rejection_reason = db.Column(db.Text, nullable=True)
    reference = db.Column(db.String(20), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    citizen = db.relationship("User", back_populates="reports", foreign_keys=[user_id])
    category = db.relationship(
        "WasteCategory", back_populates="reports", foreign_keys=[category_id]
    )
    location = db.relationship("Location", back_populates="reports", foreign_keys=[location_id])
    tasks = db.relationship(
        "CollectionTask",
        back_populates="report",
        lazy=True,
        foreign_keys="CollectionTask.report_id",
    )

    def __repr__(self):
        return f"<Report {self.reference or self.id}>"
