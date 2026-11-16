"""Collection Staff routes: dashboard, tasks, task progress update."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.collection_task import CollectionTask
from app.services.staff_service import StaffService
from app.utils.decorators import staff_required

staff_bp = Blueprint("staff", __name__, url_prefix="/staff")


@staff_bp.route("/dashboard")
@login_required
@staff_required
def dashboard():
    stats = StaffService.dashboard_stats(current_user)
    recent_tasks = (
        CollectionTask.query.filter_by(staff_id=current_user.id)
        .order_by(CollectionTask.created_at.desc())
        .limit(5)
        .all()
    )
    return render_template(
        "staff/dashboard.html", stats=stats, recent_tasks=recent_tasks
    )


@staff_bp.route("/tasks")
@login_required
@staff_required
def tasks():
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    tasks = StaffService.get_staff_tasks(
        current_user, search=search or None, status=status or None
    )
    return render_template(
        "staff/tasks.html",
        tasks=tasks,
        search=search,
        status=status,
    )


@staff_bp.route("/tasks/<int:task_id>")
@login_required
@staff_required
def task_detail(task_id):
    task = StaffService.get_task_by_id(task_id, current_user)
    if task is None:
        flash("Task not found or not assigned to you.", "danger")
        return redirect(url_for("staff.tasks"))
    return render_template("staff/task_detail.html", task=task)


@staff_bp.route("/tasks/<int:task_id>/update", methods=["POST"])
@login_required
@staff_required
def update_task(task_id):
    new_status = request.form.get("status", "").strip()
    remarks = request.form.get("remarks", "").strip()
    try:
        StaffService.update_task_progress(task_id, current_user, new_status, remarks)
        flash(f"Task #{task_id} updated to '{new_status}'.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("staff.task_detail", task_id=task_id))
