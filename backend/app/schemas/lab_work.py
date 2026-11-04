from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict

class LabWorkBase(BaseModel):
    order_num: int = Field(..., ge=1, description="Порядковый номер лабораторной работы (например, 1, 2, ...)")
    title: str = Field(..., min_length=3, max_length=255, description="Название работы (например: 'ЛР №1: Основы Git')")
    description: str = Field(..., min_length=5, description="Подробное описание задания и требования к сдаче")
    deadline: datetime = Field(..., description="Дата и время дедлайна сдачи работы")
    group_name: str = Field(default="ВПР42", min_length=2, max_length=50, description="Академическая группа")

class LabWorkCreate(LabWorkBase):
    @field_validator("deadline")
    @classmethod
    def validate_future_deadline(cls, v: datetime) -> datetime:
        now = datetime.now(timezone.utc)
        target = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if target < now:
            raise ValueError("Дедлайн не может быть установлен в прошлом времени (AC 2.2)")
        return v

class LabWorkUpdate(BaseModel):
    order_num: Optional[int] = Field(None, ge=1)
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, min_length=5)
    deadline: Optional[datetime] = None
    group_name: Optional[str] = Field(None, min_length=2, max_length=50)

class LabWorkResponse(LabWorkBase):
    id: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LabWorkListResponse(BaseModel):
    total: int
    items: List[LabWorkResponse]
