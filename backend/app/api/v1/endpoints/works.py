from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_teacher
from app.core.database import get_db
from app.models.lab_work import LabWork
from app.models.submission import SUBMISSION_STATUSES, StudentSubmission
from app.models.user import Role, User
from app.schemas.lab_work import (
    LabWorkCreate,
    LabWorkListItemResponse,
    LabWorkListResponse,
    LabWorkResponse,
    LabWorkUpdate,
    SubmissionShortResponse,
    SubmissionStatus,
)

router = APIRouter()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _deadline_fields(deadline: datetime, now: datetime) -> tuple[bool, int]:
    target = _as_utc(deadline)
    delta = target - now
    days = int(delta.total_seconds() // 86400)
    return target < now, days


def _init_submissions_for_group(db: Session, work: LabWork) -> None:
    """При создании ЛР создаём сдачи not_started для активных студентов группы."""
    students = (
        db.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(
            User.is_active.is_(True),
            User.group_name == work.group_name,
            Role.code == "student",
        )
        .all()
    )
    for student in students:
        db.add(
            StudentSubmission(
                lab_work_id=work.id,
                student_id=student.id,
                status="not_started",
            )
        )


def _to_list_item(
    work: LabWork,
    now: datetime,
    submission: Optional[StudentSubmission] = None,
) -> LabWorkListItemResponse:
    is_overdue, days_until = _deadline_fields(work.deadline, now)
    short = None
    if submission is not None:
        short = SubmissionShortResponse(
            id=submission.id,
            status=submission.status,  # type: ignore[arg-type]
            submitted_at=submission.submitted_at,
        )
    return LabWorkListItemResponse(
        id=work.id,
        order_num=work.order_num,
        title=work.title,
        description=work.description,
        deadline=work.deadline,
        group_name=work.group_name,
        is_deleted=work.is_deleted,
        created_at=work.created_at,
        updated_at=work.updated_at,
        is_overdue=is_overdue,
        days_until_deadline=days_until,
        student_submission=short,
    )


@router.post(
    "",
    response_model=LabWorkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создание новой лабораторной работы (UC-02 / US-02)",
)
def create_lab_work(
    data: LabWorkCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
):
    """
    Создание и публикация новой лабораторной работы.
    Доступно только преподавателю.
    Проверяет, что дедлайн установлен в будущем времени (AC 2.2).
    """
    new_work = LabWork(
        order_num=data.order_num,
        title=data.title,
        description=data.description,
        deadline=data.deadline,
        group_name=data.group_name,
        is_deleted=False,
    )
    db.add(new_work)
    db.flush()
    _init_submissions_for_group(db, new_work)
    db.commit()
    db.refresh(new_work)
    return new_work


@router.get(
    "",
    response_model=LabWorkListResponse,
    summary="Список работ с фильтрацией и сортировкой (WBS 4.2.3 / FR-09)",
)
def get_lab_works(
    current_user: CurrentUser,
    group_name: Optional[str] = Query("ВПР42", description="Фильтр по учебной группе"),
    status_filter: Optional[SubmissionStatus] = Query(
        None,
        alias="status",
        description="Фильтр по статусу сдачи (для студента — своя сдача)",
    ),
    sort_by: Literal["order_num", "deadline"] = Query(
        "order_num",
        description="Поле сортировки: порядковый номер или дедлайн",
    ),
    sort_desc: bool = Query(False, description="Сортировка по убыванию"),
    deadline_from: Optional[datetime] = Query(
        None,
        description="Нижняя граница дедлайна (включительно)",
    ),
    deadline_to: Optional[datetime] = Query(
        None,
        description="Верхняя граница дедлайна (включительно)",
    ),
    overdue: Optional[bool] = Query(
        None,
        description="true — только просроченные, false — только актуальные",
    ),
    db: Session = Depends(get_db),
):
    """
    Возвращает список активных лабораторных работ группы.

    Фильтры (FR-09 / AC 4.3):
    - `status` — статус сдачи студента;
    - `deadline_from` / `deadline_to` / `overdue` — по дедлайну;
    - `sort_by` + `sort_desc` — сортировка по номеру или дедлайну.
    """
    if status_filter is not None and status_filter not in SUBMISSION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Недопустимый статус: {status_filter}",
        )

    now = datetime.now(timezone.utc)
    role_code = current_user.role.code if current_user.role else None

    query = db.query(LabWork).filter(LabWork.is_deleted.is_(False))

    if group_name:
        query = query.filter(LabWork.group_name == group_name)

    if deadline_from is not None:
        query = query.filter(LabWork.deadline >= _as_utc(deadline_from))
    if deadline_to is not None:
        query = query.filter(LabWork.deadline <= _as_utc(deadline_to))
    if overdue is True:
        query = query.filter(LabWork.deadline < now)
    elif overdue is False:
        query = query.filter(LabWork.deadline >= now)

    # Фильтр по статусу сдачи
    if status_filter is not None:
        if role_code == "student":
            query = (
                query.join(
                    StudentSubmission,
                    StudentSubmission.lab_work_id == LabWork.id,
                )
                .filter(
                    StudentSubmission.student_id == current_user.id,
                    StudentSubmission.status == status_filter,
                )
                .distinct()
            )
        else:
            # Преподаватель: работы, у которых есть хотя бы одна сдача с этим статусом
            query = (
                query.join(
                    StudentSubmission,
                    StudentSubmission.lab_work_id == LabWork.id,
                )
                .filter(StudentSubmission.status == status_filter)
                .distinct()
            )

    order_column = LabWork.deadline if sort_by == "deadline" else LabWork.order_num
    query = query.order_by(desc(order_column) if sort_desc else asc(order_column))

    works = query.all()

    # Персональные сдачи студента одним запросом
    submissions_by_work: dict[int, StudentSubmission] = {}
    if role_code == "student" and works:
        work_ids = [w.id for w in works]
        rows = (
            db.query(StudentSubmission)
            .filter(
                StudentSubmission.student_id == current_user.id,
                StudentSubmission.lab_work_id.in_(work_ids),
            )
            .all()
        )
        submissions_by_work = {row.lab_work_id: row for row in rows}

    items = [
        _to_list_item(work, now, submissions_by_work.get(work.id))
        for work in works
    ]
    return LabWorkListResponse(total=len(items), items=items)


@router.get(
    "/{work_id}",
    response_model=LabWorkResponse,
    summary="Получение деталей лабораторной работы",
)
def get_lab_work(
    work_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Получение подробной информации по конкретной лабораторной работе по её ID."""
    work = (
        db.query(LabWork)
        .filter(LabWork.id == work_id, LabWork.is_deleted.is_(False))
        .first()
    )
    if not work:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Лабораторная работа с ID {work_id} не найдена",
        )
    return work


@router.patch(
    "/{work_id}",
    response_model=LabWorkResponse,
    summary="Редактирование параметров лабораторной работы (UC-02 / US-03)",
)
def update_lab_work(
    work_id: int,
    data: LabWorkUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
):
    """
    Редактирование описания, названия или продление дедлайна работы (AC 3.1).
    Доступно только преподавателю.
    """
    work = (
        db.query(LabWork)
        .filter(LabWork.id == work_id, LabWork.is_deleted.is_(False))
        .first()
    )
    if not work:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Лабораторная работа с ID {work_id} не найдена",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(work, field, value)

    db.commit()
    db.refresh(work)
    return work


@router.delete(
    "/{work_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление лабораторной работы (UC-02 / US-03)",
)
def delete_lab_work(
    work_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher),
):
    """
    Мягкое удаление (soft delete) лабораторной работы.
    Доступно только преподавателю.
    """
    work = (
        db.query(LabWork)
        .filter(LabWork.id == work_id, LabWork.is_deleted.is_(False))
        .first()
    )
    if not work:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Лабораторная работа с ID {work_id} не найдена",
        )

    work.is_deleted = True
    db.commit()
    return None
