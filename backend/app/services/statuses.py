"""Бизнес-логика смены статусов сдачи (WBS 4.3.2).

Разрешённые переходы через PATCH (матрица 4.3.1 / RBAC §5):
- student (владелец): not_started → in_progress
- teacher: submitted → accepted (comment опционален)
- teacher: submitted → needs_work (comment ≥ 5 символов обязателен)

Переходы в submitted выполняются через upload (4.4.3), не через PATCH.
Статус accepted терминальный: любая попытка смены → 409.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.comment import Comment
from app.models.status_history import SubmissionStatusHistory
from app.models.submission import SUBMISSION_STATUSES, StudentSubmission
from app.models.user import User
from app.services.reports import ensure_can_view, get_submission_or_404

COMMENT_MIN_LENGTH = 5
COMMENT_MAX_LENGTH = 2000

# (from_status, to_status) → требуемая роль
PATCH_TRANSITIONS: dict[tuple[str, str], str] = {
    ("not_started", "in_progress"): "student",
    ("submitted", "accepted"): "teacher",
    ("submitted", "needs_work"): "teacher",
}


def append_status_history(
    db: Session,
    submission: StudentSubmission,
    from_status: str,
    to_status: str,
    user: User,
    comment_text: str | None = None,
) -> SubmissionStatusHistory:
    """Добавляет запись истории в сессию (без commit)."""
    entry = SubmissionStatusHistory(
        submission_id=submission.id,
        from_status=from_status,
        to_status=to_status,
        changed_by_id=user.id,
        comment_text=comment_text,
    )
    db.add(entry)
    return entry


def _role_code(user: User) -> str | None:
    return user.role.code if user.role else None


def _normalize_comment(raw: str | None, *, required: bool) -> str | None:
    cleaned = (raw or "").strip()
    if required:
        if len(cleaned) < COMMENT_MIN_LENGTH:
            raise ApiError(
                400,
                "INVALID_COMMENT",
                "При отправке на доработку комментарий обязателен (минимум %s символов)"
                % COMMENT_MIN_LENGTH,
                details=[{
                    "field": "comment_text",
                    "issue": "После strip() осталось %s символов" % len(cleaned),
                }],
            )
    if cleaned and len(cleaned) > COMMENT_MAX_LENGTH:
        raise ApiError(
            400,
            "INVALID_COMMENT",
            "Комментарий не может быть длиннее %s символов" % COMMENT_MAX_LENGTH,
        )
    return cleaned or None


def change_submission_status(
    db: Session,
    user: User,
    submission: StudentSubmission,
    target_status: str,
    comment_text: str | None = None,
) -> StudentSubmission:
    """Выполняет разрешённый PATCH-переход статуса с записью истории."""
    if target_status not in SUBMISSION_STATUSES:
        raise ApiError(
            400,
            "INVALID_TRANSITION",
            "Недопустимый целевой статус: %s" % target_status,
        )

    current = submission.status
    if current == "accepted":
        raise ApiError(
            409,
            "INVALID_SUBMISSION_STATE",
            "Работа уже защищена и не может быть изменена",
            details=[{"field": "status", "issue": "Статус 'accepted' терминальный"}],
        )

    role = _role_code(user)
    required_role = PATCH_TRANSITIONS.get((current, target_status))

    if required_role is None:
        raise ApiError(
            400,
            "INVALID_TRANSITION",
            "Переход '%s' → '%s' запрещён правилами жизненного цикла"
            % (current, target_status),
            details=[{
                "field": "status",
                "issue": "Допустимые PATCH-переходы: not_started→in_progress (студент), "
                         "submitted→accepted / submitted→needs_work (преподаватель)",
            }],
        )

    if role != required_role:
        raise ApiError(
            403,
            "FORBIDDEN",
            "Недостаточно прав для перехода '%s' → '%s'" % (current, target_status),
        )

    if required_role == "student" and submission.student_id != user.id:
        raise ApiError(
            403,
            "FORBIDDEN",
            "Вы можете менять статус только своей сдачи",
        )

    need_comment = target_status == "needs_work"
    normalized = _normalize_comment(comment_text, required=need_comment)

    # Опциональный/обязательный комментарий преподавателя сохраняем в comments
    if normalized and required_role == "teacher":
        db.add(
            Comment(
                submission_id=submission.id,
                author_id=user.id,
                text=normalized,
            )
        )

    submission.status = target_status
    if target_status in ("accepted", "needs_work"):
        submission.reviewed_at = datetime.now(timezone.utc)

    append_status_history(
        db,
        submission,
        from_status=current,
        to_status=target_status,
        user=user,
        comment_text=normalized,
    )

    db.commit()
    db.refresh(submission)
    return submission


def list_status_history(
    db: Session,
    user: User,
    submission: StudentSubmission,
) -> list[SubmissionStatusHistory]:
    ensure_can_view(user, submission)
    return (
        db.query(SubmissionStatusHistory)
        .filter(SubmissionStatusHistory.submission_id == submission.id)
        .order_by(SubmissionStatusHistory.created_at.asc())
        .all()
    )


def submission_to_status_response(submission: StudentSubmission) -> dict:
    student = submission.student
    return {
        "id": submission.id,
        "lab_work_id": submission.lab_work_id,
        "lab_work_title": submission.lab_work.title if submission.lab_work else "",
        "student_id": submission.student_id,
        "student_name": (student.full_name or student.email) if student else "",
        "group_name": student.group_name if student else None,
        "status": submission.status,
        "submitted_at": submission.submitted_at,
        "reviewed_at": submission.reviewed_at,
        "updated_at": submission.updated_at,
    }


def history_to_response(entry: SubmissionStatusHistory) -> dict:
    actor = entry.changed_by
    return {
        "id": entry.id,
        "submission_id": entry.submission_id,
        "from_status": entry.from_status,
        "to_status": entry.to_status,
        "changed_by_id": entry.changed_by_id,
        "changed_by_name": (actor.full_name or actor.email) if actor else "",
        "comment_text": entry.comment_text,
        "created_at": entry.created_at,
    }


# Реэкспорт для эндпоинта
__all__ = [
    "append_status_history",
    "change_submission_status",
    "get_submission_or_404",
    "history_to_response",
    "list_status_history",
    "submission_to_status_response",
]
