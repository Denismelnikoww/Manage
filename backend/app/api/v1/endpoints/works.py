from typing import Optional, List, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from app.core.database import get_db
from app.models.lab_work import LabWork
from app.schemas.lab_work import (
    LabWorkCreate,
    LabWorkUpdate,
    LabWorkResponse,
    LabWorkListResponse,
)

router = APIRouter()

def get_current_role(x_user_role: Optional[str] = Header(default="teacher")) -> str:
    """
    Mock dependency for user role verification (AC 1.3, UC-01/UC-02).
    Will be connected to JWT token validation upon Auth module completion.
    """
    return x_user_role.lower() if x_user_role else "teacher"

def require_teacher(role: str = Depends(get_current_role)):
    if role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Действие доступно только пользователю с ролью преподавателя (403 Forbidden)"
        )
    return role

@router.post(
    "",
    response_model=LabWorkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создание новой лабораторной работы (UC-02 / US-02)"
)
def create_lab_work(
    data: LabWorkCreate,
    db: Session = Depends(get_db),
    _: str = Depends(require_teacher)
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
        is_deleted=False
    )
    db.add(new_work)
    db.commit()
    db.refresh(new_work)
    return new_work

@router.get(
    "",
    response_model=LabWorkListResponse,
    summary="Получение списка лабораторных работ (UC-03 / US-04)"
)
def get_lab_works(
    group_name: Optional[str] = Query("ВПР42", description="Фильтр по учебной группе"),
    sort_by: Literal["order_num", "deadline"] = Query("order_num", description="Поле сортировки"),
    sort_desc: bool = Query(False, description="Сортировка по убыванию"),
    db: Session = Depends(get_db)
):
    """
    Возвращает список всех активных лабораторных работ для академической группы.
    """
    query = db.query(LabWork).filter(LabWork.is_deleted == False)
    
    if group_name:
        query = query.filter(LabWork.group_name == group_name)
        
    order_column = LabWork.deadline if sort_by == "deadline" else LabWork.order_num
    query = query.order_by(desc(order_column) if sort_desc else asc(order_column))
    
    items = query.all()
    return LabWorkListResponse(total=len(items), items=items)

@router.get(
    "/{work_id}",
    response_model=LabWorkResponse,
    summary="Получение деталей лабораторной работы"
)
def get_lab_work(
    work_id: int,
    db: Session = Depends(get_db)
):
    """
    Получение подробной информации по конкретной лабораторной работе по её ID.
    """
    work = db.query(LabWork).filter(LabWork.id == work_id, LabWork.is_deleted == False).first()
    if not work:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Лабораторная работа с ID {work_id} не найдена"
        )
    return work

@router.patch(
    "/{work_id}",
    response_model=LabWorkResponse,
    summary="Редактирование параметров лабораторной работы (UC-02 / US-03)"
)
def update_lab_work(
    work_id: int,
    data: LabWorkUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(require_teacher)
):
    """
    Редактирование описания, названия или продление дедлайна работы (AC 3.1).
    Доступно только преподавателю.
    """
    work = db.query(LabWork).filter(LabWork.id == work_id, LabWork.is_deleted == False).first()
    if not work:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Лабораторная работа с ID {work_id} не найдена"
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
    summary="Удаление лабораторной работы (UC-02 / US-03)"
)
def delete_lab_work(
    work_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(require_teacher)
):
    """
    Мягкое удаление (soft delete) лабораторной работы.
    Доступно только преподавателю.
    """
    work = db.query(LabWork).filter(LabWork.id == work_id, LabWork.is_deleted == False).first()
    if not work:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Лабораторная работа с ID {work_id} не найдена"
        )
        
    work.is_deleted = True
    db.commit()
    return None
