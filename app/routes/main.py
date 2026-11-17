from flask import Blueprint, current_app, abort, send_from_directory, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import text
import os

from app.models.report import Report
from app.models.collection_task import CollectionTask

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    from flask import render_template
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """Centralized dashboard redirect endpoint based on the user's role.

    Unauthenticated users are handled by Flask-Login (redirect to login).
    Inactive accounts cannot reach a protected dashboard.
    """
    if not current_user.is_active:
        flash("Your account has been deactivated. Contact an administrator.", "danger")
        return redirect(url_for("auth.login"))
    if current_user.is_admin():
        return redirect(url_for("admin.dashboard"))
    if current_user.is_staff():
        return redirect(url_for("staff.dashboard"))
    if current_user.is_citizen():
        return redirect(url_for("citizen.dashboard"))
    flash("You do not have permission to access the dashboard.", "danger")
    return abort(403)


@main_bp.route("/health")
def health():
    db_status = "ok"
    try:
        from app.extensions import db
        db.session.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - health check
        current_app.logger.error("Database health check failed: %s", exc)
        return {
            "status": "fail",
            "database": "unavailable",
            "app": "EcoTrack",
        }, 503
    return {
        "status": "ok",
        "database": db_status,
        "app": "EcoTrack",
    }, 200


@main_bp.route("/uploads/<path:filename>")
@login_required
def serve_uploaded_image(filename):
    """Serve a private complaint image only to authorized users.

    Authorized to view a complaint's image:
    - the citizen who owns the complaint,
    - an administrator,
    - the staff member assigned to the complaint's collection task.
    """
    if not filename or ".." in filename or filename.startswith("/") or "\\" in filename:
        abort(404)

    safe_name = os.path.basename(filename)
    if safe_name != filename:
        abort(404)

    upload_folder = os.path.abspath(current_app.config["UPLOAD_FOLDER"])
    dest_path = os.path.abspath(os.path.join(upload_folder, safe_name))
    if not dest_path.startswith(upload_folder + os.sep):
        abort(404)
    if not os.path.isfile(dest_path):
        abort(404)

    image_path = "uploads/" + safe_name
    report = Report.query.filter_by(image_path=image_path).first()
    if report is None:
        abort(404)

    authorized = False
    if current_user.is_admin():
        authorized = True
    elif current_user.is_citizen() and report.user_id == current_user.id:
        authorized = True
    elif current_user.is_staff():
        assigned = CollectionTask.query.filter_by(
            report_id=report.id, staff_id=current_user.id
        ).first()
        if assigned is not None:
            authorized = True

    if not authorized:
        abort(403)

    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    mimetype = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
    }.get(ext, "application/octet-stream")
    return send_from_directory(upload_folder, safe_name, mimetype=mimetype)
