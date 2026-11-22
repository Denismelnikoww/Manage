"""Эндпоинты сдач: статусы (4.3.2), отчёты и комментарии (4.4.3)."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.schemas.report import (
    CommentCreateRequest,
    CommentResponse,
    PresignedDownloadResponse,
    ReportListResponse,
    ReportResponse,
    SubmissionUploadResponse,
)
from app.schemas.status import (
    StatusHistoryListResponse,
    StatusHistoryItem,
    SubmissionStatusResponse,
    SubmissionStatusUpdateRequest,
)
from app.services import reports as service
from app.services import statuses as status_service

router = APIRouter()


@router.patch(
    "/{submission_id}/status",
    response_model=SubmissionStatusResponse,
    summary="Смена статуса сдачи (WBS 4.3.2 / FR-03)",
)
def update_submission_status(
    submission_id: int,
    payload: SubmissionStatusUpdateRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> SubmissionStatusResponse:
    """FSM-переходы с проверкой прав по матрице 4.3.1."""
    submission = status_service.get_submission_or_404(db, submission_id)
    updated = status_service.change_submission_status(
        db,
        current_user,
        submission,
        target_status=payload.status,
        comment_text=payload.comment_text,
    )
    return SubmissionStatusResponse(**status_service.submission_to_status_response(updated))


@router.get(
    "/{submission_id}/status-history",
    response_model=StatusHistoryListResponse,
    summary="История смены статусов сдачи (FR-10 Could)",
)
def get_status_history(
    submission_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> StatusHistoryListResponse:
    submission = status_service.get_submission_or_404(db, submission_id)
    items = status_service.list_status_history(db, current_user, submission)
    return StatusHistoryListResponse(
        total=len(items),
        items=[StatusHistoryItem(**status_service.history_to_response(item)) for item in items],
    )


@router.post(
    "/{submission_id}/upload",
    response_model=SubmissionUploadResponse,
    summary="Загрузка файла отчёта студентом",
)
def upload_report(
    submission_id: int,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> SubmissionUploadResponse:
    """Принимает PDF/DOCX/ZIP до 20 МБ, сохраняет в MinIO и переводит сдачу в submitted."""
    submission = service.get_submission_or_404(db, submission_id)

    content = service.read_upload_limited(file.file)
    report = service.upload_report(
        db,
        current_user,
        submission,
        file.filename or "report",
        content,
    )

    return SubmissionUploadResponse(
        submission=service.submission_to_upload_info(submission, report),
        report=ReportResponse.model_validate(report),
        message="Отчёт успешно загружен и передан на проверку",
    )


@router.get(
    "/{submission_id}/download-url",
    response_model=PresignedDownloadResponse,
    summary="Временная pre-signed ссылка на скачивание отчёта",
)
def get_download_url(
    submission_id: int,
    current_user: CurrentUser,
    version_id: Optional[int] = Query(
        None,
        description="ID конкретной версии отчёта; без него — последняя версия",
    ),
    db: Session = Depends(get_db),
) -> PresignedDownloadResponse:
    submission = service.get_submission_or_404(db, submission_id)
    report, url = service.build_download_url(db, current_user, submission, version_id)
    return PresignedDownloadResponse(
        download_url=url,
        file_name=report.file_name,
        file_size_bytes=report.file_size_bytes,
        file_sha256=report.file_sha256,
        expires_in_seconds=900,
    )


@router.get(
    "/{submission_id}/reports",
    response_model=ReportListResponse,
    summary="История версий отчётов по сдаче",
)
def get_reports(
    submission_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> ReportListResponse:
    submission = service.get_submission_or_404(db, submission_id)
    items = service.list_reports(db, current_user, submission)
    return ReportListResponse(
        total=len(items),
        items=[ReportResponse.model_validate(item) for item in items],
    )


@router.get(
    "/{submission_id}/comments",
    response_model=list[CommentResponse],
    summary="Комментарии преподавателя к сдаче",
)
def get_comments(
    submission_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> list[CommentResponse]:
    submission = service.get_submission_or_404(db, submission_id)
    comments = service.list_comments(db, current_user, submission)
    return [CommentResponse(**service.comment_to_response(item)) for item in comments]


@router.post(
    "/{submission_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавление комментария преподавателем",
)
def add_comment(
    submission_id: int,
    payload: CommentCreateRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> CommentResponse:
    submission = service.get_submission_or_404(db, submission_id)
    comment = service.add_comment(db, current_user, submission, payload.text)
    return CommentResponse(**service.comment_to_response(comment))