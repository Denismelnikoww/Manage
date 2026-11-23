"""Pydantic-схемы смены статуса сдачи (WBS 4.3.2)."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SubmissionStatus = Literal[
    "not_started",
    "in_progress",
    "submitted",
    "needs_work",
    "accepted",
]


class SubmissionStatusUpdateRequest(BaseModel):
    """Тело PATCH /submissions/{id}/status."""

    status: SubmissionStatus = Field(..., description="Целевой статус перехода")
    comment_text: Optional[str] = Field(
        None,
        description="Обязателен при needs_work (≥ 5 символов); опционален при accepted",
    )


class SubmissionStatusResponse(BaseModel):
    """Карточка сдачи после смены статуса."""

    id: int
    lab_work_id: int
    lab_work_title: str
    student_id: int
    student_name: str
    group_name: str | None = None
    status: SubmissionStatus
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    updated_at: datetime | None = None


class StatusHistoryItem(BaseModel):
    id: int
    submission_id: int
    from_status: SubmissionStatus
    to_status: SubmissionStatus
    changed_by_id: int
    changed_by_name: str
    comment_text: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StatusHistoryListResponse(BaseModel):
    total: int
    items: list[StatusHistoryItem]
