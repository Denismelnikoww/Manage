"""Валидация файлов отчётов (WBS 4.4.3).

Проверки по спецификации 4.4.1/4.4.8:
- допустимые расширения: .pdf, .docx, .zip;
- magic bytes: PDF -> %PDF-, DOCX/ZIP -> PK\x03\x04;
- DOCX обязан содержать [Content_Types].xml и каталог word/;
- пустой файл отклоняется;
- размер не более REPORT_MAX_SIZE_BYTES (20 МБ).
"""

import hashlib
import io
import zipfile

from app.core.config import settings
from app.core.storage import ALLOWED_MIME_TYPES, get_extension

PDF_SIGNATURE = b"%PDF-"
ZIP_SIGNATURE = b"PK\x03\x04"
CHUNK_SIZE = 64 * 1024


class FileValidationError(Exception):
    """Ошибка валидации файла с машиночитаемым кодом по контракту."""

    def __init__(self, code: str, message: str, issue: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.issue = issue


def detect_mime_type(filename: str) -> str:
    return ALLOWED_MIME_TYPES.get(get_extension(filename), "application/octet-stream")


def _check_zip_structure(data: bytes, require_docx: bool) -> None:
    """Проверяет корректность ZIP-архива; для DOCX — наличие OOXML-структуры."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
    except zipfile.BadZipFile:
        raise FileValidationError(
            "INVALID_FILE_TYPE",
            "Допустимы только корректные файлы форматов PDF, DOCX, ZIP",
            issue="Файл не является корректным ZIP-архивом",
        )

    if not names:
        raise FileValidationError(
            "INVALID_FILE_TYPE",
            "Допустимы только корректные файлы форматов PDF, DOCX, ZIP",
            issue="Архив не содержит файлов",
        )
    if require_docx:
        has_content_types = any(name.lower() == "[content_types].xml" for name in names)
        has_word_dir = any(name.lower().startswith("word/") for name in names)
        if not (has_content_types and has_word_dir):
            raise FileValidationError(
                "INVALID_FILE_TYPE",
                "Допустимы только корректные файлы форматов PDF, DOCX, ZIP",
                issue="Файл не является документом DOCX (нет OOXML-структуры)",
            )


def validate_report_file(filename: str, content: bytes) -> str:
    """Проверяет файл по расширению, magic bytes и структуре. Возвращает MIME-тип."""
    size = len(content)
    if size == 0:
        raise FileValidationError(
            "EMPTY_FILE",
            "Файл отчёта не выбран или является пустым",
            issue="Размер файла равен 0 байт",
        )

    if size > settings.REPORT_MAX_SIZE_BYTES:
        raise FileValidationError(
            "FILE_TOO_LARGE",
            "Размер файла не должен превышать 20 МБ",
            issue="Получено байт: %s, лимит: %s" % (size, settings.REPORT_MAX_SIZE_BYTES),
        )

    extension = get_extension(filename)
    if extension not in ALLOWED_MIME_TYPES:
        raise FileValidationError(
            "INVALID_FILE_TYPE",
            "Допустимы только корректные файлы форматов PDF, DOCX, ZIP",
            issue="Недопустимое расширение файла: %s" % (extension or "без расширения"),
        )

    if extension == ".pdf":
        if not content.startswith(PDF_SIGNATURE):
            raise FileValidationError(
                "INVALID_FILE_TYPE",
                "Допустимы только корректные файлы форматов PDF, DOCX, ZIP",
                issue="Несоответствие сигнатуры файла (magic bytes) расширению .pdf",
            )
    else:
        if not content.startswith(ZIP_SIGNATURE):
            raise FileValidationError(
                "INVALID_FILE_TYPE",
                "Допустимы только корректные файлы форматов PDF, DOCX, ZIP",
                issue="Несоответствие сигнатуры файла (magic bytes) расширению %s" % extension,
            )
        _check_zip_structure(content, require_docx=(extension == ".docx"))

    return detect_mime_type(filename)


def stream_sha256(content: bytes) -> str:
    """Считает SHA-256, читая содержимое чанками."""
    digest = hashlib.sha256()
    view = memoryview(content)
    for start in range(0, len(content), CHUNK_SIZE):
        digest.update(view[start:start + CHUNK_SIZE])
    return digest.hexdigest()