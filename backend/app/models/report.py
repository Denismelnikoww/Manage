"""ORM-модель версии отчёта (WBS 4.4.2)."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Report(Base):
    """Метаданные загруженного файла отчёта (версия сдачи)."""

    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("submission_id", "version_number", name="uq_report_submission_version"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    submission_id = Column(
        Integer,
        ForeignKey("student_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)

    # Ключ объекта в MinIO (submissions/{lab_id}/{student_id}/{ts}_{uuid}_{name})
    file_path = Column(String(512), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    file_mime_type = Column(String(120), nullable=False)
    file_sha256 = Column(String(64), nullable=False)

    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    submission = relationship("StudentSubmission", backref="reports")