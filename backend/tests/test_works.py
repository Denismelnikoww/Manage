"""Дополнительные тесты фильтрации/сортировки работ (вне Must §5.2)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.submission import StudentSubmission
from tests.conftest import GROUP_NAME

pytestmark = pytest.mark.unit


def _create_work(client, headers, order_num: int, title: str, days: int, group: str = GROUP_NAME) -> dict:
    deadline = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    response = client.post(
        "/api/v1/works",
        json={
            "order_num": order_num,
            "title": title,
            "description": "Описание для теста фильтрации и сортировки работ",
            "deadline": deadline,
            "group_name": group,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_list_sort_by_deadline_desc(client, teacher_user, student_user, auth_headers):
    early = _create_work(client, auth_headers(teacher_user), 103, "Сорт desc ранняя ЛР", days=4)
    late = _create_work(client, auth_headers(teacher_user), 104, "Сорт desc поздняя ЛР", days=40)

    response = client.get(
        "/api/v1/works?group_name=%s&sort_by=deadline&sort_desc=true" % GROUP_NAME,
        headers=auth_headers(student_user),
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids.index(late["id"]) < ids.index(early["id"])


def test_list_filter_deadline_to(client, teacher_user, student_user, auth_headers):
    near = _create_work(client, auth_headers(teacher_user), 105, "Дедлайн близко CI", days=2)
    far = _create_work(client, auth_headers(teacher_user), 106, "Дедлайн далеко CI", days=60)
    boundary = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")

    response = client.get(
        "/api/v1/works",
        params={"group_name": GROUP_NAME, "deadline_to": boundary},
        headers=auth_headers(student_user),
    )
    assert response.status_code == 200, response.text
    ids = {item["id"] for item in response.json()["items"]}
    assert near["id"] in ids
    assert far["id"] not in ids


def test_list_filter_overdue_false(client, teacher_user, student_user, auth_headers):
    work = _create_work(client, auth_headers(teacher_user), 107, "Актуальная работа CI", days=5)
    response = client.get(
        "/api/v1/works?group_name=%s&overdue=false" % GROUP_NAME,
        headers=auth_headers(student_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert all(item["is_overdue"] is False for item in data["items"])
    assert any(item["id"] == work["id"] for item in data["items"])


def test_list_item_has_deadline_fields_and_submission(
    client, teacher_user, student_user, auth_headers
):
    work = _create_work(client, auth_headers(teacher_user), 108, "Поля списка CI", days=8)
    response = client.get(
        "/api/v1/works?group_name=%s" % GROUP_NAME,
        headers=auth_headers(student_user),
    )
    assert response.status_code == 200
    item = next(i for i in response.json()["items"] if i["id"] == work["id"])
    assert item["is_overdue"] is False
    assert item["days_until_deadline"] is not None
    assert item["student_submission"] is not None
    assert item["student_submission"]["status"] == "not_started"


def test_list_filter_by_status_student(
    client, db_session, teacher_user, student_user, auth_headers
):
    work = _create_work(client, auth_headers(teacher_user), 109, "Фильтр по статусу CI", days=12)

    sub = (
        db_session.query(StudentSubmission)
        .filter(
            StudentSubmission.lab_work_id == work["id"],
            StudentSubmission.student_id == student_user.id,
        )
        .one()
    )
    sub.status = "in_progress"
    db_session.commit()

    response = client.get(
        "/api/v1/works?group_name=%s&status=in_progress" % GROUP_NAME,
        headers=auth_headers(student_user),
    )
    assert response.status_code == 200
    assert work["id"] in {item["id"] for item in response.json()["items"]}

    response_ns = client.get(
        "/api/v1/works?group_name=%s&status=accepted" % GROUP_NAME,
        headers=auth_headers(student_user),
    )
    assert response_ns.status_code == 200
    assert work["id"] not in {item["id"] for item in response_ns.json()["items"]}


def test_list_filter_invalid_status_rejected(client, student_user, auth_headers):
    response = client.get(
        "/api/v1/works?status=unknown_status",
        headers=auth_headers(student_user),
    )
    assert response.status_code == 422
