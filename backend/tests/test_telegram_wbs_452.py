"""Тесты моделей и шаблонов Telegram-модуля (WBS 4.5.2)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.bot.templates import (
    escape,
    msg_invalid_token,
    msg_link_success,
    msg_new_submission,
    msg_start_without_token,
    msg_status_accepted,
    msg_status_rework,
    truncate_comment,
)
from app.core.database import Base
from app.models import (
    NOTIFICATION_EVENT_TYPES,
    NOTIFICATION_STATUSES,
    NotificationLog,
    Role,
    TelegramAuthToken,
    User,
)

pytestmark = pytest.mark.unit

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base.metadata.create_all(bind=engine)


def _seed_user() -> User:
    db = Session()
    role = Role(id=1, code="student", title="Студент")
    db.add(role)
    db.flush()
    user = User(
        id=1,
        email="tg@test.local",
        hashed_password="x",
        full_name="Тест Юзер",
        group_name="ВПР42",
        role_id=1,
        is_active=True,
        notifications_enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


_seed_user()


def test_notification_event_types_match_spec():
    assert "NEW_SUBMISSION" in NOTIFICATION_EVENT_TYPES
    assert "STATUS_CHANGED_ACCEPTED" in NOTIFICATION_EVENT_TYPES
    assert "STATUS_CHANGED_REWORK" in NOTIFICATION_EVENT_TYPES
    assert "NEW_COMMENT" in NOTIFICATION_EVENT_TYPES
    assert "TG_LINK_SUCCESS" in NOTIFICATION_EVENT_TYPES


def test_notification_statuses_match_spec():
    assert set(NOTIFICATION_STATUSES) == {
        "pending",
        "retrying",
        "sent",
        "failed",
        "skipped",
    }


def test_create_telegram_auth_token():
    db = Session()
    token = TelegramAuthToken(
        user_id=1,
        token="abc123token",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        is_used=False,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    assert token.id is not None
    assert token.is_used is False
    db.close()


def test_create_notification_log():
    db = Session()
    log = NotificationLog(
        recipient_id=1,
        submission_id=None,
        event_type="TG_LINK_SUCCESS",
        message_text="<b>ok</b>",
        status="pending",
        attempts=0,
        telegram_chat_id=123456,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    assert log.id is not None
    assert log.status == "pending"
    assert log.event_type == "TG_LINK_SUCCESS"
    db.close()


def test_user_notifications_enabled_default():
    db = Session()
    user = db.query(User).filter(User.id == 1).first()
    assert user.notifications_enabled is True
    db.close()


def test_html_escape_in_templates():
    dangerous = "A <b>B</b> & C"
    assert "&lt;b&gt;" in escape(dangerous)
    text = msg_link_success("Иван <script>", is_teacher=False, group_name="ВПР42")
    assert "<script>" not in text
    assert "&lt;script&gt;" in text


def test_start_templates_from_spec():
    assert "LabFlow" in msg_start_without_token()
    assert "недействительна" in msg_invalid_token()


def test_new_submission_templates():
    primary = msg_new_submission(
        student_name="Иванов",
        group_name="ВПР42",
        work_number=1,
        work_title="Git",
        file_name="a.pdf",
        submitted_at="22.11.2026 21:00",
        is_resubmission=False,
    )
    assert "Новая сдача" in primary
    retry = msg_new_submission(
        student_name="Иванов",
        group_name="ВПР42",
        work_number=1,
        work_title="Git",
        file_name="a.pdf",
        submitted_at="22.11.2026 21:00",
        is_resubmission=True,
    )
    assert "Повторная сдача" in retry


def test_status_templates():
    accepted = msg_status_accepted(
        work_number=2,
        work_title="Docker",
        teacher_name="Иванова",
        comment_text=None,
    )
    assert "принята" in accepted.lower() or "Принята" in accepted
    assert "Комментарий преподавателя" not in accepted

    rework = msg_status_rework(
        work_number=2,
        work_title="Docker",
        teacher_name="Иванова",
        comment_text="Исправьте выводы",
    )
    assert "На доработке" in rework
    assert "Исправьте выводы" in rework


def test_truncate_comment():
    long = "x" * 1200
    truncated = truncate_comment(long, limit=1000)
    assert truncated.endswith("… (полный текст доступен в LabFlow)")
    assert len(truncated) < len(long)
