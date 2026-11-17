from app.extensions import db


class WasteCategory(db.Model):
    __tablename__ = "waste_categories"

    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)

    reports = db.relationship("Report", back_populates="category", lazy=True)

    def __repr__(self):
        return f"<WasteCategory {self.category_name}>"
