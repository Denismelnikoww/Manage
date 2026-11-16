"""Локальный сид: пользователи + лабораторные работы через API (dev)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "http://localhost:8000/api/v1"
PASSWORD = "Password123!"

TEACHERS = [
    {"email": "ivanova@example.com", "full_name": "Иванова Мария Петровна", "role": "teacher", "group_name": "ВПР42"},
    {"email": "sidorov@example.com", "full_name": "Сидоров Алексей Игоревич", "role": "teacher", "group_name": "ВПР42"},
]

STUDENTS = [
    {"email": "ivanov@example.com", "full_name": "Иванов Иван", "role": "student", "group_name": "ВПР42"},
    {"email": "petrov@example.com", "full_name": "Петров Пётр", "role": "student", "group_name": "ВПР42"},
    {"email": "smirnova@example.com", "full_name": "Смирнова Анна", "role": "student", "group_name": "ВПР42"},
    {"email": "kuznetsov@example.com", "full_name": "Кузнецов Дмитрий", "role": "student", "group_name": "ВПР42"},
    {"email": "volkova@example.com", "full_name": "Волкова Елена", "role": "student", "group_name": "ВПР42"},
    {"email": "novikov@example.com", "full_name": "Новиков Сергей", "role": "student", "group_name": "ВПР42"},
    {"email": "fedorova@example.com", "full_name": "Фёдорова Ольга", "role": "student", "group_name": "ВПР42"},
    {"email": "morozov@example.com", "full_name": "Морозов Никита", "role": "student", "group_name": "ВПР42"},
    {"email": "orlov@example.com", "full_name": "Орлов Артём", "role": "student", "group_name": "ВПР41"},
    {"email": "belova@example.com", "full_name": "Белова Дарья", "role": "student", "group_name": "ВПР41"},
]

WORKS = [
    {"order_num": 1, "title": "ЛР №1: Git и Git-flow", "description": "Настроить репозиторий, ветки feature/develop/main, решить merge conflict.", "days": 5, "group_name": "ВПР42"},
    {"order_num": 2, "title": "ЛР №2: Docker Compose", "description": "Поднять FastAPI + PostgreSQL через docker compose, проверить health.", "days": 8, "group_name": "ВПР42"},
    {"order_num": 3, "title": "ЛР №3: CRUD лабораторных работ", "description": "Реализовать эндпоинты создания, списка, обновления и soft-delete.", "days": 12, "group_name": "ВПР42"},
    {"order_num": 4, "title": "ЛР №4: Фильтрация и сортировка", "description": "Добавить фильтры по статусу и дедлайну, сортировку списка работ.", "days": 15, "group_name": "ВПР42"},
    {"order_num": 5, "title": "ЛР №5: JWT и RBAC", "description": "Защитить эндпоинты JWT, разграничить права student/teacher.", "days": 20, "group_name": "ВПР42"},
    {"order_num": 6, "title": "ЛР №6: Статусы сдачи", "description": "Матрица переходов статусов, история изменений, проверка прав.", "days": 25, "group_name": "ВПР42"},
    {"order_num": 7, "title": "ЛР №7: Отчёты и MinIO", "description": "Загрузка PDF/DOCX/ZIP, pre-signed URL, ограничения по размеру.", "days": 30, "group_name": "ВПР42"},
    {"order_num": 8, "title": "ЛР №8: Telegram-уведомления", "description": "Привязка бота, триггеры смены статуса и новых комментариев.", "days": 35, "group_name": "ВПР42"},
    {"order_num": 1, "title": "ЛР №1: Введение в API", "description": "Первые запросы к REST API, Postman/Swagger.", "days": 6, "group_name": "ВПР41"},
    {"order_num": 2, "title": "ЛР №2: Моделирование БД", "description": "ERD, нормализация, индексы для списка работ.", "days": 14, "group_name": "ВПР41"},
]


def request(method: str, path: str, body: dict | None = None, token: str | None = None):
    data = None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return exc.code, payload


def register_user(user: dict) -> str:
    payload = {**user, "password": PASSWORD}
    code, data = request("POST", "/auth/register", payload)
    if code == 201:
        print(f"  + user {user['email']} ({user['role']})")
        return "created"
    if code == 409:
        print(f"  = user {user['email']} already exists")
        return "exists"
    raise RuntimeError(f"register failed for {user['email']}: {code} {data}")


def login(email: str) -> str:
    code, data = request("POST", "/auth/login", {"email": email, "password": PASSWORD})
    if code != 200:
        raise RuntimeError(f"login failed for {email}: {code} {data}")
    return data["access_token"]


def create_work(token: str, work: dict) -> None:
    deadline = datetime.now(timezone.utc) + timedelta(days=work["days"])
    body = {
        "order_num": work["order_num"],
        "title": work["title"],
        "description": work["description"],
        "deadline": deadline.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "group_name": work["group_name"],
    }
    code, data = request("POST", "/works", body, token=token)
    if code == 201:
        print(f"  + work [{work['group_name']}] #{work['order_num']} {work['title']} (id={data['id']})")
        return
    raise RuntimeError(f"create work failed: {code} {data}")


def main() -> int:
    print("== Users ==")
    for user in TEACHERS + STUDENTS:
        register_user(user)

    print("== Works (as teacher) ==")
    token = login("ivanova@example.com")
    for work in WORKS:
        create_work(token, work)

    print("\nDone.")
    print(f"Password for all accounts: {PASSWORD}")
    print("Teachers: ivanova@example.com, sidorov@example.com")
    print("Students VPR42: ivanov/petrov/smirnova/kuznetsov/volkova/novikov/fedorova/morozov @example.com")
    print("Students VPR41: orlov@example.com, belova@example.com")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
