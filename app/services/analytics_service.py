"""Analytics service layer for EcoTrack.

Provides aggregated database queries for administrator dashboards:
complaints by category/status, monthly submissions/resolutions, staff
performance, pending vs completed tasks, and location-wise summaries.
Supports date filtering (last 7 days, 30 days, 3 months, custom range).
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models.user import User, Role, ReportStatus, TaskStatus
from app.models.report import Report
from app.models.waste_category import WasteCategory
from app.models.collection_task import CollectionTask
from app.models.location import Location


class AnalyticsService:
    """Service layer for administrator analytics and reporting."""

    # ---------- Date range helpers ----------

    @staticmethod
    def _parse_date(date_str):
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

    @classmethod
    def date_range(cls, preset, date_from=None, date_to=None):
        """Return (start, end) datetimes for a given preset or custom range."""
        now = datetime.now(timezone.utc)
        if preset == "7days":
            start = now - timedelta(days=7)
            end = now
        elif preset == "30days":
            start = now - timedelta(days=30)
            end = now
        elif preset == "3months":
            start = now - timedelta(days=90)
            end = now
        elif preset == "custom":
            start = cls._parse_date(date_from) or (now - timedelta(days=30))
            end = cls._parse_date(date_to) or now
            if end:
                end = end.replace(hour=23, minute=59, second=59)
        else:
            start = now - timedelta(days=30)
            end = now
        return start, end

    @staticmethod
    def _filter_by_date(query, date_column, start, end):
        if start:
            query = query.filter(date_column >= start)
        if end:
            query = query.filter(date_column <= end)
        return query

    # ---------- Chart 1: Complaints by category ----------

    @classmethod
    def complaints_by_category(cls, preset="30days", date_from=None, date_to=None):
        start, end = cls.date_range(preset, date_from, date_to)
        query = (
            db.session.query(
                WasteCategory.category_name, func.count(Report.id)
            )
            .outerjoin(Report, Report.category_id == WasteCategory.id)
        )
        query = cls._filter_by_date(query, Report.created_at, start, end)
        query = query.group_by(WasteCategory.category_name).order_by(
            func.count(Report.id).desc()
        )
        rows = query.all()
        return {
            "labels": [r[0] or "Uncategorized" for r in rows],
            "data": [r[1] for r in rows],
        }

    # ---------- Chart 2: Complaints by status ----------

    @classmethod
    def complaints_by_status(cls, preset="30days", date_from=None, date_to=None):
        start, end = cls.date_range(preset, date_from, date_to)
        query = (
            db.session.query(Report.status, func.count(Report.id))
            .group_by(Report.status)
        )
        query = cls._filter_by_date(query, Report.created_at, start, end)
        rows = query.all()
        status_map = {
            ReportStatus.PENDING: "Pending",
            ReportStatus.VERIFIED: "Verified",
            ReportStatus.REJECTED: "Rejected",
            ReportStatus.ASSIGNED: "Assigned",
            ReportStatus.IN_PROGRESS: "In Progress",
            ReportStatus.COMPLETED: "Completed",
        }
        labels = []
        data = []
        for status, count in rows:
            labels.append(status_map.get(status, status))
            data.append(count)
        return {"labels": labels, "data": data}

    # ---------- Chart 3: Monthly complaint submissions ----------

    @classmethod
    def monthly_submissions(cls, months=6):
        now = datetime.now(timezone.utc)
        labels = []
        data = []
        for i in range(months - 1, -1, -1):
            month_start = (now.replace(day=1) - timedelta(days=30 * i)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            if i == 0:
                month_end = now
            else:
                next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(
                    day=1
                )
                month_end = next_month - timedelta(seconds=1)
            count = (
                db.session.query(func.count(Report.id))
                .filter(Report.created_at >= month_start)
                .filter(Report.created_at <= month_end)
                .scalar()
            )
            labels.append(month_start.strftime("%b %Y"))
            data.append(count)
        return {"labels": labels, "data": data}

    # ---------- Chart 4: Monthly resolved complaints ----------

    @classmethod
    def monthly_resolved(cls, months=6):
        now = datetime.now(timezone.utc)
        labels = []
        data = []
        for i in range(months - 1, -1, -1):
            month_start = (now.replace(day=1) - timedelta(days=30 * i)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            if i == 0:
                month_end = now
            else:
                next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(
                    day=1
                )
                month_end = next_month - timedelta(seconds=1)
            count = (
                db.session.query(func.count(Report.id))
                .filter(Report.status == ReportStatus.COMPLETED)
                .filter(Report.updated_at >= month_start)
                .filter(Report.updated_at <= month_end)
                .scalar()
            )
            labels.append(month_start.strftime("%b %Y"))
            data.append(count)
        return {"labels": labels, "data": data}

    # ---------- Chart 5: Staff task completion performance ----------

    @classmethod
    def staff_performance(cls):
        rows = (
            db.session.query(
                User.full_name,
                func.count(CollectionTask.id).label("total"),
                func.sum(
                    db.case(
                        (
                            CollectionTask.task_status == TaskStatus.COMPLETED,
                            1,
                        ),
                        else_=0,
                    )
                ).label("completed"),
            )
            .join(CollectionTask, CollectionTask.staff_id == User.id)
            .filter(User.role == Role.STAFF)
            .group_by(User.id, User.full_name)
            .order_by(func.count(CollectionTask.id).desc())
            .all()
        )
        labels = [r[0] for r in rows]
        total = [r[1] for r in rows]
        completed = [int(r[2] or 0) for r in rows]
        return {
            "labels": labels,
            "total": total,
            "completed": completed,
        }

    # ---------- Chart 6: Pending vs completed tasks ----------

    @classmethod
    def pending_vs_completed_tasks(cls):
        pending = (
            db.session.query(func.count(CollectionTask.id))
            .filter(CollectionTask.task_status == TaskStatus.ASSIGNED)
            .scalar()
        )
        in_progress = (
            db.session.query(func.count(CollectionTask.id))
            .filter(CollectionTask.task_status == TaskStatus.IN_PROGRESS)
            .scalar()
        )
        completed = (
            db.session.query(func.count(CollectionTask.id))
            .filter(CollectionTask.task_status == TaskStatus.COMPLETED)
            .scalar()
        )
        return {
            "labels": ["Assigned", "In Progress", "Completed"],
            "data": [pending, in_progress, completed],
        }

    # ---------- Chart 7: Location-wise complaint summaries ----------

    @classmethod
    def complaints_by_location(cls, limit=10):
        rows = (
            db.session.query(
                Location.address_text,
                func.count(Report.id),
            )
            .join(Report, Report.location_id == Location.id)
            .group_by(Location.id, Location.address_text)
            .order_by(func.count(Report.id).desc())
            .limit(limit)
            .all()
        )
        return {
            "labels": [r[0] or "Unknown" for r in rows],
            "data": [r[1] for r in rows],
        }

    # ---------- Dashboard summary statistics ----------

    @classmethod
    def dashboard_summary(cls, preset="30days", date_from=None, date_to=None):
        start, end = cls.date_range(preset, date_from, date_to)
        total = cls._filter_by_date(
            db.session.query(Report), Report.created_at, start, end
        ).count()
        pending = cls._filter_by_date(
            db.session.query(Report).filter_by(status=ReportStatus.PENDING),
            Report.created_at,
            start,
            end,
        ).count()
        verified = cls._filter_by_date(
            db.session.query(Report).filter_by(status=ReportStatus.VERIFIED),
            Report.created_at,
            start,
            end,
        ).count()
        rejected = cls._filter_by_date(
            db.session.query(Report).filter_by(status=ReportStatus.REJECTED),
            Report.created_at,
            start,
            end,
        ).count()
        completed = cls._filter_by_date(
            db.session.query(Report).filter_by(status=ReportStatus.COMPLETED),
            Report.created_at,
            start,
            end,
        ).count()
        return {
            "total": total,
            "pending": pending,
            "verified": verified,
            "rejected": rejected,
            "completed": completed,
        }

    # ---------- Map data ----------

    @classmethod
    def get_map_complaints(
        cls, preset="30days", date_from=None, date_to=None, status=None, category_id=None
    ):
        start, end = cls.date_range(preset, date_from, date_to)
        query = (
            db.session.query(
                Report.reference,
                Report.status,
                WasteCategory.category_name,
                Location.address_text,
                Location.latitude,
                Location.longitude,
            )
            .outerjoin(WasteCategory, Report.category_id == WasteCategory.id)
            .outerjoin(Location, Report.location_id == Location.id)
            .filter(Location.latitude.isnot(None))
            .filter(Location.longitude.isnot(None))
        )
        query = cls._filter_by_date(query, Report.created_at, start, end)
        if status:
            query = query.filter(Report.status == status)
        if category_id:
            query = query.filter(Report.category_id == category_id)
        rows = query.order_by(Report.created_at.desc()).all()
        return [
            {
                "reference": r[0],
                "status": r[1],
                "category": r[2] or "Uncategorized",
                "address": r[3] or "",
                "latitude": r[4],
                "longitude": r[5],
            }
            for r in rows
        ]

    @classmethod
    def get_categories(cls):
        return WasteCategory.query.order_by(WasteCategory.category_name).all()
