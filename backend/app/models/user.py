"""ORM-модели пользователей и ролей (WBS 4.1.2)."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Role(Base):
    """Роль пользователя: student / teacher."""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    title = Column(String(64), nullable=False)

    users = relationship("User", back_populates="role")

    def __repr__(self) -> str:
        return "<Role %s>" % self.code


class User(Base):
    """Пользователь системы (студент или преподаватель)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    full_name = Column(String(255), nullable=True)
    group_name = Column(String(50), nullable=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    role = relationship("Role", back_populates="users", lazy="joined")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return "<User %s>" % self.email