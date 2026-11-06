from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db

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

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

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
        headers={"X-User-Role": "teacher"}
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
        headers={"X-User-Role": "student"}
    )
    assert response.status_code == 403

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
        headers={"X-User-Role": "teacher"}
    )
    assert response.status_code == 422

def test_get_lab_works_list():
    response = client.get("/api/v1/works?group_name=ВПР42")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert data["total"] >= 1

def test_update_lab_work_deadline():
    new_deadline = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    response = client.patch(
        "/api/v1/works/1",
        json={"deadline": new_deadline},
        headers={"X-User-Role": "teacher"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == 1

def test_delete_lab_work_soft_delete():
    response = client.delete(
        "/api/v1/works/1",
        headers={"X-User-Role": "teacher"}
    )
    assert response.status_code == 204
    
    # After soft deletion, getting details should return 404
    get_res = client.get("/api/v1/works/1")
    assert get_res.status_code == 404
