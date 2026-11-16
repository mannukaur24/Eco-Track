"""Administrator routes: dashboard, complaints, tasks, staff, categories, awareness."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.report import Report
from app.services.admin_service import AdminService
from app.utils.decorators import administrator_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required
@administrator_required
def dashboard():
    stats = AdminService.dashboard_stats()
    recent_complaints = (
        Report.query.order_by(Report.created_at.desc()).limit(10).all()
    )
    return render_template(
        "admin/dashboard.html", stats=stats, recent_complaints=recent_complaints
    )


@admin_bp.route("/complaints")
@login_required
@administrator_required
def complaints():
    search = request.args.get("search", "").strip()
    category_id = request.args.get("category_id", type=int)
    status = request.args.get("status", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    complaints = AdminService.get_complaints(
        search=search or None,
        category_id=category_id,
        status=status or None,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    categories = AdminService.get_categories()
    return render_template(
        "admin/complaints.html",
        complaints=complaints,
        categories=categories,
        search=search,
        category_id=category_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )


@admin_bp.route("/complaints/<reference>/verify", methods=["POST"])
@login_required
@administrator_required
def verify_complaint(reference):
    try:
        AdminService.verify_complaint(reference, current_user)
        flash(f"Complaint {reference} verified.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.complaints"))


@admin_bp.route("/complaints/<reference>/reject", methods=["POST"])
@login_required
@administrator_required
def reject_complaint(reference):
    reason = request.form.get("rejection_reason", "").strip()
    try:
        AdminService.reject_complaint(reference, reason, current_user)
        flash(f"Complaint {reference} rejected.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.complaints"))


@admin_bp.route("/complaints/<reference>")
@login_required
@administrator_required
def complaint_detail(reference):
    complaint = AdminService.get_complaint_by_reference(reference)
    if complaint is None:
        flash("Complaint not found.", "danger")
        return redirect(url_for("admin.complaints"))
    staff = AdminService.get_active_staff()
    return render_template(
        "admin/complaint_detail.html",
        complaint=complaint,
        staff=staff,
    )


@admin_bp.route("/tasks/assign", methods=["POST"])
@login_required
@administrator_required
def assign_task():
    reference = request.form.get("reference", "").strip()
    staff_id = request.form.get("staff_id", type=int)
    due_date = request.form.get("due_date", "").strip()
    instructions = request.form.get("instructions", "").strip()
    try:
        AdminService.assign_task(reference, staff_id, due_date, instructions, current_user)
        flash(f"Task assigned for complaint {reference}.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.complaint_detail", reference=reference))


@admin_bp.route("/staff")
@login_required
@administrator_required
def staff_management():
    staff_members = AdminService.get_staff_members()
    return render_template("admin/staff.html", staff_members=staff_members)


@admin_bp.route("/staff/add", methods=["POST"])
@login_required
@administrator_required
def add_staff():
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    availability = request.form.get("availability", "").strip()
    service_area = request.form.get("service_area", "").strip()
    password = request.form.get("password", "").strip()
    try:
        AdminService.create_staff(
            full_name, email, phone, availability, service_area, password
        )
        flash("Staff member added.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.staff_management"))


@admin_bp.route("/staff/<int:user_id>/toggle", methods=["POST"])
@login_required
@administrator_required
def toggle_staff(user_id):
    try:
        user = AdminService.toggle_staff_active(user_id)
        status = "activated" if user.is_active else "deactivated"
        flash(f"Staff member {user.full_name} {status}.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.staff_management"))


@admin_bp.route("/staff/<int:user_id>/edit", methods=["POST"])
@login_required
@administrator_required
def edit_staff(user_id):
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    availability = request.form.get("availability", "").strip()
    service_area = request.form.get("service_area", "").strip()
    try:
        AdminService.update_staff(user_id, full_name, phone, availability, service_area)
        flash("Staff member updated.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.staff_management"))


@admin_bp.route("/categories")
@login_required
@administrator_required
def categories():
    cats = AdminService.get_categories()
    return render_template("admin/categories.html", categories=cats)


@admin_bp.route("/categories/add", methods=["POST"])
@login_required
@administrator_required
def add_category():
    name = request.form.get("category_name", "").strip()
    description = request.form.get("description", "").strip()
    try:
        AdminService.create_category(name, description)
        flash("Category added.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categories/<int:category_id>/edit", methods=["POST"])
@login_required
@administrator_required
def edit_category(category_id):
    name = request.form.get("category_name", "").strip()
    description = request.form.get("description", "").strip()
    try:
        AdminService.update_category(category_id, name, description)
        flash("Category updated.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@login_required
@administrator_required
def delete_category(category_id):
    try:
        AdminService.delete_category(category_id)
        flash("Category deleted.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/awareness")
@login_required
@administrator_required
def awareness():
    articles = AdminService.get_articles()
    return render_template("admin/awareness.html", articles=articles)


@admin_bp.route("/awareness/add", methods=["POST"])
@login_required
@administrator_required
def add_article():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    topic = request.form.get("topic", "").strip()
    is_published = "is_published" in request.form
    try:
        AdminService.create_article(title, content, topic, is_published)
        flash("Article created.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.awareness"))


@admin_bp.route("/awareness/<int:article_id>/edit", methods=["POST"])
@login_required
@administrator_required
def edit_article(article_id):
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    topic = request.form.get("topic", "").strip()
    is_published = "is_published" in request.form
    try:
        AdminService.update_article(article_id, title, content, topic, is_published)
        flash("Article updated.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.awareness"))


@admin_bp.route("/awareness/<int:article_id>/toggle", methods=["POST"])
@login_required
@administrator_required
def toggle_article(article_id):
    try:
        AdminService.toggle_publish(article_id)
        flash("Article publication status updated.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.awareness"))


@admin_bp.route("/awareness/<int:article_id>/delete", methods=["POST"])
@login_required
@administrator_required
def delete_article(article_id):
    try:
        AdminService.delete_article(article_id)
        flash("Article deleted.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.awareness"))
