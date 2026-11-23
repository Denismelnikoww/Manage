"""Общие фикстуры pytest (WBS 2.2.2).

Изоляция: схема создаётся на каждый тест; без жёстких обращений к id=1.
БД: SQLite in-memory по умолчанию; PostgreSQL при TEST_DATABASE_URL / CI.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app as fastapi_app
from app.models import LabWork, Role, User

# Импорт моделей для Base.metadata (отчёты/telegram/статусы)
import app.models  # noqa: F401

TEST_PASSWORD = "ValidPass123"
GROUP_NAME = "ВПР42"


def pytest_configure(config: pytest.Config) -> None:
    # Гарантируем регистрацию маркеров даже без pytest.ini (IDE / alternate cwd)
    for marker in (
        "unit: модульные тесты без внешней PostgreSQL",
        "integration: интеграционные тесты с PostgreSQL 16",
        "security: проверки 401/403, подмены токена, IDOR",
        "slow: медленные тесты (ночной прогон)",
    ):
        config.addinivalue_line("markers", marker)


def _database_url() -> str:
    return (
        os.getenv("TEST_DATABASE_URL")
        or os.getenv("DATABASE_URL_TEST")
        or "sqlite://"
    )


def _is_postgres(url: str) -> bool:
    return url.startswith("postgresql")


@pytest.fixture(scope="session")
def db_url() -> str:
    return _database_url()


@pytest.fixture
def engine(db_url: str):
    """Движок БД на тест: SQLite StaticPool или PostgreSQL из CI service."""
    if _is_postgres(db_url):
        eng = create_engine(db_url, pool_pre_ping=True)
    else:
        eng = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(eng, "connect")
        def _fk_on(dbapi_conn, _connection_record):  # noqa: ANN001
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.drop_all(bind=eng)
    Base.metadata.create_all(bind=eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(bind=eng)
        eng.dispose()


@pytest.fixture
def db_session(engine) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seed_roles(db_session: Session) -> dict[str, Role]:
    student = Role(code="student", title="Студент")
    teacher = Role(code="teacher", title="Преподаватель")
    db_session.add_all([student, teacher])
    db_session.commit()
    db_session.refresh(student)
    db_session.refresh(teacher)
    return {"student": student, "teacher": teacher}


@pytest.fixture
def make_user(db_session: Session, seed_roles: dict[str, Role]) -> Callable[..., User]:
    def _factory(
        *,
        email: str,
        role: str = "student",
        full_name: str = "Тест Пользователь",
        group_name: str | None = GROUP_NAME,
        is_active: bool = True,
        password: str = TEST_PASSWORD,
    ) -> User:
        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            full_name=full_name,
            group_name=group_name,
            role_id=seed_roles[role].id,
            is_active=is_active,
            notifications_enabled=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _factory


@pytest.fixture
def student_user(make_user: Callable[..., User]) -> User:
    return make_user(
        email="student@example.com",
        role="student",
        full_name="Тестовый Студент",
    )


@pytest.fixture
def teacher_user(make_user: Callable[..., User]) -> User:
    return make_user(
        email="teacher@example.com",
        role="teacher",
        full_name="Тестовый Преподаватель",
        group_name=GROUP_NAME,
    )


@pytest.fixture
def inactive_user(make_user: Callable[..., User]) -> User:
    return make_user(
        email="inactive@example.com",
        role="student",
        full_name="Деактивированный",
        is_active=False,
    )


@pytest.fixture
def make_work(db_session: Session) -> Callable[..., LabWork]:
    def _factory(
        *,
        order_num: int = 1,
        title: str = "ЛР №1: Тестовая работа",
        description: str = "Описание лабораторной работы для автотестов",
        days: int = 7,
        group_name: str = GROUP_NAME,
        deadline: datetime | None = None,
    ) -> LabWork:
        work = LabWork(
            order_num=order_num,
            title=title,
            description=description,
            deadline=deadline
            or (datetime.now(timezone.utc) + timedelta(days=days)),
            group_name=group_name,
            is_deleted=False,
        )
        db_session.add(work)
        db_session.commit()
        db_session.refresh(work)
        return work

    return _factory


@pytest.fixture
def auth_headers() -> Callable[..., dict[str, str]]:
    def _factory(user: User, role: str | None = None) -> dict[str, str]:
        role_code = role or (user.role.code if user.role else "student")
        token, _ = create_access_token(
            subject=str(user.id),
            extra={"role": role_code},
        )
        return {"Authorization": "Bearer %s" % token}

    return _factory


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """HTTP-клиент с подменой get_db. lifespan не запускаем (нет боевой БД/MinIO)."""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    previous = fastapi_app.dependency_overrides.get(get_db)
    fastapi_app.dependency_overrides[get_db] = _override_get_db
    test_client = TestClient(fastapi_app)
    try:
        yield test_client
    finally:
        if previous is not None:
            fastapi_app.dependency_overrides[get_db] = previous
        else:
            fastapi_app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def future_deadline_iso() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()


@pytest.fixture
def past_deadline_iso() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


@pytest.fixture
def work_payload(future_deadline_iso: str) -> dict[str, Any]:
    return {
        "order_num": 1,
        "title": "ЛР №1: Основы Git и CI/CD",
        "description": "Изучить Git-flow, настроить защиту веток и CI пайплайн.",
        "deadline": future_deadline_iso,
        "group_name": GROUP_NAME,
    }
