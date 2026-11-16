from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.user import Role, User

# Use in-memory SQLite database with StaticPool for isolated testing
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Create test tables
Base.metadata.create_all(bind=test_engine)


def _seed_users():
    """Создаёт роли и по одному пользователю каждой роли для проверки RBAC."""
    db = TestingSessionLocal()
    try:
        if db.query(Role).filter(Role.code == "student").first() is None:
            db.add_all(
                [
                    Role(id=1, code="student", title="Студент"),
                    Role(id=2, code="teacher", title="Преподаватель"),
                ]
            )
            db.flush()
            db.add_all(
                [
                    User(
                        id=1,
                        email="student@test.local",
                        hashed_password="not-used-in-token-tests",
                        full_name="Тестовый Студент",
                        group_name="ВПР42",
                        role_id=1,
                        is_active=True,
                    ),
                    User(
                        id=2,
                        email="teacher@test.local",
                        hashed_password="not-used-in-token-tests",
                        full_name="Тестовый Преподаватель",
                        group_name="ВПР42",
                        role_id=2,
                        is_active=True,
                    ),
                ]
            )
            db.commit()
    finally:
        db.close()


_seed_users()


def auth_headers(role: str) -> dict:
    """Формирует заголовок Authorization с JWT для указанной роли (WBS 4.1.3)."""
    user_id = 1 if role == "student" else 2
    token, _ = create_access_token(subject=str(user_id), extra={"role": role})
    return {"Authorization": "Bearer %s" % token}


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


client = TestClient(app)


def test_create_lab_work_teacher_success():
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    payload = {
        "order_num": 1,
        "title": "ЛР №1: Основы Git и CI/CD",
        "description": "Изучить Git-flow, настроить защиту веток и CI пайплайн.",
        "deadline": future_deadline,
        "group_name": "ВПР42"
    }

    response = client.post(
        "/api/v1/works",
        json=payload,
        headers=auth_headers("teacher")
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["title"] == payload["title"]
    assert data["group_name"] == "ВПР42"
    assert data["is_deleted"] is False


def test_create_lab_work_student_forbidden():
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    payload = {
        "order_num": 2,
        "title": "Попытка создать ЛР студентом",
        "description": "Студент не имеет прав создания",
        "deadline": future_deadline,
        "group_name": "ВПР42"
    }
    response = client.post(
        "/api/v1/works",
        json=payload,
        headers=auth_headers("student")
    )
    assert response.status_code == 403


def test_create_lab_work_without_token_unauthorized():
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    payload = {
        "order_num": 21,
        "title": "Без токена",
        "description": "Запрос без заголовка Authorization",
        "deadline": future_deadline,
        "group_name": "ВПР42"
    }
    response = client.post("/api/v1/works", json=payload)
    assert response.status_code == 401


def test_create_lab_work_with_invalid_token_unauthorized():
    future_deadline = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    payload = {
        "order_num": 22,
        "title": "Битый токен",
        "description": "Невалидный JWT",
        "deadline": future_deadline,
        "group_name": "ВПР42"
    }
    response = client.post(
        "/api/v1/works",
        json=payload,
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert response.status_code == 401


def test_create_lab_work_past_deadline_validation():
    past_deadline = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    payload = {
        "order_num": 3,
        "title": "ЛР с дедлайном в прошлом",
        "description": "Тест валидации",
        "deadline": past_deadline,
        "group_name": "ВПР42"
    }
    response = client.post(
        "/api/v1/works",
        json=payload,
        headers=auth_headers("teacher")
    )
    assert response.status_code == 422


def test_get_lab_works_list():
    response = client.get("/api/v1/works?group_name=ВПР42", headers=auth_headers("student"))
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert data["total"] >= 1


def test_get_lab_works_list_without_token_unauthorized():
    response = client.get("/api/v1/works")
    assert response.status_code == 401


def test_update_lab_work_deadline():
    new_deadline = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    response = client.patch(
        "/api/v1/works/1",
        json={"deadline": new_deadline},
        headers=auth_headers("teacher")
    )
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_update_lab_work_student_forbidden():
    new_deadline = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    response = client.patch(
        "/api/v1/works/1",
        json={"deadline": new_deadline},
        headers=auth_headers("student")
    )
    assert response.status_code == 403


def test_delete_lab_work_student_forbidden():
    response = client.delete("/api/v1/works/1", headers=auth_headers("student"))
    assert response.status_code == 403


def test_delete_lab_work_soft_delete():
    response = client.delete(
        "/api/v1/works/1",
        headers=auth_headers("teacher")
    )
    assert response.status_code == 204

    # After soft deletion, getting details should return 404
    get_res = client.get("/api/v1/works/1", headers=auth_headers("teacher"))
    assert get_res.status_code == 404


# --- WBS 4.2.3: фильтрация и сортировка ---

def _create_work(order_num: int, title: str, days: int, group: str = "ВПР42") -> dict:
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
        headers=auth_headers("teacher"),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_list_sort_by_deadline_asc():
    """Сортировка по дедлайну по возрастанию (ближайшие первыми)."""
    early = _create_work(101, "Сорт ранняя ЛР", days=3)
    late = _create_work(102, "Сорт поздняя ЛР", days=30)

    response = client.get(
        "/api/v1/works?group_name=ВПР42&sort_by=deadline&sort_desc=false",
        headers=auth_headers("student"),
    )
    assert response.status_code == 200
    items = response.json()["items"]
    ids = [item["id"] for item in items]
    assert ids.index(early["id"]) < ids.index(late["id"])


def test_list_sort_by_deadline_desc():
    """Сортировка по дедлайну по убыванию."""
    early = _create_work(103, "Сорт desc ранняя", days=4)
    late = _create_work(104, "Сорт desc поздняя", days=40)

    response = client.get(
        "/api/v1/works?group_name=ВПР42&sort_by=deadline&sort_desc=true",
        headers=auth_headers("student"),
    )
    assert response.status_code == 200
    items = response.json()["items"]
    ids = [item["id"] for item in items]
    assert ids.index(late["id"]) < ids.index(early["id"])


def test_list_filter_deadline_to():
    """Фильтр deadline_to оставляет только работы с дедлайном не позже границы."""
    near = _create_work(105, "Дедлайн близко", days=2)
    far = _create_work(106, "Дедлайн далеко", days=60)
    boundary = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")

    response = client.get(
        "/api/v1/works",
        params={"group_name": "ВПР42", "deadline_to": boundary},
        headers=auth_headers("student"),
    )
    assert response.status_code == 200, response.text
    ids = {item["id"] for item in response.json()["items"]}
    assert near["id"] in ids
    assert far["id"] not in ids


def test_list_filter_overdue_false():
    """overdue=false — только работы с актуальным дедлайном."""
    work = _create_work(107, "Актуальная работа", days=5)
    response = client.get(
        "/api/v1/works?group_name=ВПР42&overdue=false",
        headers=auth_headers("student"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert all(item["is_overdue"] is False for item in data["items"])
    assert any(item["id"] == work["id"] for item in data["items"])


def test_list_item_has_deadline_fields_and_submission():
    """В списке есть is_overdue, days_until_deadline и student_submission."""
    work = _create_work(108, "Поля списка", days=8)
    response = client.get(
        "/api/v1/works?group_name=ВПР42",
        headers=auth_headers("student"),
    )
    assert response.status_code == 200
    item = next(i for i in response.json()["items"] if i["id"] == work["id"])
    assert "is_overdue" in item
    assert item["is_overdue"] is False
    assert item["days_until_deadline"] is not None
    assert item["student_submission"] is not None
    assert item["student_submission"]["status"] == "not_started"


def test_list_filter_by_status_student():
    """Студент фильтрует список по статусу своей сдачи."""
    from app.models.submission import StudentSubmission

    work = _create_work(109, "Фильтр по статусу", days=12)

    db = TestingSessionLocal()
    try:
        sub = (
            db.query(StudentSubmission)
            .filter(
                StudentSubmission.lab_work_id == work["id"],
                StudentSubmission.student_id == 1,
            )
            .one()
        )
        sub.status = "in_progress"
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/v1/works?group_name=ВПР42&status=in_progress",
        headers=auth_headers("student"),
    )
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert work["id"] in ids

    response_ns = client.get(
        "/api/v1/works?group_name=ВПР42&status=accepted",
        headers=auth_headers("student"),
    )
    assert response_ns.status_code == 200
    ids_ns = {item["id"] for item in response_ns.json()["items"]}
    assert work["id"] not in ids_ns


def test_list_filter_invalid_status_rejected():
    response = client.get(
        "/api/v1/works?status=unknown_status",
        headers=auth_headers("student"),
    )
    assert response.status_code == 422