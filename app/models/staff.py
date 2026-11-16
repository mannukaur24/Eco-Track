from app.extensions import db


class Staff(db.Model):
    __tablename__ = "staff"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    availability = db.Column(db.String(50), nullable=True)
    service_area = db.Column(db.String(120), nullable=True)

    user = db.relationship("User", back_populates="staff_profile", foreign_keys=[user_id])

    def __repr__(self):
        return f"<Staff {self.user_id}>"
