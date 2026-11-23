"""Патчи схемы для уже существующих БД (create_all не добавляет колонки)."""

from sqlalchemy import text

from app.core.database import engine


def ensure_telegram_user_columns() -> None:
    """Добавляет users.telegram_username и users.notifications_enabled при отсутствии."""
    statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_username VARCHAR(100)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN DEFAULT TRUE NOT NULL",
    ]
    # SQLite (тесты) до 3.35 не везде поддерживает IF NOT EXISTS — глотаем ошибку дубликата
    with engine.begin() as conn:
        for sql in statements:
            try:
                conn.execute(text(sql))
            except Exception:  # noqa: BLE001
                pass
