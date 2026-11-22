"""Тесты модуля отчётов и комментариев (WBS 4.4.3)."""

import hashlib
import io
import zipfile
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models import LabWork, Role, StudentSubmission, User
from app.services import reports as reports_service

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


class FakeStorage:
    """Подмена MinIO для тестов: объекты хранятся в памяти."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.removed: list[str] = []

    def ensure_bucket(self) -> None:
        pass

    def put_object(self, key: str, stream, length: int, content_type: str) -> None:
        self.objects[key] = stream.read()

    def presigned_get_url(self, key: str, file_name: str, content_type: str, expires_seconds=None) -> str:
        return "http://fake-minio/%s?expires=%s" % (key, expires_seconds)

    def remove_object(self, key: str) -> None:
        self.removed.append(key)
        self.objects.pop(key, None)


storage = FakeStorage()


@pytest.fixture(autouse=True)
def _override_db():
    """Подменяем get_db на тестовую БД и возвращаем предыдущий override после теста."""
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    yield
    if previous is not None:
        app.dependency_overrides[get_db] = previous
    else:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def _patch_storage(monkeypatch):
    monkeypatch.setattr(reports_service, "get_storage", lambda: storage)
    storage.objects.clear()
    storage.removed.clear()
    yield


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
            User(id=1, email="student1@test.local", hashed_password="x",
                 full_name="Студент Первый", group_name="ВПР42", role_id=1, is_active=True),
            User(id=2, email="teacher@test.local", hashed_password="x",
                 full_name="Преподаватель", group_name="ВПР42", role_id=2, is_active=True),
            User(id=3, email="student2@test.local", hashed_password="x",
                 full_name="Студент Второй", group_name="ВПР42", role_id=1, is_active=True),
        ])
        deadline = datetime.now(timezone.utc) + timedelta(days=30)
        for lab_id in range(1, 14):
            db.add(LabWork(id=lab_id, order_num=lab_id, title="ЛР %s" % lab_id,
                           description="Описание работы %s" % lab_id, deadline=deadline,
                           group_name="ВПР42", is_deleted=False))
        db.flush()
        # sub1: успешная загрузка; sub2: чужая сдача; sub3: уже сдана;
        # sub4: docx; sub8: zip; sub9: неверный формат; sub5: пустой; sub6: слишком большой;
        # sub7: без файла
        submissions = [
            (1, 1, 1, "not_started"),
            (2, 2, 3, "in_progress"),
            (3, 3, 1, "submitted"),
            (4, 4, 1, "not_started"),
            (5, 5, 1, "not_started"),
            (6, 6, 1, "not_started"),
            (7, 7, 1, "not_started"),
            (8, 8, 1, "not_started"),
            (9, 9, 1, "not_started"),
        ]
        for sub_id, lab_id, student_id, status in submissions:
            db.add(StudentSubmission(id=sub_id, lab_work_id=lab_id, student_id=student_id,
                                     status=status))
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


def make_pdf(text: str = "test report") -> bytes:
    return b"%PDF-1.4\n" + text.encode("utf-8") + b"\n%%EOF"


def make_docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    return buffer.getvalue()


def make_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("report.txt", "data")
    return buffer.getvalue()


def upload(submission_id: int, filename: str, content: bytes, headers: dict):
    return client.post(
        "/api/v1/submissions/%s/upload" % submission_id,
        files={"file": (filename, content, "application/octet-stream")},
        headers=headers,
    )


def test_upload_pdf_success():
    content = make_pdf()
    response = upload(1, "report.pdf", content, student_headers())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["submission"]["status"] == "submitted"
    assert data["submission"]["file_name"] == "report.pdf"
    assert data["report"]["version_number"] == 1
    assert data["report"]["file_mime_type"] == "application/pdf"
    assert data["report"]["file_size_bytes"] == len(content)
    assert data["report"]["file_sha256"] == hashlib.sha256(content).hexdigest()
    assert len(storage.objects) == 1
    key = next(iter(storage.objects))
    assert key.startswith("submissions/1/1/")


def test_upload_docx_success():
    response = upload(4, "report.docx", make_docx(), student_headers())
    assert response.status_code == 200, response.text
    assert response.json()["report"]["file_mime_type"].endswith("wordprocessingml.document")


def test_upload_zip_success():
    response = upload(8, "sources.zip", make_zip(), student_headers())
    assert response.status_code == 200, response.text


def test_upload_invalid_extension():
    response = upload(9, "malware.exe", b"MZ test", student_headers())
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_FILE_TYPE"


def test_upload_magic_bytes_mismatch():
    response = upload(9, "fake.pdf", b"MZ fake executable", student_headers())
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_FILE_TYPE"


def test_upload_empty_file():
    response = upload(5, "empty.pdf", b"", student_headers())
    assert response.status_code == 400
    assert response.json()["code"] == "EMPTY_FILE"


def test_upload_too_large(monkeypatch):
    monkeypatch.setattr(settings, "REPORT_MAX_SIZE_BYTES", 10)
    response = upload(6, "big.pdf", make_pdf("more than ten bytes"), student_headers())
    assert response.status_code == 400
    assert response.json()["code"] == "FILE_TOO_LARGE"


def test_upload_foreign_submission_forbidden():
    response = upload(2, "report.pdf", make_pdf(), student_headers())
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_upload_teacher_forbidden():
    response = upload(2, "report.pdf", make_pdf(), teacher_headers())
    assert response.status_code == 403


def test_upload_to_submitted_submission_conflict():
    response = upload(3, "report.pdf", make_pdf(), student_headers())
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_SUBMISSION_STATE"


def test_upload_requires_token():
    response = client.post(
        "/api/v1/submissions/1/upload",
        files={"file": ("report.pdf", make_pdf(), "application/pdf")},
    )
    assert response.status_code == 401


def test_download_url_owner():
    upload(1, "report.pdf", make_pdf(), student_headers())
    response = client.get("/api/v1/submissions/1/download-url", headers=student_headers())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["download_url"].startswith("http://fake-minio/")
    assert data["expires_in_seconds"] == 900
    assert data["file_name"] == "report.pdf"
    assert len(data["file_sha256"]) == 64


def test_download_url_teacher_allowed():
    upload(1, "report.pdf", make_pdf(), student_headers())
    response = client.get("/api/v1/submissions/1/download-url", headers=teacher_headers())
    assert response.status_code == 200


def test_download_url_foreign_student_forbidden():
    response = client.get("/api/v1/submissions/2/download-url", headers=student_headers())
    assert response.status_code == 403


def test_download_url_without_file():
    response = client.get("/api/v1/submissions/7/download-url", headers=student_headers())
    assert response.status_code == 400
    assert response.json()["code"] == "FILE_NOT_UPLOADED"


def test_download_url_unknown_submission():
    response = client.get("/api/v1/submissions/999/download-url", headers=student_headers())
    assert response.status_code == 404


def test_reports_history():
    upload(1, "report.pdf", make_pdf(), student_headers())
    response = client.get("/api/v1/submissions/1/reports", headers=student_headers())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["version_number"] == 1


def test_add_comment_teacher_success():
    payload = {"text": "Исправьте выводы в разделе 3"}
    response = client.post("/api/v1/submissions/1/comments", json=payload, headers=teacher_headers())
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["text"] == payload["text"]
    assert data["author_role"] == "teacher"
    assert data["author_name"] == "Преподаватель"


def test_add_comment_student_forbidden():
    response = client.post(
        "/api/v1/submissions/1/comments",
        json={"text": "Студент не может комментировать"},
        headers=student_headers(),
    )
    assert response.status_code == 403


def test_add_comment_too_short():
    response = client.post(
        "/api/v1/submissions/1/comments",
        json={"text": "   ok   "},
        headers=teacher_headers(),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_COMMENT"


def test_list_comments_owner_and_teacher():
    client.post("/api/v1/submissions/1/comments",
                json={"text": "Замечание преподавателя"},
                headers=teacher_headers())

    owner_response = client.get("/api/v1/submissions/1/comments", headers=student_headers())
    assert owner_response.status_code == 200
    assert any(item["text"] == "Замечание преподавателя" for item in owner_response.json())

    teacher_response = client.get("/api/v1/submissions/1/comments", headers=teacher_headers())
    assert teacher_response.status_code == 200

    foreign_response = client.get("/api/v1/submissions/1/comments", headers=second_student_headers())
    assert foreign_response.status_code == 403