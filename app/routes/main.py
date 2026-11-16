from flask import Blueprint, current_app
from sqlalchemy import text

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    from flask import render_template
    return render_template("index.html")


@main_bp.route("/health")
def health():
    db_status = "ok"
    try:
        from app.extensions import db
        db.session.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - health check
        db_status = f"error: {exc}"
        current_app.logger.error("Database health check failed: %s", exc)
    return {
        "status": "ok",
        "database": db_status,
        "app": "EcoTrack",
    }, 200
