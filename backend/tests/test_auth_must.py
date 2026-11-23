"""Must-набор auth/RBAC для PR-гейта (WBS 2.2.2 §5.1)."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token
from tests.conftest import GROUP_NAME, TEST_PASSWORD

pytestmark = pytest.mark.unit


def _b64url_decode(segment: str) -> bytes:
    pad = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + pad)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


@pytest.mark.security
def test_tc_auth_019_successful_login(client, student_user):
    """TC-AUTH-019: успешный вход → 200, bearer, expires_in=86400."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": student_user.email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 86400
    assert data["user"]["email"] == student_user.email
    assert data["user"]["id"] == student_user.id


@pytest.mark.security
def test_tc_auth_020_wrong_password(client, student_user):
    """TC-AUTH-020: неверный пароль → 401 + WWW-Authenticate: Bearer."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": student_user.email, "password": "WrongPass123"},
    )
    assert response.status_code == 401
    assert response.headers.get("www-authenticate", "").lower().startswith("bearer")
    body = response.json()
    assert "access_token" not in body
    assert body["detail"] == "Неверный email или пароль"


@pytest.mark.security
def test_tc_auth_021_unknown_email_same_as_wrong_password(client, student_user):
    """TC-AUTH-021: несуществующий email → тот же 401, что и TC-AUTH-020."""
    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": student_user.email, "password": "WrongPass123"},
    )
    unknown = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "AnyPass123"},
    )
    assert unknown.status_code == 401
    assert unknown.json() == wrong_password.json()
    assert unknown.headers.get("www-authenticate", "").lower().startswith("bearer")


@pytest.mark.security
def test_tc_auth_023_inactive_user(client, inactive_user):
    """TC-AUTH-023: деактивированный пользователь → 403, токен не выдан."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": inactive_user.email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 403
    assert "access_token" not in response.json()
    assert "деактивир" in response.json()["detail"].lower()


@pytest.mark.security
def test_tc_auth_017_secrets_not_in_responses(client, make_user, work_payload, auth_headers):
    """TC-AUTH-017: в ответах нет password / hashed_password / SECRET_KEY."""
    teacher = make_user(email="secrets.teacher@example.com", role="teacher")
    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "fresh.secrets@example.com",
            "password": TEST_PASSWORD,
            "full_name": "Секреты",
            "group_name": GROUP_NAME,
            "role": "student",
        },
    )
    assert register.status_code == 201, register.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "fresh.secrets@example.com", "password": TEST_PASSWORD},
    )
    assert login.status_code == 200
    for blob in (register.text, login.text):
        assert "hashed_password" not in blob
        assert "SECRET_KEY" not in blob
        assert TEST_PASSWORD not in blob
        assert settings.SECRET_KEY not in blob
        assert '"password"' not in blob
    create = client.post(
        "/api/v1/works",
        json=work_payload,
        headers=auth_headers(teacher),
    )
    assert create.status_code == 201
    assert "hashed_password" not in create.text
    assert settings.SECRET_KEY not in create.text


@pytest.mark.security
def test_tc_auth_028_tampered_jwt_payload(client, student_user, work_payload):
    """TC-AUTH-028: подмена payload без переподписи → 401."""
    token, _ = create_access_token(str(student_user.id), {"role": "student"})
    header_b64, payload_b64, signature = token.split(".")
    payload = json.loads(_b64url_decode(payload_b64))
    payload["role"] = "teacher"
    tampered = "%s.%s.%s" % (header_b64, _b64url_encode(json.dumps(payload).encode()), signature)
    response = client.post(
        "/api/v1/works",
        json=work_payload,
        headers={"Authorization": "Bearer %s" % tampered},
    )
    assert response.status_code == 401


@pytest.mark.security
def test_tc_auth_030_expired_token(client, student_user, work_payload):
    """TC-AUTH-030: истёкший токен → 401."""
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(student_user.id),
            "role": "student",
            "iat": now - timedelta(hours=48),
            "exp": now - timedelta(hours=24),
            "type": "access",
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    response = client.post(
        "/api/v1/works",
        json=work_payload,
        headers={"Authorization": "Bearer %s" % token},
    )
    assert response.status_code == 401


@pytest.mark.security
def test_tc_auth_032_no_token_teacher_endpoint(client, work_payload):
    """TC-AUTH-032: без токена к teacher-эндпоинту → 401."""
    response = client.post("/api/v1/works", json=work_payload)
    assert response.status_code == 401


@pytest.mark.security
def test_tc_auth_033_fake_role_header_without_token(client, work_payload):
    """TC-AUTH-033: X-User-Role без токена не аутентифицирует."""
    response = client.post(
        "/api/v1/works",
        json=work_payload,
        headers={"X-User-Role": "teacher"},
    )
    assert response.status_code == 401


@pytest.mark.security
def test_tc_auth_034_student_cannot_create_work(
    client, student_user, auth_headers, work_payload
):
    """TC-AUTH-034 / TC-WORK-002: студент создаёт работу → 403."""
    response = client.post(
        "/api/v1/works",
        json=work_payload,
        headers=auth_headers(student_user),
    )
    assert response.status_code == 403


@pytest.mark.security
def test_tc_auth_035_student_cannot_patch_or_delete(
    client, student_user, teacher_user, auth_headers, work_payload
):
    """TC-AUTH-035 / TC-WORK-040/048: студент PATCH/DELETE → 403."""
    created = client.post(
        "/api/v1/works",
        json=work_payload,
        headers=auth_headers(teacher_user),
    )
    assert created.status_code == 201, created.text
    work_id = created.json()["id"]

    patch = client.patch(
        "/api/v1/works/%s" % work_id,
        json={"title": "Взлом названия работы"},
        headers=auth_headers(student_user),
    )
    assert patch.status_code == 403

    delete = client.delete(
        "/api/v1/works/%s" % work_id,
        headers=auth_headers(student_user),
    )
    assert delete.status_code == 403


@pytest.mark.security
def test_tc_auth_041_jwt_beats_role_header(
    client, student_user, auth_headers, work_payload
):
    """TC-AUTH-041: JWT студента + X-User-Role: teacher → 403."""
    headers = auth_headers(student_user)
    headers["X-User-Role"] = "teacher"
    response = client.post("/api/v1/works", json=work_payload, headers=headers)
    assert response.status_code == 403


@pytest.mark.security
def test_tc_auth_039_me_without_token(client):
    """TC-AUTH-039: /auth/me без токена → 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.security
def test_tc_auth_040_me_with_token(client, student_user, teacher_user, auth_headers):
    """TC-AUTH-040: /auth/me возвращает только текущего пользователя."""
    response = client.get("/api/v1/auth/me", headers=auth_headers(student_user))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == student_user.id
    assert data["email"] == student_user.email
    assert data["id"] != teacher_user.id
