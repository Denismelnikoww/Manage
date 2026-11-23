"""Must-набор CRUD работ для PR-гейта (WBS 2.2.2 §5.2)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.submission import StudentSubmission
from tests.conftest import GROUP_NAME

pytestmark = pytest.mark.unit


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_tc_work_001_create_by_teacher(client, teacher_user, auth_headers, work_payload):
    """TC-WORK-001: создание работы преподавателем → 201, is_deleted=false."""
    response = client.post(
        "/api/v1/works",
        json=work_payload,
        headers=auth_headers(teacher_user),
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["title"] == work_payload["title"]
    assert data["group_name"] == GROUP_NAME
    assert data["order_num"] == work_payload["order_num"]
    assert data["is_deleted"] is False
    assert data["id"] is not None


@pytest.mark.security
def test_tc_work_003_create_without_token(client, work_payload):
    """TC-WORK-003: создание без токена → 401."""
    response = client.post("/api/v1/works", json=work_payload)
    assert response.status_code == 401


def test_tc_work_005_title_too_short(client, teacher_user, auth_headers, work_payload):
    """TC-WORK-005: название из 2 символов → 422."""
    payload = {**work_payload, "title": "ЛР"}
    response = client.post(
        "/api/v1/works",
        json=payload,
        headers=auth_headers(teacher_user),
    )
    assert response.status_code == 422


def test_tc_work_010_past_deadline(client, teacher_user, auth_headers, work_payload, past_deadline_iso):
    """TC-WORK-010: дедлайн в прошлом → 422."""
    payload = {**work_payload, "deadline": past_deadline_iso}
    response = client.post(
        "/api/v1/works",
        json=payload,
        headers=auth_headers(teacher_user),
    )
    assert response.status_code == 422


@pytest.mark.integration
def test_tc_work_017_init_submissions(
    client, db_session: Session, teacher_user, student_user, make_user, auth_headers, work_payload
):
    """TC-WORK-017: при создании ЛР — сдача not_started на каждого активного студента группы."""
    other = make_user(email="student2@example.com", role="student", full_name="Студент 2")
    inactive = make_user(
        email="inactive.student@example.com",
        role="student",
        full_name="Неактивный",
        is_active=False,
    )
    other_group = make_user(
        email="other.group@example.com",
        role="student",
        full_name="Другая группа",
        group_name="ВПР43",
    )

    response = client.post(
        "/api/v1/works",
        json=work_payload,
        headers=auth_headers(teacher_user),
    )
    assert response.status_code == 201, response.text
    work_id = response.json()["id"]

    subs = (
        db_session.query(StudentSubmission)
        .filter(StudentSubmission.lab_work_id == work_id)
        .all()
    )
    student_ids = {s.student_id for s in subs}
    assert student_user.id in student_ids
    assert other.id in student_ids
    assert inactive.id not in student_ids
    assert other_group.id not in student_ids
    assert all(s.status == "not_started" for s in subs)
    assert len(subs) == 2


def test_tc_work_019_list_for_teacher(client, teacher_user, auth_headers, work_payload):
    """TC-WORK-019: список для преподавателя — total/items, только активные."""
    created = client.post(
        "/api/v1/works",
        json=work_payload,
        headers=auth_headers(teacher_user),
    )
    assert created.status_code == 201
    work_id = created.json()["id"]

    response = client.get(
        "/api/v1/works?group_name=%s" % GROUP_NAME,
        headers=auth_headers(teacher_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert "total" in data and "items" in data
    assert data["total"] >= 1
    assert any(item["id"] == work_id for item in data["items"])
    assert all(item["is_deleted"] is False for item in data["items"])


@pytest.mark.security
def test_tc_work_022_list_without_token(client):
    """TC-WORK-022: список без токена → 401."""
    response = client.get("/api/v1/works")
    assert response.status_code == 401


def test_tc_work_026_sort_by_deadline(
    client, teacher_user, student_user, auth_headers, work_payload
):
    """TC-WORK-026: сортировка по дедлайну — ближайший первым."""
    early = {
        **work_payload,
        "order_num": 10,
        "title": "Ранний дедлайн работы CI",
        "deadline": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
    }
    late = {
        **work_payload,
        "order_num": 11,
        "title": "Поздний дедлайн работы CI",
        "deadline": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    }
    early_id = client.post("/api/v1/works", json=early, headers=auth_headers(teacher_user)).json()["id"]
    late_id = client.post("/api/v1/works", json=late, headers=auth_headers(teacher_user)).json()["id"]

    response = client.get(
        "/api/v1/works?group_name=%s&sort_by=deadline&sort_desc=false" % GROUP_NAME,
        headers=auth_headers(student_user),
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids.index(early_id) < ids.index(late_id)


def test_tc_work_029_get_existing(client, teacher_user, auth_headers, work_payload):
    """TC-WORK-029: детали существующей работы → 200."""
    created = client.post(
        "/api/v1/works",
        json=work_payload,
        headers=auth_headers(teacher_user),
    )
    work_id = created.json()["id"]
    response = client.get(
        "/api/v1/works/%s" % work_id,
        headers=auth_headers(teacher_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == work_id
    assert data["title"] == work_payload["title"]
    assert data["group_name"] == GROUP_NAME
    assert "deadline" in data


def test_tc_work_030_missing_and_deleted(client, teacher_user, auth_headers, work_payload):
    """TC-WORK-030: несуществующая и удалённая → 404."""
    missing = client.get("/api/v1/works/999999", headers=auth_headers(teacher_user))
    assert missing.status_code == 404

    created = client.post(
        "/api/v1/works",
        json=work_payload,
        headers=auth_headers(teacher_user),
    )
    work_id = created.json()["id"]
    delete = client.delete("/api/v1/works/%s" % work_id, headers=auth_headers(teacher_user))
    assert delete.status_code == 204
    deleted = client.get("/api/v1/works/%s" % work_id, headers=auth_headers(teacher_user))
    assert deleted.status_code == 404


def test_tc_work_036_extend_deadline(client, teacher_user, auth_headers, work_payload):
    """TC-WORK-036: продление дедлайна → 200, updated_at меняется."""
    created = client.post(
        "/api/v1/works",
        json=work_payload,
        headers=auth_headers(teacher_user),
    )
    data = created.json()
    work_id = data["id"]
    old_updated = data["updated_at"]
    new_deadline = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()

    response = client.patch(
        "/api/v1/works/%s" % work_id,
        json={"deadline": new_deadline},
        headers=auth_headers(teacher_user),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == work_id
    assert body["updated_at"] != old_updated or body["deadline"] != data["deadline"]


def test_tc_work_049_soft_delete(client, db_session: Session, teacher_user, auth_headers, work_payload):
    """TC-WORK-049: soft delete → 204, GET 404, строка остаётся в БД."""
    from app.models.lab_work import LabWork

    created = client.post(
        "/api/v1/works",
        json=work_payload,
        headers=auth_headers(teacher_user),
    )
    work_id = created.json()["id"]
    response = client.delete(
        "/api/v1/works/%s" % work_id,
        headers=auth_headers(teacher_user),
    )
    assert response.status_code == 204
    assert client.get("/api/v1/works/%s" % work_id, headers=auth_headers(teacher_user)).status_code == 404

    row = db_session.query(LabWork).filter(LabWork.id == work_id).one()
    assert row.is_deleted is True


@pytest.mark.integration
def test_tc_work_058_timezone_preserved(client, teacher_user, auth_headers, work_payload):
    """TC-WORK-058: дедлайн с +03:00 сохраняется как тот же момент времени (PostgreSQL)."""
    payload = {
        **work_payload,
        "deadline": "2026-12-01T23:59:59+03:00",
    }
    created = client.post(
        "/api/v1/works",
        json=payload,
        headers=auth_headers(teacher_user),
    )
    assert created.status_code == 201, created.text
    work_id = created.json()["id"]
    details = client.get(
        "/api/v1/works/%s" % work_id,
        headers=auth_headers(teacher_user),
    )
    assert details.status_code == 200
    returned = datetime.fromisoformat(details.json()["deadline"].replace("Z", "+00:00"))
    expected = datetime.fromisoformat("2026-12-01T23:59:59+03:00").astimezone(timezone.utc)
    assert returned.astimezone(timezone.utc) == expected
