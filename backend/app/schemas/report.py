"""Pydantic-схемы модуля отчётов и комментариев (WBS 4.4.3)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    field: str
    issue: str


class ErrorResponse(BaseModel):
    """Унифицированный формат ошибок по контракту 4.4.8."""

    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ReportResponse(BaseModel):
    """Метаданные одной версии отчёта."""

    id: int
    submission_id: int
    version_number: int
    file_name: str
    file_size_bytes: int
    file_mime_type: str
    file_sha256: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportListResponse(BaseModel):
    total: int
    items: list[ReportResponse]


class SubmissionUploadInfo(BaseModel):
    """Актуализированная карточка сдачи в ответе на загрузку."""

    id: int
    lab_work_id: int
    lab_work_title: str
    student_id: int
    student_name: str
    group_name: str | None = None
    status: str
    file_name: str
    file_size_bytes: int
    submitted_at: datetime | None = None
    updated_at: datetime | None = None


class SubmissionUploadResponse(BaseModel):
    submission: SubmissionUploadInfo
    report: ReportResponse
    message: str


class PresignedDownloadResponse(BaseModel):
    download_url: str
    file_name: str
    file_size_bytes: int
    file_sha256: str
    expires_in_seconds: int


class CommentCreateRequest(BaseModel):
    """Текст комментария. Длина проверяется в сервисе (400 по контракту)."""

    text: str = Field(..., description="Текст замечания, 5..2000 символов")


class CommentResponse(BaseModel):
    id: int
    submission_id: int
    author_id: int
    author_name: str
    author_role: Literal["student", "teacher"]
    text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)