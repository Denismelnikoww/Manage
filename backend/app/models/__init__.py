from app.models.comment import Comment
from app.models.lab_work import LabWork
from app.models.report import Report
from app.models.submission import SUBMISSION_STATUSES, StudentSubmission
from app.models.user import Role, User
from app.core.database import Base

__all__ = [
    "Base",
    "Comment",
    "LabWork",
    "Report",
    "Role",
    "StudentSubmission",
    "SUBMISSION_STATUSES",
    "User",
]