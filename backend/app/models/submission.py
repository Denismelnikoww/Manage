"""ORM-модель сдачи лабораторной работы (нужна для фильтра по статусу, WBS 4.2.3)."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base

# 5 статусов из OpenAPI / матрицы переходов (WBS 4.3.1)
SUBMISSION_STATUSES = (
    "not_started",
    "in_progress",
    "submitted",
    "needs_work",
    "accepted",
)


class StudentSubmission(Base):
    """Прогресс студента по конкретной лабораторной работе."""

    __tablename__ = "student_submissions"
    __table_args__ = (
        UniqueConstraint("lab_work_id", "student_id", name="uq_submission_lab_student"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lab_work_id = Column(Integer, ForeignKey("lab_works.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="not_started", index=True)

    submitted_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    lab_work = relationship("LabWork", back_populates="submissions")
    student = relationship("User")
