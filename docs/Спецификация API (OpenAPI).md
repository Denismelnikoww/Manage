# Спецификация REST API (OpenAPI 3.0.3) — Проект LabFlow

**Задача ИСР:** 3.1.3. [Аналитик] Описание API (OpenAPI-спецификация), схема БД, матрица ролей и прав доступа  
**Исполнитель:** Пашковский Владимир (Роль: Аналитик) при участии Паршина А. (Lead Dev) и Мельникова Д. (PM + Auth)  
**Период выполнения:** 4–5 ноября 2026 г.  
**Продукт:** Веб-сервис трекинга лабораторных работ LabFlow  
**Исходный файл контракта:** [openapi.yaml](file:///A:/sadovaya/LabFlow/Проект/openapi.yaml)  
**Статус документа:** Утверждено для генерации клиентских типов (TypeScript) и валидации серверных схем (Pydantic / FastAPI)  

---

## 1. Архитектурный обзор API

Интерфейс прикладного программирования (API) веб-сервиса **LabFlow** спроектирован в соответствии с архитектурным стилем REST и формализован стандартом **OpenAPI Specification v3.0.3**. 

### Базовые характеристики:
- **Базовый URL (Base URL):**
  - Локальная среда разработки: `http://localhost:8000/api/v1`
  - Тестовый контур (Staging): `https://labflow.local/api/v1`
- **Формат обмена данными:** `application/json` (для всех стандартных запросов и ответов) и `multipart/form-data` (для загрузки файлов отчетов).
- **Кодировка:** `UTF-8`.
- **Временные метки:** Стандарт ISO 8601 / RFC 3339 (`YYYY-MM-DDTHH:MM:SSZ`).
- **Идентификаторы сущностей:** UUIDv4 (`123e4567-e89b-12d3-a456-426614174000`).

---

## 2. Схемы безопасности (Security Schemes)

В спецификации объявлены две схемы авторизации запросов:

1. **`BearerAuth` (HTTP Bearer JWT):**
   - Используется для всех пользовательских запросов в веб-интерфейсе.
   - Клиент передает токен в заголовке `Authorization: Bearer <access_token>`.
   - Токен выдается эндпоинтом `/auth/login` и содержит идентификатор пользователя, роль (`student` или `teacher`) и группу.
2. **`ServiceTokenAuth` (API Key):**
   - Используется для защищенного межсервисного взаимодействия бэкенда и фонового Telegram-бота (`aiogram3`).
   - Передается в заголовке `X-Service-Token: <SECRET_BOT_API_KEY>`.
   - Защищает внутренний эндпоинт привязки `/telegram/internal/bind`.

---

## 3. Каталог эндпоинтов и операций

Спецификация включает 14 маршрутов (18 HTTP-операций), сгруппированных по 5 функциональным тегам:

```
├── Auth (Аутентификация и профиль)
│   ├── POST   /auth/register                           # Регистрация студента/преподавателя
│   ├── POST   /auth/login                              # Логин и получение JWT
│   └── GET    /auth/me                                 # Данные текущего пользователя
├── Telegram (Интеграция с ботом)
│   ├── POST   /telegram/link-token                     # Генерация deep-link токена
│   ├── DELETE /telegram/unlink                         # Отвязка Telegram
│   └── POST   /telegram/internal/bind                  # Привязка chat_id ботом (Service Auth)
├── Lab Works (Лабораторные работы и дедлайны)
│   ├── GET    /labs                                    # Список работ с дедлайнами и статусами
│   ├── POST   /labs                                    # Создание работы (Преподаватель)
│   ├── GET    /labs/{lab_id}                           # Детальная карточка работы
│   ├── PUT    /labs/{lab_id}                           # Редактирование работы (Преподаватель)
│   └── DELETE /labs/{lab_id}                           # Мягкое удаление (Преподаватель)
├── Submissions (Сдачи отчетов и статусы)
│   ├── GET    /submissions                             # Ведомость / список сдач
│   ├── GET    /submissions/{submission_id}             # Детальная карточка сдачи
│   ├── PATCH  /submissions/{submission_id}/status      # Смена статуса жизненного цикла
│   ├── POST   /submissions/{submission_id}/upload      # Загрузка отчета в MinIO (Студент)
│   └── GET    /submissions/{submission_id}/download-url# Получение pre-signed URL на скачивание
└── Comments (Рецензирование и замечания)
    ├── GET    /submissions/{submission_id}/comments    # Список комментариев к сдаче
    └── POST   /submissions/{submission_id}/comments    # Добавление замечания (Преподаватель)
```

---

## 4. Описание ключевых контрактов и моделей данных

### 4.1. Аутентификация (`/auth`)

#### `POST /auth/register` — Регистрация пользователя
- **Запрос (`UserRegisterRequest`):**
  ```json
  {
    "email": "student.ivanov@edu.local",
    "password": "SuperSecretPass123!",
    "full_name": "Иванов Иван Иванович",
    "role": "student",
    "group_name": "ВПР42"
  }
  ```
- **Ответ (`201 Created` ➔ `UserResponse`):**
  ```json
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "student.ivanov@edu.local",
    "full_name": "Иванов Иван Иванович",
    "role": "student",
    "group_name": "ВПР42",
    "is_telegram_linked": false,
    "telegram_username": null,
    "created_at": "2026-11-04T10:00:00Z"
  }
  ```

#### `POST /auth/login` — Авторизация
- **Ответ (`200 OK` ➔ `TokenResponse`):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 86400,
    "user": { ... }
  }
  ```

---

### 4.2. Лабораторные работы (`/labs`)

#### `POST /labs` — Создание работы (Преподаватель)
- **Запрос (`LabWorkCreateRequest`):**
  ```json
  {
    "work_number": 1,
    "title": "ЛР №1: Основы Git и командная разработка",
    "description": "Настроить репозиторий, настроить ветвление по Git-flow, решить merge conflict.",
    "deadline": "2026-11-15T23:59:59Z",
    "group_name": "ВПР42"
  }
  ```
- **Бизнес-логика:** Бэкенд создает запись в `lab_works` и автоматически генерирует строки в `student_submissions` со статусом `not_started` для каждого зарегистрированного студента группы ВПР42.

#### `GET /labs` — Список работ
- **Параметры:** `group_name` (строка, по умолчанию `ВПР42`), `status` (опциональный фильтр по статусу).
- **Ответ (`200 OK` ➔ `Array<LabWorkListItemResponse>`):**
  ```json
  [
    {
      "id": "456e4567-e89b-12d3-a456-426614174001",
      "work_number": 1,
      "title": "ЛР №1: Основы Git и командная разработка",
      "deadline": "2026-11-15T23:59:59Z",
      "group_name": "ВПР42",
      "is_overdue": false,
      "days_until_deadline": 11,
      "student_submission": {
        "id": "789e4567-e89b-12d3-a456-426614174002",
        "status": "in_progress",
        "submitted_at": null
      }
    }
  ]
  ```

---

### 4.3. Сдачи и жизненный цикл (`/submissions`)

#### `PATCH /submissions/{id}/status` — Смена статуса
- **Запрос (`SubmissionStatusUpdateRequest`):**
  ```json
  {
    "status": "needs_work",
    "comment_text": "Исправьте раздел 3, добавьте скриншот выполнения git rebase."
  }
  ```
- **Правила валидации:**
  - Переход `not_started ➔ in_progress` доступен **только студенту**.
  - Переходы `submitted ➔ accepted` и `submitted ➔ needs_work` доступны **только преподавателю**.
  - При статусе `needs_work` поле `comment_text` обязательно (длина ≥ 5 символов).

#### `POST /submissions/{id}/upload` — Загрузка файла отчета
- **Формат запроса:** `multipart/form-data`, поле `file`.
- **Ограничения:** Допустимые форматы: `.pdf`, `.docx`, `.zip`. Максимальный размер: **20 МБ** (20 971 520 байт).
- **Результат:** Файл загружается в MinIO по ключу `submissions/{lab_id}/{student_id}/{timestamp}_{filename}`, статус переводится в `submitted`, преподавателю направляется нотификация в Telegram.

#### `GET /submissions/{id}/download-url` — Скачивание отчета
- **Ответ (`200 OK` ➔ `PresignedDownloadResponse`):**
  ```json
  {
    "download_url": "https://minio.local/labflow-submissions/submissions/lab1/student1/timestamp_report.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...&X-Amz-Signature=...",
    "file_name": "LR1_Ivanov_VPR42.pdf",
    "expires_in_seconds": 900
  }
  ```
- **Безопасность:** Временная ссылка (Pre-signed URL) активна ровно 15 минут. Студент может запрашивать ссылку только для своего файла.

---

### 4.4. Комментарии и рецензирование (`/submissions/{id}/comments`)

#### `POST /submissions/{id}/comments` — Добавление замечания (Преподаватель)
- **Запрос (`CommentCreateRequest`):**
  ```json
  {
    "text": "Отчет проверен. Замечания по форматированию библиографии устранены, работа зачтена."
  }
  ```
- **Ответ (`201 Created` ➔ `CommentResponse`):**
  ```json
  {
    "id": "a12e4567-e89b-12d3-a456-426614174003",
    "submission_id": "789e4567-e89b-12d3-a456-426614174002",
    "author_id": "999e4567-e89b-12d3-a456-426614174999",
    "author_name": "Петров Петр (Преподаватель)",
    "author_role": "teacher",
    "text": "Отчет проверен. Замечания по форматированию библиографии устранены, работа зачтена.",
    "created_at": "2026-11-04T14:30:00Z"
  }
  ```

---

## 5. Стандартизированный формат ошибок

В случае возникновения ошибок сервер возвращает тело ответа в соответствии со схемой `ErrorResponse`:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Ошибка валидации входных данных",
  "details": [
    {
      "field": "deadline",
      "issue": "Дедлайн не может быть установлен в прошлом"
    }
  ]
}
```

### Коды ответов HTTP:
- `200 OK` — Успешное выполнение запроса.
- `201 Created` — Ресурс успешно создан (`POST /auth/register`, `POST /labs`, `POST /submissions/{id}/comments`).
- `204 No Content` — Успешное удаление без тела ответа (`DELETE /labs/{id}`, `DELETE /telegram/unlink`).
- `400 Bad Request` — Ошибка валидации параметров, недопустимый переход статуса или некорректный формат файла.
- `401 Unauthorized` — Отсутствует или недействителен Bearer JWT токен.
- `403 Forbidden` — Доступ запрещен (недостаточно прав роли или обращение к чужой сдаче).
- `404 Not Found` — Запрашиваемый ресурс не найден.
- `409 Conflict` — Конфликт состояния (например, повторная сдача уже принятой работы).
- `500 Internal Server Error` — Внутренняя ошибка сервера (сбой хранилища MinIO или СУБД).

---

## 6. Связанные проектные документы
- Полный YAML-файл спецификации: [openapi.yaml](file:///A:/sadovaya/LabFlow/Проект/openapi.yaml)
- Реляционная модель данных: [[Схема базы данных (ERD)|Схема базы данных (ERD)]]
- Матрица прав доступа: [[Матрица ролей и прав доступа|Матрица ролей и прав доступа]]
- Пользовательские сценарии: [[Use Cases|Use Cases]] и [[User Stories|User Stories]]
