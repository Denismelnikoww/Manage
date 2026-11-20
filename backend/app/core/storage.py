"""Сервис объектного хранилища MinIO (WBS 4.4.2).

Инкапсулирует создание бакета, загрузку/удаление объектов и генерацию
pre-signed GET-ссылок. Клиент для подписи ссылок инициализируется внешним
endpoint'ом (MINIO_PUBLIC_ENDPOINT), иначе MinIO вернёт SignatureDoesNotMatch.
"""

import logging
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlparse

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = (".pdf", ".docx", ".zip")

ALLOWED_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".zip": "application/zip",
}

# Разрешённые символы в ключе объекта: только ASCII-буквы, цифры, точка, дефис, подчёркивание
# (оригинальное имя сохраняется в БД в reports.file_name)
_UNSAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_EXT_RE = re.compile(r"[^A-Za-z0-9]+")


def sanitize_filename(filename: str) -> str:
    """Очищает имя файла для использования в ключе MinIO.

    Оставляет только ASCII-символы (буквы, цифры, '.', '_', '-'), защищает
    от path traversal. Кириллица и спецсимволы заменяются, расширение
    сохраняется. Оригинальное имя хранится в БД (reports.file_name).
    """
    name = (filename or "").replace("\\", "/").split("/")[-1]
    name = name.replace("\x00", "")

    stem, extension = name, ""
    if "." in name:
        stem, raw_ext = name.rsplit(".", 1)
        cleaned_ext = _EXT_RE.sub("", raw_ext.lower())[:10]
        if cleaned_ext:
            extension = "." + cleaned_ext

    stem = _UNSAFE_FILENAME_RE.sub("_", stem).strip("._-")
    if not stem:
        stem = "report"

    return (stem[:110] + extension)[:120]


def get_extension(filename: str) -> str:
    """Возвращает расширение в нижнем регистре (включая точку) или ''."""
    name = (filename or "").lower()
    dot = name.rfind(".")
    return name[dot:] if dot != -1 else ""


def build_object_key(lab_work_id: int, student_id: int, filename: str) -> str:
    """Формирует ключ объекта по контракту:
    submissions/{lab_work_id}/{student_id}/{utc_timestamp}_{short_uuid}_{filename}
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short_uuid = uuid.uuid4().hex[:8]
    safe_name = sanitize_filename(filename)
    return f"submissions/{lab_work_id}/{student_id}/{timestamp}_{short_uuid}_{safe_name}"


def _parse_endpoint(endpoint: str) -> tuple[str, bool]:
    """Разбирает endpoint вида http(s)://host:port -> (host:port, secure)."""
    raw = (endpoint or "").strip()
    if "://" not in raw:
        return raw, settings.MINIO_USE_SSL
    parsed = urlparse(raw)
    secure = parsed.scheme == "https"
    host = parsed.netloc or parsed.path
    return host, secure


class MinioStorageService:
    """Тонкая обёртка над minio-py для нужд модуля отчётов."""

    def __init__(
        self,
        endpoint: str | None = None,
        public_endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        secure: bool | None = None,
    ) -> None:
        self.bucket = bucket or settings.MINIO_BUCKET_REPORTS
        internal_host = endpoint or settings.MINIO_ENDPOINT
        self._secure = settings.MINIO_USE_SSL if secure is None else secure

        self._client = Minio(
            internal_host,
            access_key=access_key or settings.MINIO_ROOT_USER,
            secret_key=secret_key or settings.MINIO_ROOT_PASSWORD,
            secure=self._secure,
            region="us-east-1",
        )

        public_host, public_secure = _parse_endpoint(
            public_endpoint or settings.MINIO_PUBLIC_ENDPOINT
        )
        self._public_client = Minio(
            public_host,
            access_key=access_key or settings.MINIO_ROOT_USER,
            secret_key=secret_key or settings.MINIO_ROOT_PASSWORD,
            secure=public_secure,
            region="us-east-1",
        )

    # --- инфраструктура ---

    def ensure_bucket(self) -> None:
        """Создаёт бакет, если его нет. Политика доступа — приватная (по умолчанию).

        Делает несколько попыток: при старте контейнера MinIO может быть ещё
        не готов принимать запросы.
        """
        last_error: Exception | None = None
        for attempt in range(1, 6):
            try:
                if not self._client.bucket_exists(self.bucket):
                    self._client.make_bucket(self.bucket)
                    logger.info("MinIO: создан приватный бакет %s", self.bucket)
                return
            except Exception as error:  # noqa: BLE001 - retry на старте
                last_error = error
                logger.warning(
                    "MinIO: попытка %s/5 создать/проверить бакет не удалась: %s",
                    attempt,
                    error,
                )
                time.sleep(2)
        if last_error is not None:
            raise last_error

    def is_available(self) -> bool:
        try:
            return self._client.bucket_exists(self.bucket)
        except Exception:  # noqa: BLE001 - healthcheck не должен падать
            return False

    # --- объекты ---

    def put_object(self, key: str, stream, length: int, content_type: str) -> None:
        """Загружает объект в бакет. stream должен поддерживать read()."""
        self._client.put_object(
            self.bucket,
            key,
            stream,
            length=length,
            content_type=content_type,
        )

    def remove_object(self, key: str) -> None:
        """Удаляет объект (используется для компенсации при сбое БД)."""
        try:
            self._client.remove_object(self.bucket, key)
        except S3Error:
            logger.exception("MinIO: не удалось удалить объект %s", key)

    def presigned_get_url(
        self,
        key: str,
        file_name: str,
        content_type: str,
        expires_seconds: int | None = None,
    ) -> str:
        """Генерирует pre-signed GET URL с принудительным скачиванием файла."""
        ttl = expires_seconds or settings.PRESIGNED_URL_TTL_SECONDS
        encoded_name = quote(file_name, safe="")
        disposition = "attachment; filename*=UTF-8''%s" % encoded_name
        return self._public_client.presigned_get_object(
            self.bucket,
            key,
            expires=timedelta(seconds=ttl),
            response_headers={
                "response-content-disposition": disposition,
                "response-content-type": content_type or "application/octet-stream",
            },
        )


_storage: MinioStorageService | None = None


def get_storage() -> MinioStorageService:
    """Возвращает singleton-сервис хранилища."""
    global _storage
    if _storage is None:
        _storage = MinioStorageService()
    return _storage


def set_storage(service: MinioStorageService | None) -> None:
    """Подменяет singleton (используется в тестах)."""
    global _storage
    _storage = service
