"""Тесты вспомогательных функций хранилища (WBS 4.4.2)."""

from app.core.storage import (
    ALLOWED_EXTENSIONS,
    build_object_key,
    get_extension,
    sanitize_filename,
    _parse_endpoint,
)


def test_allowed_extensions_contract():
    assert ALLOWED_EXTENSIONS == (".pdf", ".docx", ".zip")


def test_get_extension():
    assert get_extension("report.PDF") == ".pdf"
    assert get_extension("archive.tar.zip") == ".zip"
    assert get_extension("no_extension") == ""


def test_sanitize_filename_removes_paths_and_traversal():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("C:\\Users\\student\\report.pdf") == "report.pdf"
    assert "/" not in sanitize_filename("a/b/c.pdf")
    assert ".." not in sanitize_filename("..\\..\\evil.pdf")


def test_sanitize_filename_replaces_unsafe_symbols():
    cleaned = sanitize_filename('Отчёт ЛР №1 (Иванов).pdf')
    assert cleaned.endswith(".pdf")
    assert " " not in cleaned
    assert "(" not in cleaned and ")" not in cleaned
    assert "№" not in cleaned


def test_sanitize_filename_fallback_and_limit():
    assert sanitize_filename("") == "report"
    assert sanitize_filename("///") == "report"
    long_name = "a" * 400 + ".pdf"
    assert len(sanitize_filename(long_name)) <= 120


def test_build_object_key_matches_contract():
    key = build_object_key(12, 45, "Отчёт ЛР1.pdf")
    parts = key.split("/")
    assert parts[0] == "submissions"
    assert parts[1] == "12"
    assert parts[2] == "45"
    file_part = parts[3]
    assert file_part.endswith(".pdf")
    # 20261120T101010Z_abcdef12_name.pdf
    timestamp, short_uuid, _ = file_part.split("_", 2)
    assert len(timestamp) == 16 and timestamp.endswith("Z")
    assert len(short_uuid) == 8


def test_build_object_key_is_unique():
    assert build_object_key(1, 2, "a.pdf") != build_object_key(1, 2, "a.pdf")


def test_parse_endpoint():
    assert _parse_endpoint("http://localhost:9000") == ("localhost:9000", False)
    assert _parse_endpoint("https://s3.example.com") == ("s3.example.com", True)
    host, secure = _parse_endpoint("minio:9000")
    assert host == "minio:9000"
