"""Administrator service layer for EcoTrack.

Business logic for complaint management, task assignment,
staff management, category management, and awareness content.
"""

from datetime import datetime, time, timedelta

from sqlalchemy import func

from app.extensions import db
from app.models.user import User, Role, ReportStatus, TaskStatus
from app.models.report import Report
from app.models.report_status_history import ReportStatusHistory
from app.models.waste_category import WasteCategory
from app.models.collection_task import CollectionTask
from app.models.awareness_article import AwarenessArticle
from app.models.staff import Staff
from app.services.complaint_service import ComplaintService
from app.utils.datetime import utc_now


class AdminService:
    """Service layer for administrator operations."""

    # ---------- Dashboard statistics ----------

    @staticmethod
    def dashboard_stats():
        """Return complaint/task statistics using SQL aggregate queries."""
        total_complaints = db.session.query(func.count(Report.id)).scalar() or 0
        pending_complaints = (
            db.session.query(func.count(Report.id))
            .filter_by(status=ReportStatus.PENDING)
            .scalar()
            or 0
        )
        verified_complaints = (
            db.session.query(func.count(Report.id))
            .filter_by(status=ReportStatus.VERIFIED)
            .scalar()
            or 0
        )
        rejected_complaints = (
            db.session.query(func.count(Report.id))
            .filter_by(status=ReportStatus.REJECTED)
            .scalar()
            or 0
        )
        assigned_tasks = (
            db.session.query(func.count(CollectionTask.id))
            .filter_by(task_status=TaskStatus.ASSIGNED)
            .scalar()
            or 0
        )
        in_progress_tasks = (
            db.session.query(func.count(CollectionTask.id))
            .filter_by(task_status=TaskStatus.IN_PROGRESS)
            .scalar()
            or 0
        )
        completed_tasks = (
            db.session.query(func.count(CollectionTask.id))
            .filter_by(task_status=TaskStatus.COMPLETED)
            .scalar()
            or 0
        )
        overdue_tasks = (
            db.session.query(func.count(CollectionTask.id))
            .filter(CollectionTask.task_status != TaskStatus.COMPLETED)
            .filter(CollectionTask.due_date.isnot(None))
            .filter(CollectionTask.due_date < utc_now())
            .scalar()
            or 0
        )

        return {
            "total_complaints": total_complaints,
            "pending_complaints": pending_complaints,
            "verified_complaints": verified_complaints,
            "rejected_complaints": rejected_complaints,
            "assigned_tasks": assigned_tasks,
            "in_progress_tasks": in_progress_tasks,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
        }

    # ---------- Complaint management ----------

    @staticmethod
    def get_complaints(search=None, category_id=None, status=None, date_from=None, date_to=None):
        query = Report.query
        if search:
            query = query.filter(Report.reference.ilike(f"%{search}%"))
        if category_id:
            query = query.filter_by(category_id=category_id)
        if status:
            query = query.filter_by(status=status)
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                from_date = None
            if from_date is not None:
                query = query.filter(
                    Report.created_at >= datetime.combine(from_date, time.min)
                )
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                to_date = None
            if to_date is not None:
                # Include the entire selected end date (up to 23:59:59.999999).
                query = query.filter(
                    Report.created_at < datetime.combine(to_date + timedelta(days=1), time.min)
                )
        return query.order_by(Report.created_at.desc()).all()

    @staticmethod
    def get_complaint_by_reference(reference):
        return Report.query.filter_by(reference=reference).first()

    @staticmethod
    def verify_complaint(reference, admin_user):
        report = AdminService.get_complaint_by_reference(reference)
        if report is None:
            raise ValueError("Complaint not found.")
        if report.status != ReportStatus.PENDING:
            raise ValueError("Only pending complaints can be verified.")
        previous_status = report.status
        report.status = ReportStatus.VERIFIED
        report.updated_at = utc_now()
        ComplaintService.record_status_history(
            report,
            previous_status=previous_status,
            new_status=ReportStatus.VERIFIED,
            updated_by=admin_user.id,
            remarks="Complaint verified by administrator.",
        )
        db.session.commit()
        return report

    @staticmethod
    def reject_complaint(reference, reason, admin_user):
        report = AdminService.get_complaint_by_reference(reference)
        if report is None:
            raise ValueError("Complaint not found.")
        if report.status not in (ReportStatus.PENDING, ReportStatus.VERIFIED):
            raise ValueError("This complaint cannot be rejected.")
        if not reason or not reason.strip():
            raise ValueError("A rejection reason is required.")
        previous_status = report.status
        report.status = ReportStatus.REJECTED
        report.rejection_reason = reason.strip()
        report.updated_at = utc_now()
        ComplaintService.record_status_history(
            report,
            previous_status=previous_status,
            new_status=ReportStatus.REJECTED,
            updated_by=admin_user.id,
            remarks=f"Complaint rejected: {reason.strip()}",
        )
        db.session.commit()
        return report

    # ---------- Task assignment ----------

    @staticmethod
    def get_assignable_complaints():
        return Report.query.filter_by(status=ReportStatus.VERIFIED).order_by(
            Report.created_at.desc()
        ).all()

    @staticmethod
    def get_active_staff():
        return (
            User.query.join(User.staff_profile)
            .filter(User.role == Role.STAFF, User.is_active == True)  # noqa: E712
            .order_by(User.full_name)
            .all()
        )

    @staticmethod
    def assign_task(reference, staff_id, due_date, instructions, admin_user):
        report = AdminService.get_complaint_by_reference(reference)
        if report is None:
            raise ValueError("Complaint not found.")
        if report.status != ReportStatus.VERIFIED:
            raise ValueError("Only verified complaints can be assigned.")

        staff_user = db.session.get(User, int(staff_id))
        if staff_user is None or staff_user.role != Role.STAFF or not staff_user.is_active:
            raise ValueError("Invalid or inactive staff member.")

        due_dt = None
        if due_date:
            due_dt = datetime.fromisoformat(due_date)

        task = CollectionTask(
            report_id=report.id,
            staff_id=staff_user.id,
            assigned_by=admin_user.id,
            due_date=due_dt,
            task_status=TaskStatus.ASSIGNED,
            instructions=instructions or "",
        )
        db.session.add(task)

        previous_status = report.status
        report.status = ReportStatus.ASSIGNED
        report.updated_at = utc_now()
        ComplaintService.record_status_history(
            report,
            previous_status=previous_status,
            new_status=ReportStatus.ASSIGNED,
            updated_by=admin_user.id,
            remarks="Task assigned to collection staff.",
        )

        db.session.commit()
        return task

    # ---------- Staff management ----------

    @staticmethod
    def get_staff_members():
        return (
            User.query.join(User.staff_profile)
            .filter(User.role == Role.STAFF)
            .order_by(User.full_name)
            .all()
        )

    @staticmethod
    def create_staff(full_name, email, phone, availability, service_area, password):
        if User.query.filter_by(email=email.lower()).first():
            raise ValueError("An account with this email already exists.")
        user = User(
            full_name=full_name.strip(),
            email=email.strip().lower(),
            role=Role.STAFF,
            phone=phone or None,
            is_active=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        staff = Staff(
            user_id=user.id,
            availability=availability or None,
            service_area=service_area or None,
        )
        db.session.add(staff)
        db.session.commit()
        return user

    @staticmethod
    def toggle_staff_active(user_id):
        user = db.session.get(User, int(user_id))
        if user is None or user.role != Role.STAFF:
            raise ValueError("Staff member not found.")
        user.is_active = not user.is_active
        db.session.commit()
        return user

    @staticmethod
    def update_staff(user_id, full_name, phone, availability, service_area):
        user = db.session.get(User, int(user_id))
        if user is None or user.role != Role.STAFF:
            raise ValueError("Staff member not found.")
        user.full_name = full_name.strip()
        user.phone = phone or None
        staff = user.staff_profile
        if staff:
            staff.availability = availability or None
            staff.service_area = service_area or None
        db.session.commit()
        return user

    @staticmethod
    def get_staff_workload(user_id):
        tasks = CollectionTask.query.filter_by(staff_id=int(user_id)).all()
        return {
            "total": len(tasks),
            "pending": sum(1 for t in tasks if t.task_status == TaskStatus.PENDING),
            "in_progress": sum(1 for t in tasks if t.task_status == TaskStatus.IN_PROGRESS),
            "completed": sum(1 for t in tasks if t.task_status == TaskStatus.COMPLETED),
        }

    # ---------- Category management ----------

    @staticmethod
    def get_categories():
        return WasteCategory.query.order_by(WasteCategory.category_name).all()

    @staticmethod
    def create_category(name, description):
        if WasteCategory.query.filter_by(category_name=name.strip()).first():
            raise ValueError("A category with this name already exists.")
        category = WasteCategory(category_name=name.strip(), description=description or None)
        db.session.add(category)
        db.session.commit()
        return category

    @staticmethod
    def update_category(category_id, name, description):
        category = db.session.get(WasteCategory, int(category_id))
        if category is None:
            raise ValueError("Category not found.")
        category.category_name = name.strip()
        category.description = description or None
        db.session.commit()
        return category

    @staticmethod
    def delete_category(category_id):
        category = db.session.get(WasteCategory, int(category_id))
        if category is None:
            raise ValueError("Category not found.")
        if category.reports:
            raise ValueError("Cannot delete a category that is in use by complaints.")
        db.session.delete(category)
        db.session.commit()

    # ---------- Awareness content management ----------

    @staticmethod
    def get_articles():
        return AwarenessArticle.query.order_by(AwarenessArticle.created_at.desc()).all()

    @staticmethod
    def create_article(title, content, topic, is_published):
        article = AwarenessArticle(
            title=title.strip(),
            content=content.strip(),
            topic=topic or None,
            is_published=bool(is_published),
            published_at=utc_now() if is_published else None,
        )
        db.session.add(article)
        db.session.commit()
        return article

    @staticmethod
    def update_article(article_id, title, content, topic, is_published):
        article = db.session.get(AwarenessArticle, int(article_id))
        if article is None:
            raise ValueError("Article not found.")
        article.title = title.strip()
        article.content = content.strip()
        article.topic = topic or None
        article.is_published = bool(is_published)
        if is_published and not article.published_at:
            article.published_at = utc_now()
        elif not is_published:
            article.published_at = None
        db.session.commit()
        return article

    @staticmethod
    def toggle_publish(article_id):
        article = db.session.get(AwarenessArticle, int(article_id))
        if article is None:
            raise ValueError("Article not found.")
        article.is_published = not article.is_published
        if article.is_published and not article.published_at:
            article.published_at = utc_now()
        elif not article.is_published:
            article.published_at = None
        db.session.commit()
        return article

    @staticmethod
    def delete_article(article_id):
        article = db.session.get(AwarenessArticle, int(article_id))
        if article is None:
            raise ValueError("Article not found.")
        db.session.delete(article)
        db.session.commit()
