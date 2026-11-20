"""Бизнес-логика модуля отчётов и комментариев (WBS 4.4.3)."""

import io
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ApiError
from app.core.files import FileValidationError, stream_sha256, validate_report_file
from app.core.storage import build_object_key, get_storage
from app.models.comment import Comment
from app.models.report import Report
from app.models.submission import StudentSubmission
from app.models.user import User

UPLOAD_ALLOWED_STATUSES = ("not_started", "in_progress", "needs_work")
COMMENT_MIN_LENGTH = 5
COMMENT_MAX_LENGTH = 2000


def get_submission_or_404(db: Session, submission_id: int) -> StudentSubmission:
    submission = db.query(StudentSubmission).filter(StudentSubmission.id == submission_id).first()
    if submission is None:
        raise ApiError(404, "NOT_FOUND", "Сдача с указанным идентификатором не найдена")
    return submission


def ensure_can_upload(user: User, submission: StudentSubmission) -> None:
    role = user.role.code if user.role else None
    if role != "student":
        raise ApiError(403, "FORBIDDEN", "Загрузка отчёта доступна только студенту")
    if submission.student_id != user.id:
        raise ApiError(403, "FORBIDDEN", "Вы не можете загружать отчёт для данной сдачи")


def ensure_can_view(user: User, submission: StudentSubmission) -> None:
    role = user.role.code if user.role else None
    if role == "teacher":
        return
    if role == "student" and submission.student_id == user.id:
        return
    raise ApiError(403, "FORBIDDEN", "Доступ запрещён: вы можете просматривать только свои сдачи")


def ensure_teacher(user: User) -> None:
    role = user.role.code if user.role else None
    if role != "teacher":
        raise ApiError(403, "FORBIDDEN", "Действие доступно только преподавателю")


def read_upload_limited(upload_file) -> bytes:
    """Читает файл чанками, не превышая лимит (защита от исчерпания памяти)."""
    max_size = settings.REPORT_MAX_SIZE_BYTES
    buffer = bytearray()
    while True:
        chunk = upload_file.read(64 * 1024)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > max_size:
            raise ApiError(
                400,
                "FILE_TOO_LARGE",
                "Размер файла не должен превышать 20 МБ",
                details=[{"field": "file", "issue": "Получено больше байт, чем лимит %s" % max_size}],
            )
    return bytes(buffer)


def upload_report(
    db: Session,
    user: User,
    submission: StudentSubmission,
    file_name: str,
    content: bytes,
) -> Report:
    """Валидирует файл, сохраняет его в MinIO и создаёт версию отчёта в БД."""
    ensure_can_upload(user, submission)

    if submission.status not in UPLOAD_ALLOWED_STATUSES:
        raise ApiError(
            409,
            "INVALID_SUBMISSION_STATE",
            "Повторная загрузка недоступна: работа уже сдана или принята",
            details=[{
                "field": "status",
                "issue": "Текущий статус '%s'. Повторная загрузка возможна только "
                         "в статусе 'needs_work'" % submission.status,
            }],
        )

    try:
        mime_type = validate_report_file(file_name, content)
    except FileValidationError as error:
        raise ApiError(
            400,
            error.code,
            error.message,
            details=[{"field": "file", "issue": error.issue}] if error.issue else None,
        )

    sha256 = stream_sha256(content)
    key = build_object_key(submission.lab_work_id, submission.student_id, file_name)
    storage = get_storage()

    try:
        storage.put_object(key, io.BytesIO(content), len(content), mime_type)
    except Exception:  # noqa: BLE001 - любой сбой хранилища -> 500
        raise ApiError(
            500,
            "STORAGE_ERROR",
            "Сбой сохранения файла в объектном хранилище MinIO. "
            "Попробуйте повторить попытку позже",
        )

    next_version = (
        db.query(func.max(Report.version_number))
        .filter(Report.submission_id == submission.id)
        .scalar()
        or 0
    ) + 1

    report = Report(
        submission_id=submission.id,
        version_number=next_version,
        file_path=key,
        file_name=file_name,
        file_size_bytes=len(content),
        file_mime_type=mime_type,
        file_sha256=sha256,
    )
    submission.status = "submitted"
    submission.submitted_at = datetime.now(timezone.utc)

    try:
        db.add(report)
        db.commit()
        db.refresh(report)
    except Exception:  # noqa: BLE001 - ошибка БД -> откат + компенсация
        db.rollback()
        storage.remove_object(key)
        raise ApiError(
            500,
            "DB_ERROR",
            "Не удалось сохранить данные отчёта. Попробуйте повторить попытку позже",
        )

    return report


def get_report_for_download(
    db: Session,
    user: User,
    submission: StudentSubmission,
    version_id: int | None = None,
) -> Report:
    ensure_can_view(user, submission)

    query = db.query(Report).filter(Report.submission_id == submission.id)
    if version_id is not None:
        query = query.filter(Report.id == version_id)

    report = query.order_by(Report.version_number.desc()).first()
    if report is None:
        raise ApiError(
            400 if version_id is None else 404,
            "FILE_NOT_UPLOADED" if version_id is None else "NOT_FOUND",
            "Для данной сдачи файл отчёта ещё не был загружен"
            if version_id is None
            else "Версия отчёта не найдена",
        )
    return report


def build_download_url(
    db: Session,
    user: User,
    submission: StudentSubmission,
    version_id: int | None = None,
) -> tuple[Report, str]:
    report = get_report_for_download(db, user, submission, version_id)
    url = get_storage().presigned_get_url(
        report.file_path,
        report.file_name,
        report.file_mime_type,
        expires_seconds=settings.PRESIGNED_URL_TTL_SECONDS,
    )
    return report, url


def list_reports(db: Session, user: User, submission: StudentSubmission) -> list[Report]:
    ensure_can_view(user, submission)
    return (
        db.query(Report)
        .filter(Report.submission_id == submission.id)
        .order_by(Report.version_number.desc())
        .all()
    )


def list_comments(db: Session, user: User, submission: StudentSubmission) -> list[Comment]:
    ensure_can_view(user, submission)
    return (
        db.query(Comment)
        .filter(Comment.submission_id == submission.id)
        .order_by(Comment.created_at.asc())
        .all()
    )


def add_comment(db: Session, user: User, submission: StudentSubmission, text: str) -> Comment:
    ensure_teacher(user)
    cleaned = (text or "").strip()
    if len(cleaned) < COMMENT_MIN_LENGTH:
        raise ApiError(
            400,
            "INVALID_COMMENT",
            "Комментарий должен содержать минимум %s символов" % COMMENT_MIN_LENGTH,
            details=[{"field": "text", "issue": "После strip() осталось %s символов" % len(cleaned)}],
        )
    if len(cleaned) > COMMENT_MAX_LENGTH:
        raise ApiError(
            400,
            "INVALID_COMMENT",
            "Комментарий не может быть длиннее %s символов" % COMMENT_MAX_LENGTH,
        )

    comment = Comment(submission_id=submission.id, author_id=user.id, text=cleaned)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def comment_to_response(comment: Comment) -> dict:
    author = comment.author
    role = author.role.code if author and author.role else "student"
    return {
        "id": comment.id,
        "submission_id": comment.submission_id,
        "author_id": comment.author_id,
        "author_name": (author.full_name or author.email) if author else "",
        "author_role": role,
        "text": comment.text,
        "created_at": comment.created_at,
    }


def submission_to_upload_info(submission: StudentSubmission, report: Report) -> dict:
    student = submission.student
    return {
        "id": submission.id,
        "lab_work_id": submission.lab_work_id,
        "lab_work_title": submission.lab_work.title if submission.lab_work else "",
        "student_id": submission.student_id,
        "student_name": (student.full_name or student.email) if student else "",
        "group_name": student.group_name if student else None,
        "status": submission.status,
        "file_name": report.file_name,
        "file_size_bytes": report.file_size_bytes,
        "submitted_at": submission.submitted_at,
        "updated_at": submission.updated_at,
    }