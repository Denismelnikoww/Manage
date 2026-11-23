"""ORM-модель истории смены статусов сдачи (WBS 4.3.2 / FR-10 Could)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class SubmissionStatusHistory(Base):
    """Запись о каждом переходе статуса сдачи (кто, когда, откуда → куда)."""

    __tablename__ = "submission_status_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    submission_id = Column(
        Integer,
        ForeignKey("student_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status = Column(String(32), nullable=False)
    to_status = Column(String(32), nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    comment_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    submission = relationship("StudentSubmission", backref="status_history")
    changed_by = relationship("User")
