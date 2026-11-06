"""Эндпоинты регистрации и входа (WBS 4.1.2)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import Role, User
from app.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse

router = APIRouter()


def _get_role(db: Session, code: str) -> Role | None:
    return db.query(Role).filter(Role.code == code).first()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя (UC-01)",
)
def register(data: UserRegister, db: Session = Depends(get_db)) -> User:
    """Создаёт пользователя с хешированным паролем (bcrypt)."""
    email = data.email.lower()
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует",
        )

    role = _get_role(db, data.role)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Справочник ролей не заполнен",
        )

    user = User(
        email=email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        group_name=data.group_name or settings.DEFAULT_GROUP_NAME,
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход по email и паролю (UC-01)",
)
def login(data: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """Проверяет пароль и возвращает JWT."""
    user = db.query(User).filter(User.email == data.email.lower()).first()
    # Одинаковый ответ и для несуществующего email, и для неверного пароля
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учётная запись деактивирована",
        )

    access_token, expires_in = create_access_token(
        subject=str(user.id),
        extra={"role": user.role.code if user.role else None},
    )
    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )