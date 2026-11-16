"""Administrator analytics, maps, and reporting routes.

All routes require administrator authorization. Provides:
- Analytics dashboard with Chart.js visualizations.
- Complaint location map (Leaflet + OpenStreetMap).
- CSV downloads for 7 report types.
"""

from flask import Blueprint, render_template, request
from flask_login import login_required
from app.services.analytics_service import AnalyticsService
from app.services.reports_service import ReportsService
from app.utils.decorators import administrator_required

analytics_bp = Blueprint("admin_analytics", __name__, url_prefix="/admin")


@analytics_bp.route("/analytics")
@login_required
@administrator_required
def analytics():
    preset = request.args.get("preset", "30days")
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    summary = AnalyticsService.dashboard_summary(preset, date_from, date_to)
    by_category = AnalyticsService.complaints_by_category(preset, date_from, date_to)
    by_status = AnalyticsService.complaints_by_status(preset, date_from, date_to)
    monthly_sub = AnalyticsService.monthly_submissions()
    monthly_res = AnalyticsService.monthly_resolved()
    staff_perf = AnalyticsService.staff_performance()
    pending_vs_completed = AnalyticsService.pending_vs_completed_tasks()
    by_location = AnalyticsService.complaints_by_location()

    return render_template(
        "admin/analytics.html",
        summary=summary,
        by_category=by_category,
        by_status=by_status,
        monthly_sub=monthly_sub,
        monthly_res=monthly_res,
        staff_perf=staff_perf,
        pending_vs_completed=pending_vs_completed,
        by_location=by_location,
        preset=preset,
        date_from=date_from,
        date_to=date_to,
    )


@analytics_bp.route("/map")
@login_required
@administrator_required
def map_view():
    preset = request.args.get("preset", "30days")
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    status_filter = request.args.get("status", "").strip()
    category_id = request.args.get("category_id", type=int)

    complaints = AnalyticsService.get_map_complaints(
        preset=preset,
        date_from=date_from,
        date_to=date_to,
        status=status_filter or None,
        category_id=category_id,
    )
    categories = AnalyticsService.get_categories()
    return render_template(
        "admin/map.html",
        complaints=complaints,
        categories=categories,
        preset=preset,
        date_from=date_from,
        date_to=date_to,
        status_filter=status_filter,
        category_id=category_id,
    )


@analytics_bp.route("/reports/complaint-register")
@login_required
@administrator_required
def report_complaint_register():
    return ReportsService.complaint_register()


@analytics_bp.route("/reports/pending-complaints")
@login_required
@administrator_required
def report_pending_complaints():
    return ReportsService.pending_complaints()


@analytics_bp.route("/reports/category-wise")
@login_required
@administrator_required
def report_category_wise():
    return ReportsService.category_wise_report()


@analytics_bp.route("/reports/location-wise")
@login_required
@administrator_required
def report_location_wise():
    return ReportsService.location_wise_report()


@analytics_bp.route("/reports/staff-workload")
@login_required
@administrator_required
def report_staff_workload():
    return ReportsService.staff_workload_report()


@analytics_bp.route("/reports/task-completion")
@login_required
@administrator_required
def report_task_completion():
    return ReportsService.task_completion_summary()


@analytics_bp.route("/reports/monthly-activity")
@login_required
@administrator_required
def report_monthly_activity():
    months = request.args.get("months", 6, type=int)
    return ReportsService.monthly_activity_report(months=months)
