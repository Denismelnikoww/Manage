"""Тесты API смены статуса сдачи (WBS 4.3.2)."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models import LabWork, Role, StudentSubmission, SubmissionStatusHistory, User
from app.models.comment import Comment

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def _override_db():
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    yield
    if previous is not None:
        app.dependency_overrides[get_db] = previous
    else:
        app.dependency_overrides.pop(get_db, None)


def _seed():
    db = TestingSessionLocal()
    try:
        if db.query(User).filter(User.id == 1).first() is not None:
            return
        db.add_all([
            Role(id=1, code="student", title="Студент"),
            Role(id=2, code="teacher", title="Преподаватель"),
        ])
        db.flush()
        db.add_all([
            User(
                id=1,
                email="student1@test.local",
                hashed_password="x",
                full_name="Студент Первый",
                group_name="ВПР42",
                role_id=1,
                is_active=True,
            ),
            User(
                id=2,
                email="teacher@test.local",
                hashed_password="x",
                full_name="Преподаватель",
                group_name="ВПР42",
                role_id=2,
                is_active=True,
            ),
            User(
                id=3,
                email="student2@test.local",
                hashed_password="x",
                full_name="Студент Второй",
                group_name="ВПР42",
                role_id=1,
                is_active=True,
            ),
        ])
        deadline = datetime.now(timezone.utc) + timedelta(days=30)
        for lab_id in range(1, 7):
            db.add(
                LabWork(
                    id=lab_id,
                    order_num=lab_id,
                    title="ЛР %s" % lab_id,
                    description="Описание %s" % lab_id,
                    deadline=deadline,
                    group_name="ВПР42",
                    is_deleted=False,
                )
            )
        db.flush()
        # 1: not_started (взять в работу)
        # 2: submitted (принять / на доработку)
        # 3: accepted (терминальный)
        # 4: in_progress (запрещённый PATCH → submitted)
        # 5: чужая сдача student2 not_started
        # 6: submitted без комментария → needs_work
        submissions = [
            (1, 1, 1, "not_started"),
            (2, 2, 1, "submitted"),
            (3, 3, 1, "accepted"),
            (4, 4, 1, "in_progress"),
            (5, 5, 3, "not_started"),
            (6, 6, 1, "submitted"),
        ]
        for sub_id, lab_id, student_id, status in submissions:
            db.add(
                StudentSubmission(
                    id=sub_id,
                    lab_work_id=lab_id,
                    student_id=student_id,
                    status=status,
                )
            )
        db.commit()
    finally:
        db.close()


_seed()


def auth_headers(user_id: int, role: str) -> dict:
    token, _ = create_access_token(subject=str(user_id), extra={"role": role})
    return {"Authorization": "Bearer %s" % token}


def student_headers() -> dict:
    return auth_headers(1, "student")


def teacher_headers() -> dict:
    return auth_headers(2, "teacher")


def second_student_headers() -> dict:
    return auth_headers(3, "student")


def patch_status(submission_id: int, payload: dict, headers: dict):
    return client.patch(
        "/api/v1/submissions/%s/status" % submission_id,
        json=payload,
        headers=headers,
    )


def test_student_take_in_progress():
    response = patch_status(1, {"status": "in_progress"}, student_headers())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["id"] == 1

    history = client.get(
        "/api/v1/submissions/1/status-history",
        headers=student_headers(),
    )
    assert history.status_code == 200
    body = history.json()
    assert body["total"] >= 1
    assert body["items"][-1]["from_status"] == "not_started"
    assert body["items"][-1]["to_status"] == "in_progress"
    assert body["items"][-1]["changed_by_id"] == 1


def test_student_foreign_submission_forbidden():
    response = patch_status(5, {"status": "in_progress"}, student_headers())
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_teacher_cannot_take_in_progress():
    response = patch_status(5, {"status": "in_progress"}, teacher_headers())
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_teacher_accept_submission():
    response = patch_status(
        2,
        {"status": "accepted", "comment_text": "Отлично, принято"},
        teacher_headers(),
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "accepted"
    assert data["reviewed_at"] is not None

    db = TestingSessionLocal()
    try:
        comments = db.query(Comment).filter(Comment.submission_id == 2).all()
        assert any("Отлично" in c.text for c in comments)
        hist = (
            db.query(SubmissionStatusHistory)
            .filter(
                SubmissionStatusHistory.submission_id == 2,
                SubmissionStatusHistory.to_status == "accepted",
            )
            .first()
        )
        assert hist is not None
        assert hist.changed_by_id == 2
    finally:
        db.close()


def test_teacher_needs_work_requires_comment():
    response = patch_status(6, {"status": "needs_work"}, teacher_headers())
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_COMMENT"


def test_teacher_needs_work_with_comment():
    # lab_work_id=6 ещё не занят парой (6, student=1) — в seed id=6 это submitted на ЛР6
    # используем уже seeded submission #6, если предыдущий тест не менял её статус
    db = TestingSessionLocal()
    try:
        sub = db.query(StudentSubmission).filter(StudentSubmission.id == 6).first()
        assert sub is not None
        sub.status = "submitted"
        db.commit()
    finally:
        db.close()

    response = patch_status(
        6,
        {"status": "needs_work", "comment_text": "Исправьте выводы"},
        teacher_headers(),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "needs_work"


def test_student_cannot_accept():
    db = TestingSessionLocal()
    try:
        # сдача #2 могла быть принята другим тестом — создаём/сбрасываем через свободный id
        existing = db.query(StudentSubmission).filter(StudentSubmission.id == 2).first()
        if existing is not None:
            existing.status = "submitted"
            db.commit()
            target_id = 2
        else:
            target_id = 2
    finally:
        db.close()

    response = patch_status(target_id, {"status": "accepted"}, student_headers())
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_invalid_transition_in_progress_to_accepted():
    response = patch_status(4, {"status": "accepted"}, teacher_headers())
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_TRANSITION"


def test_accepted_is_terminal():
    response = patch_status(3, {"status": "needs_work", "comment_text": "Поздно"}, teacher_headers())
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_SUBMISSION_STATE"


def test_status_change_requires_token():
    response = client.patch(
        "/api/v1/submissions/1/status",
        json={"status": "in_progress"},
    )
    assert response.status_code == 401


def test_status_history_foreign_student_forbidden():
    response = client.get(
        "/api/v1/submissions/1/status-history",
        headers=second_student_headers(),
    )
    assert response.status_code == 403


def test_unknown_submission():
    response = patch_status(999, {"status": "in_progress"}, student_headers())
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
