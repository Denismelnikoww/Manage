"""Идемпотентное заполнение справочника ролей при старте приложения."""

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.user import Role

DEFAULT_ROLES = (
    ("student", "Студент"),
    ("teacher", "Преподаватель"),
)


def seed_roles(db: Session) -> None:
    """Создаёт роли student/teacher, если их ещё нет."""
    existing = {code for (code,) in db.query(Role.code).all()}
    created = False
    for code, title in DEFAULT_ROLES:
        if code not in existing:
            db.add(Role(code=code, title=title))
            created = True
    if created:
        db.commit()


def seed_roles_on_startup() -> None:
    db = SessionLocal()
    try:
        seed_roles(db)
    finally:
        db.close()