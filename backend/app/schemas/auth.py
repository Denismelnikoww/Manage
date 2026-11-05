"""Pydantic-схемы модуля аутентификации (WBS 4.1.2)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RoleResponse(BaseModel):
    id: int
    code: str
    title: str

    model_config = ConfigDict(from_attributes=True)


class UserRegister(BaseModel):
    email: EmailStr = Field(..., description="Email (логин)")
    password: str = Field(..., min_length=8, max_length=72, description="Пароль, минимум 8 символов")
    full_name: str | None = Field(default=None, max_length=255)
    group_name: str | None = Field(default=None, max_length=50, description="Учебная группа, например ВПР42")
    role: Literal["student", "teacher"] = Field(default="student", description="Роль пользователя")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    group_name: str | None = None
    telegram_id: int | None = None
    is_active: bool
    role: RoleResponse
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse