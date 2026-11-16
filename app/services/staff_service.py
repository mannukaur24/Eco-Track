"""Collection Staff service layer for EcoTrack.

Business logic for staff task management: viewing assigned tasks,
updating progress, adding remarks, and marking tasks complete.
"""

from app.extensions import db
from app.models.user import ReportStatus, TaskStatus
from app.models.report import Report
from app.models.report_status_history import ReportStatusHistory
from app.models.collection_task import CollectionTask
from app.models.task_update import TaskUpdate
from app.services.complaint_service import ComplaintService
from app.utils.datetime import utc_now


class StaffService:
    """Service layer for collection staff operations."""

    # ---------- Dashboard statistics ----------

    @staticmethod
    def dashboard_stats(staff_user):
        tasks = CollectionTask.query.filter_by(staff_id=staff_user.id).all()
        now = utc_now()

        overdue = 0
        for t in tasks:
            if t.task_status not in (TaskStatus.COMPLETED,) and t.due_date and t.due_date < now:
                overdue += 1

        return {
            "total_tasks": len(tasks),
            "assigned_tasks": sum(1 for t in tasks if t.task_status == TaskStatus.ASSIGNED),
            "in_progress_tasks": sum(1 for t in tasks if t.task_status == TaskStatus.IN_PROGRESS),
            "completed_tasks": sum(1 for t in tasks if t.task_status == TaskStatus.COMPLETED),
            "overdue_tasks": overdue,
        }

    # ---------- Task management ----------

    @staticmethod
    def get_staff_tasks(staff_user, search=None, status=None):
        """Return tasks assigned to the staff member, optionally filtered."""
        query = CollectionTask.query.filter_by(staff_id=staff_user.id)
        if search:
            query = query.join(CollectionTask.report).filter(
                Report.reference.ilike(f"%{search}%")
            )
        if status:
            query = query.filter_by(task_status=status)
        return query.order_by(CollectionTask.created_at.desc()).all()

    @staticmethod
    def get_task_by_id(task_id, staff_user):
        """Return a task only if it is assigned to the given staff member."""
        return CollectionTask.query.filter_by(
            id=int(task_id), staff_id=staff_user.id
        ).first()

    @staticmethod
    def update_task_progress(task_id, staff_user, new_status, remarks):
        """Update a task's progress with transaction handling.

        Records a TaskUpdate with previous status, new status, remarks,
        timestamp, and staff user. When completed, records completion
        time and synchronises the related complaint status.
        """
        task = StaffService.get_task_by_id(task_id, staff_user)
        if task is None:
            raise ValueError("Task not found or not assigned to you.")

        previous_status = task.task_status

        # Validate status transition
        valid_transitions = {
            TaskStatus.ASSIGNED: (TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED),
            TaskStatus.IN_PROGRESS: (TaskStatus.COMPLETED,),
            TaskStatus.COMPLETED: (),
        }
        if new_status not in valid_transitions.get(previous_status, ()):
            raise ValueError(
                f"Cannot move task from '{previous_status}' to '{new_status}'."
            )

        try:
            # Record the task update
            update = TaskUpdate(
                task_id=task.id,
                updated_by=staff_user.id,
                status=new_status,
                remarks=remarks or "",
            )
            db.session.add(update)

            # Update task status
            task.task_status = new_status
            if new_status == TaskStatus.COMPLETED:
                task.completed_at = utc_now()
            task.updated_at = utc_now()

            # Synchronise complaint status in the same transaction
            report = task.report
            if new_status == TaskStatus.IN_PROGRESS:
                report.status = ReportStatus.IN_PROGRESS
            elif new_status == TaskStatus.COMPLETED:
                report.status = ReportStatus.COMPLETED
            report.updated_at = utc_now()

            # Record complaint status history
            ComplaintService.record_status_history(
                report,
                previous_status=previous_status,
                new_status=new_status,
                updated_by=staff_user.id,
                remarks=remarks or "",
            )

            db.session.commit()
            return task, update
        except Exception:
            db.session.rollback()
            raise
