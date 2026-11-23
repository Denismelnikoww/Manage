"""Шаблоны сообщений бота (Спецификация Telegram §3)."""

from __future__ import annotations

import html


def escape(value: str | None) -> str:
    """Экранирование пользовательских данных для parse_mode=HTML."""
    return html.escape(value or "", quote=False)


def truncate_comment(text: str | None, limit: int = 1000) -> str:
    raw = text or ""
    if len(raw) <= limit:
        return raw
    return raw[:limit] + "… (полный текст доступен в LabFlow)"


def msg_start_without_token() -> str:
    return (
        "👋 Здравствуйте! Это бот уведомлений сервиса <b>LabFlow</b>. "
        "Для привязки аккаунта перейдите по персональной ссылке из раздела "
        "«Настройки профиля» на сайте."
    )


def msg_invalid_token() -> str:
    return (
        "⛔ Ссылка привязки недействительна или устарела. "
        "Пожалуйста, сгенерируйте новую ссылку в личном кабинете LabFlow."
    )


def msg_link_success(
    full_name: str,
    *,
    is_teacher: bool,
    group_name: str | None = None,
) -> str:
    if is_teacher:
        role_label = "Преподаватель"
    else:
        role_label = "Студент (группа %s)" % escape(group_name or "—")
    return (
        "✅ <b>Telegram успешно подключён к LabFlow!</b>\n\n"
        "👤 Пользователь: {full_name}\n"
        "🎓 Роль: {role_label}\n\n"
        "Теперь вы будете оперативно получать уведомления о проверках "
        "и сдачах лабораторных работ."
    ).format(full_name=escape(full_name), role_label=role_label)


def msg_new_submission(
    *,
    student_name: str,
    group_name: str,
    work_number: int,
    work_title: str,
    file_name: str,
    submitted_at: str,
    is_resubmission: bool,
) -> str:
    header = (
        "🔄 <b>Повторная сдача работы после доработки!</b>"
        if is_resubmission
        else "📥 <b>Новая сдача работы!</b>"
    )
    file_label = "Новый файл" if is_resubmission else "Файл"
    return (
        "{header}\n\n"
        "👨‍🎓 <b>Студент:</b> {student_name} ({group_name})\n"
        "📘 <b>Работа:</b> ЛР №{work_number} «{work_title}»\n"
        "📎 <b>{file_label}:</b> <code>{file_name}</code>\n"
        "🕒 <b>Дата сдачи:</b> {submitted_at}"
    ).format(
        header=header,
        student_name=escape(student_name),
        group_name=escape(group_name),
        work_number=work_number,
        work_title=escape(work_title),
        file_label=file_label,
        file_name=escape(file_name),
        submitted_at=escape(submitted_at),
    )


def msg_status_accepted(
    *,
    work_number: int,
    work_title: str,
    teacher_name: str,
    comment_text: str | None = None,
) -> str:
    body = (
        "🎉 <b>Поздравляем! Ваша работа принята.</b>\n\n"
        "📘 <b>Работа:</b> ЛР №{work_number} «{work_title}»\n"
        "👨‍🏫 <b>Проверил:</b> {teacher_name}\n"
        "📌 <b>Статус:</b> ✅ Принята"
    ).format(
        work_number=work_number,
        work_title=escape(work_title),
        teacher_name=escape(teacher_name),
    )
    if comment_text:
        body += (
            "\n\n💬 <b>Комментарий преподавателя:</b>\n"
            "<blockquote>%s</blockquote>" % escape(truncate_comment(comment_text))
        )
    return body


def msg_status_rework(
    *,
    work_number: int,
    work_title: str,
    teacher_name: str,
    comment_text: str,
) -> str:
    return (
        "📋 <b>Изменение статуса лабораторной работы</b>\n\n"
        "📘 <b>Работа:</b> ЛР №{work_number} «{work_title}»\n"
        "👨‍🏫 <b>Проверил:</b> {teacher_name}\n"
        "📌 <b>Новый статус:</b> ⚠️ На доработке\n\n"
        "💬 <b>Замечания преподавателя:</b>\n"
        "<blockquote>{comment}</blockquote>\n\n"
        "Исправьте замечания и загрузите обновлённый отчёт в личном кабинете LabFlow."
    ).format(
        work_number=work_number,
        work_title=escape(work_title),
        teacher_name=escape(teacher_name),
        comment=escape(truncate_comment(comment_text)),
    )


def msg_new_comment(
    *,
    work_number: int,
    work_title: str,
    teacher_name: str,
    status_label: str,
    comment_text: str,
) -> str:
    return (
        "💬 <b>Новый комментарий преподавателя</b>\n\n"
        "📘 <b>Работа:</b> ЛР №{work_number} «{work_title}»\n"
        "👨‍🏫 <b>Автор:</b> {teacher_name}\n"
        "📌 <b>Текущий статус:</b> {status_label}\n\n"
        "<b>Текст сообщения:</b>\n"
        "<blockquote>{comment}</blockquote>"
    ).format(
        work_number=work_number,
        work_title=escape(work_title),
        teacher_name=escape(teacher_name),
        status_label=escape(status_label),
        comment=escape(truncate_comment(comment_text)),
    )
