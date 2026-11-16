from app.extensions import db
from app.utils.datetime import utc_now


class AwarenessArticle(db.Model):
    __tablename__ = "awareness_articles"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(100), nullable=True)
    is_published = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(
        db.DateTime,
        default=utc_now,
        onupdate=utc_now,
    )

    def __repr__(self):
        return f"<AwarenessArticle {self.title}>"
