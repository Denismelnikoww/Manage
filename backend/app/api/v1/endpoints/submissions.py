"""Эндпоинты отчётов и комментариев (WBS 4.4.3)."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.core.errors import ApiError
from app.schemas.report import (
    CommentCreateRequest,
    CommentResponse,
    PresignedDownloadResponse,
    ReportListResponse,
    ReportResponse,
    SubmissionUploadResponse,
)
from app.services import reports as service

router = APIRouter()


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