"""Citizen routes: dashboard, complaint submission, history, detail."""

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models.report import Report
from app.models.waste_category import WasteCategory
from app.services.complaint_service import ComplaintService
from app.utils.uploads import UploadError
from app.utils.decorators import citizen_required

citizen_bp = Blueprint("citizen", __name__, url_prefix="/citizen")


@citizen_bp.route("/dashboard")
@login_required
@citizen_required
def dashboard():
    stats = ComplaintService.dashboard_stats(current_user)
    recent = (
        Report.query.filter_by(user_id=current_user.id)
        .order_by(Report.created_at.desc())
        .limit(5)
        .all()
    )
    return render_template("citizen/dashboard.html", stats=stats, recent=recent)


@citizen_bp.route("/submit", methods=["GET", "POST"])
@login_required
@citizen_required
def submit():
    categories = WasteCategory.query.order_by(WasteCategory.category_name).all()
    if request.method == "POST":
        form_data = {
            "category_id": request.form.get("category_id"),
            "description": request.form.get("description"),
            "address_text": request.form.get("address_text"),
            "latitude": request.form.get("latitude"),
            "longitude": request.form.get("longitude"),
            "additional_info": request.form.get("additional_info"),
        }
        image_file = request.files.get("image")
        try:
            report = ComplaintService.create_report(
                current_user, form_data, image_file, current_app.config["UPLOAD_FOLDER"]
            )
            flash(
                f"Complaint submitted successfully. Reference: {report.reference}",
                "success",
            )
            return redirect(url_for("citizen.detail", reference=report.reference))
        except UploadError as exc:
            flash(str(exc), "danger")
        except ValueError as exc:
            flash(str(exc), "danger")
    return render_template("citizen/submit.html", categories=categories)


@citizen_bp.route("/history")
@login_required
@citizen_required
def history():
    status_filter = request.args.get("status")
    search = request.args.get("search")
    reports = ComplaintService.get_user_reports(
        current_user, status_filter=status_filter, search=search
    )
    return render_template(
        "citizen/history.html",
        reports=reports,
        status_filter=status_filter or "",
        search=search or "",
    )


@citizen_bp.route("/complaint/<reference>")
@login_required
@citizen_required
def detail(reference):
    report = ComplaintService.get_report_by_reference(reference, current_user)
    if report is None:
        flash("Complaint not found or you do not have access to it.", "danger")
        return redirect(url_for("citizen.history"))
    return render_template("citizen/detail.html", report=report)
