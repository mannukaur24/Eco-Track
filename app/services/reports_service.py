"""Reports service layer for EcoTrack.

Provides CSV export data for administrator reports:
1. Complaint register
2. Pending complaints report
3. Category-wise waste report
4. Location-wise waste report
5. Staff assignment and workload report
6. Task completion summary
7. Monthly activity report
"""

import csv
import io
from datetime import datetime, timezone, timedelta
from flask import make_response
from app.extensions import db
from app.models.user import User, Role, ReportStatus, TaskStatus
from app.models.report import Report
from app.models.waste_category import WasteCategory
from app.models.location import Location
from app.models.collection_task import CollectionTask


class ReportsService:
    """Service layer for downloadable administrator reports."""

    # ---------- CSV helpers ----------

    @staticmethod
    def _csv_response(filename, header, rows):
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)
        output = make_response(buffer.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename={filename}"
        output.headers["Content-Type"] = "text/csv; charset=utf-8"
        return output

    @staticmethod
    def _fmt(dt):
        if dt is None:
            return ""
        if isinstance(dt, str):
            return dt
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    # ---------- Report 1: Complaint register ----------

    @classmethod
    def complaint_register(cls):
        rows = (
            db.session.query(
                Report.reference,
                User.full_name,
                User.email,
                WasteCategory.category_name,
                Location.address_text,
                Report.description,
                Report.status,
                Report.reference,
                Report.created_at,
            )
            .outerjoin(User, Report.user_id == User.id)
            .outerjoin(WasteCategory, Report.category_id == WasteCategory.id)
            .outerjoin(Location, Report.location_id == Location.id)
            .order_by(Report.created_at.desc())
            .all()
        )
        data = [
            [
                r[0],
                r[1] or "",
                r[2] or "",
                r[3] or "Uncategorized",
                r[4] or "",
                (r[5] or "")[:80],
                r[6],
                r[7],
                cls._fmt(r[8]),
            ]
            for r in rows
        ]
        return cls._csv_response(
            "complaint_register.csv",
            [
                "Reference",
                "Citizen Name",
                "Citizen Email",
                "Category",
                "Location",
                "Description",
                "Status",
                "Reference",
                "Submitted At",
            ],
            data,
        )

    # ---------- Report 2: Pending complaints report ----------

    @classmethod
    def pending_complaints(cls):
        rows = (
            db.session.query(
                Report.reference,
                User.full_name,
                WasteCategory.category_name,
                Location.address_text,
                Report.description,
                Report.created_at,
            )
            .outerjoin(User, Report.user_id == User.id)
            .outerjoin(WasteCategory, Report.category_id == WasteCategory.id)
            .outerjoin(Location, Report.location_id == Location.id)
            .filter(Report.status == ReportStatus.PENDING)
            .order_by(Report.created_at.asc())
            .all()
        )
        data = [
            [
                r[0],
                r[1] or "",
                r[2] or "Uncategorized",
                r[3] or "",
                (r[4] or "")[:80],
                cls._fmt(r[5]),
            ]
            for r in rows
        ]
        return cls._csv_response(
            "pending_complaints.csv",
            [
                "Reference",
                "Citizen Name",
                "Category",
                "Location",
                "Description",
                "Submitted At",
            ],
            data,
        )

    # ---------- Report 3: Category-wise waste report ----------

    @classmethod
    def category_wise_report(cls):
        rows = (
            db.session.query(
                WasteCategory.category_name,
                db.func.count(Report.id),
            )
            .outerjoin(Report, Report.category_id == WasteCategory.id)
            .group_by(WasteCategory.id, WasteCategory.category_name)
            .order_by(db.func.count(Report.id).desc())
            .all()
        )
        data = [[r[0] or "Uncategorized", r[1]] for r in rows]
        return cls._csv_response(
            "category_wise_waste_report.csv",
            ["Category", "Complaint Count"],
            data,
        )

    # ---------- Report 4: Location-wise waste report ----------

    @classmethod
    def location_wise_report(cls):
        rows = (
            db.session.query(
                Location.address_text,
                Location.latitude,
                Location.longitude,
                db.func.count(Report.id),
            )
            .join(Report, Report.location_id == Location.id)
            .group_by(Location.id, Location.address_text, Location.latitude, Location.longitude)
            .order_by(db.func.count(Report.id).desc())
            .all()
        )
        data = [
            [r[0] or "Unknown", r[1] or "", r[2] or "", r[3]] for r in rows
        ]
        return cls._csv_response(
            "location_wise_waste_report.csv",
            ["Location", "Latitude", "Longitude", "Complaint Count"],
            data,
        )

    # ---------- Report 5: Staff assignment and workload report ----------

    @classmethod
    def staff_workload_report(cls):
        rows = (
            db.session.query(
                User.full_name,
                User.email,
                db.func.count(CollectionTask.id).label("total"),
                db.func.sum(
                    db.case(
                        (
                            CollectionTask.task_status == TaskStatus.COMPLETED,
                            1,
                        ),
                        else_=0,
                    )
                ).label("completed"),
                db.func.sum(
                    db.case(
                        (
                            CollectionTask.task_status.in_(
                                [TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ).label("active"),
            )
            .outerjoin(CollectionTask, CollectionTask.staff_id == User.id)
            .filter(User.role == Role.STAFF)
            .group_by(User.id, User.full_name, User.email)
            .order_by(User.full_name)
            .all()
        )
        data = [
            [r[0], r[1] or "", int(r[2] or 0), int(r[3] or 0), int(r[4] or 0)]
            for r in rows
        ]
        return cls._csv_response(
            "staff_workload_report.csv",
            ["Staff Name", "Email", "Total Tasks", "Completed", "Active"],
            data,
        )

    # ---------- Report 6: Task completion summary ----------

    @classmethod
    def task_completion_summary(cls):
        rows = (
            db.session.query(
                CollectionTask.task_status,
                db.func.count(CollectionTask.id),
            )
            .group_by(CollectionTask.task_status)
            .all()
        )
        status_map = {
            TaskStatus.ASSIGNED: "Assigned",
            TaskStatus.IN_PROGRESS: "In Progress",
            TaskStatus.COMPLETED: "Completed",
            TaskStatus.OVERDUE: "Overdue",
        }
        data = [[status_map.get(r[0], r[0]), r[1]] for r in rows]
        return cls._csv_response(
            "task_completion_summary.csv",
            ["Task Status", "Task Count"],
            data,
        )

    # ---------- Report 7: Monthly activity report ----------

    @classmethod
    def monthly_activity_report(cls, months=6):
        now = datetime.now(timezone.utc)
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
            submitted = (
                db.session.query(db.func.count(Report.id))
                .filter(Report.created_at >= month_start)
                .filter(Report.created_at <= month_end)
                .scalar()
            )
            resolved = (
                db.session.query(db.func.count(Report.id))
                .filter(Report.status == ReportStatus.COMPLETED)
                .filter(Report.updated_at >= month_start)
                .filter(Report.updated_at <= month_end)
                .scalar()
            )
            data.append(
                [
                    month_start.strftime("%B %Y"),
                    int(submitted or 0),
                    int(resolved or 0),
                ]
            )
        return cls._csv_response(
            "monthly_activity_report.csv",
            ["Month", "Complaints Submitted", "Complaints Resolved"],
            data,
        )
