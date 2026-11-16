from app.extensions import db


class Location(db.Model):
    __tablename__ = "locations"

    id = db.Column(db.Integer, primary_key=True)
    address_text = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    reports = db.relationship("Report", back_populates="location", lazy=True)

    def __repr__(self):
        return f"<Location {self.address_text}>"
