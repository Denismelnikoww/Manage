"""ORM-модели Telegram-модуля: токены привязки и журнал уведомлений (WBS 4.5.2)."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base

# Коды событий из Спецификации Telegram (раздел 2.1)
NOTIFICATION_EVENT_TYPES = (
    "TG_LINK_SUCCESS",
    "NEW_SUBMISSION",
    "STATUS_CHANGED_ACCEPTED",
    "STATUS_CHANGED_REWORK",
    "NEW_COMMENT",
    "TG_UNLINK_INFO",
)

# Жизненный цикл доставки (раздел 4.1)
NOTIFICATION_STATUSES = (
    "pending",
    "retrying",
    "sent",
    "failed",
    "skipped",
)


class TelegramAuthToken(Base):
    """Одноразовый deep-link токен привязки Telegram (TTL 10 мин, ERD §3.6)."""

    __tablename__ = "telegram_auth_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="telegram_auth_tokens")


class NotificationLog(Base):
    """Журнал истории уведомлений (Спецификация TG §4.1 / WBS 4.5.2)."""

    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    recipient_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    submission_id = Column(
        Integer,
        ForeignKey("student_submissions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type = Column(String(64), nullable=False, index=True)
    message_text = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # chat_id на момент постановки (для отправки без join; Could-удобство)
    telegram_chat_id = Column(BigInteger, nullable=True)

    recipient = relationship("User", backref="notification_logs")
    submission = relationship("StudentSubmission", backref="notification_logs")
