"""Хендлеры aiogram3: /start и привязка через backend (WBS 4.5.2).

Вызов POST /telegram/internal/bind реализуется в WBS 4.5.3.
Пока эндпоинт недоступен — бот отвечает шаблоном недействительной ссылки.
"""

from __future__ import annotations

import logging

import httpx
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import Message

from app.bot.templates import msg_invalid_token, msg_link_success, msg_start_without_token
from app.core.config import settings

logger = logging.getLogger(__name__)
router = Router(name="telegram_start")


async def _bind_via_backend(
    token: str,
    chat_id: int,
    telegram_username: str | None,
) -> dict | None:
    """Вызывает внутренний bind API бэкенда. None — токен/сервис недоступен."""
    url = settings.BACKEND_INTERNAL_URL.rstrip("/") + "/api/v1/telegram/internal/bind"
    headers = {"X-Service-Token": settings.TELEGRAM_SERVICE_TOKEN}
    payload = {
        "token": token,
        "chat_id": chat_id,
        "telegram_username": telegram_username,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError:
        logger.exception("Не удалось вызвать backend bind")
        return None

    if response.status_code == 200:
        return response.json()
    logger.warning("bind failed: status=%s body=%s", response.status_code, response.text)
    return None


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject) -> None:
    """Обработка /start и /start <token> по шаблонам спецификации §3.2."""
    deep_link_token = (command.args or "").strip() if command else ""

    if not deep_link_token:
        await message.answer(msg_start_without_token(), parse_mode="HTML")
        return

    username = message.from_user.username if message.from_user else None
    chat_id = message.chat.id
    user_payload = await _bind_via_backend(deep_link_token, chat_id, username)

    if user_payload is None:
        await message.answer(msg_invalid_token(), parse_mode="HTML")
        return

    role = (user_payload.get("role") or {})
    role_code = role.get("code") if isinstance(role, dict) else None
    text = msg_link_success(
        user_payload.get("full_name") or user_payload.get("email") or "Пользователь",
        is_teacher=(role_code == "teacher"),
        group_name=user_payload.get("group_name"),
    )
    await message.answer(text, parse_mode="HTML")
