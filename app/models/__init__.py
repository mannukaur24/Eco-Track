from app.models.user import User, Role, ReportStatus, TaskStatus
from app.models.staff import Staff
from app.models.waste_category import WasteCategory
from app.models.location import Location
from app.models.report import Report
from app.models.collection_task import CollectionTask
from app.models.task_update import TaskUpdate
from app.models.awareness_article import AwarenessArticle
from app.models.report_status_history import ReportStatusHistory

__all__ = [
    "User",
    "Role",
    "ReportStatus",
    "TaskStatus",
    "Staff",
    "WasteCategory",
    "Location",
    "Report",
    "CollectionTask",
    "TaskUpdate",
    "AwarenessArticle",
    "ReportStatusHistory",
]
