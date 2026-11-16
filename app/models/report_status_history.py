"""Complaint status history model for EcoTrack.

Records an immutable audit trail of complaint status changes:
report ID, previous status, new status, updated-by user ID, timestamp,
and remarks. Records are only created when a real status transition
occurs; no historical records are fabricated.
"""

from app.extensions import db
from app.utils.datetime import utc_now


class ReportStatusHistory(db.Model):
    __tablename__ = "report_status_history"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(
        db.Integer, db.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=False)
    updated_by = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    report = db.relationship("Report", back_populates="status_history", foreign_keys=[report_id])
    updated_by_user = db.relationship(
        "User", back_populates="status_history_updates", foreign_keys=[updated_by]
    )

    def __repr__(self):
        return f"<ReportStatusHistory report={self.report_id} {self.previous_status} -> {self.new_status}>"
