"""Точка входа Telegram-бота LabFlow (aiogram3, WBS 4.5.2).

Запуск:
  python -m app.bot.main
"""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers import router
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("labflow.bot")


async def run_bot() -> None:
    token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
    if not token or token.startswith("1234567890"):
        logger.error(
            "TELEGRAM_BOT_TOKEN не задан или оставлен placeholder из .env.example. "
            "Укажите токен от @BotFather и перезапустите сервис telegram-bot."
        )
        # Не падаем сразу — даём оператору время поправить env в docker
        await asyncio.sleep(30)
        raise SystemExit(1)

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    me = await bot.get_me()
    logger.info(
        "Bot started as @%s (expected username from env: %s)",
        me.username,
        settings.TELEGRAM_BOT_USERNAME,
    )
    await dispatcher.start_polling(bot)


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
