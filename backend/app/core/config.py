import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "LabFlow API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database (PostgreSQL)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://labflow_user:labflow_secret_password@localhost:5432/labflow_db"
    )

    # CORS Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # Academic defaults
    DEFAULT_GROUP_NAME: str = "ВПР42"

    # Security / JWT (WBS 4.1.2)
    SECRET_KEY: str = "super_secret_jwt_key_labflow_2026_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Object storage / MinIO (WBS 4.4.2)
    # Внутренний адрес, по которому backend видит MinIO (docker network)
    MINIO_ENDPOINT: str = "localhost:9000"
    # Внешний адрес, по которому браузер скачивает файл (используется для подписи URL)
    MINIO_PUBLIC_ENDPOINT: str = "http://localhost:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin"
    MINIO_BUCKET_REPORTS: str = "labflow-reports"
    MINIO_USE_SSL: bool = False

    # Ограничения файлов отчётов (WBS 4.4.1/4.4.3)
    REPORT_MAX_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 971 520
    PRESIGNED_URL_TTL_SECONDS: int = 900

    # Telegram / aiogram3 (WBS 4.5.2)
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = "LabFlowBot"
    # Межсервисный секрет для X-Service-Token (бот → backend bind API, 4.5.3)
    TELEGRAM_SERVICE_TOKEN: str = "labflow-telegram-service-token-change-me"
    # URL бэкенда глазами контейнера бота (docker: http://backend:8000)
    BACKEND_INTERNAL_URL: str = "http://localhost:8000"
    # TTL токена deep-link привязки (минуты), ERD / US-10
    TELEGRAM_LINK_TOKEN_TTL_MINUTES: int = 10

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="allow"
    )


settings = Settings()