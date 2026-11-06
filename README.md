# LabFlow 🚀

> **Веб-сервис трекинга и сдачи лабораторных работ** для академической группы ВПР42.

Проект разработан в рамках учебного курса. Сервис решает проблему непрозрачности сдачи учебных работ, автоматизирует процесс рецензирования преподавателем, отслеживание 5 детерминированных статусов (`Не начата` → `В работе` → `Сдана` → `На доработке` → `Принята`), хранение отчётов и доставку уведомлений в Telegram.

---

## 👥 Команда проекта

- **Паршин Артём** — Lead Dev / Backend
- **Теплов Андрей** — Backend разработчик
- **Пашковский Виктор** — Frontend разработчик
- **Пашковский Владимир** — Системный аналитик
- **Кулов Дамир** — QA инженер / Тестировщик

---

## 🛠 Технологический стек

- **Backend:** Python 3.11, FastAPI, SQLAlchemy, Pydantic, Alembic
- **Database & Storage:** PostgreSQL 16, MinIO (S3-совместимое объектное хранилище)
- **Frontend:** React 19, TypeScript, Vite
- **Integrations:** Telegram Bot API (aiogram 3)
- **DevOps & CI/CD:** Docker, Docker Compose, GitHub Actions

---

## 🚀 Быстрый старт (Инструкция по локальному запуску)

### 1. Предварительные требования
Убедитесь, что на вашей машине установлены:
- [Git](https://git-scm.com/)
- [Node.js](https://nodejs.org/) (версия 20 LTS или новее)
- [Python](https://www.python.org/) (версия 3.11 или новее)
- [Docker](https://www.docker.com/) и Docker Compose (рекомендуется для запуска инфраструктуры)

---

### 2. Клонирование и настройка окружения

1. Клонируйте репозиторий и перейдите в рабочую ветку `develop`:
   ```bash
   git clone https://github.com/Denismelnikoww/Manage.git
   cd Manage
   git checkout develop
   ```

2. Создайте файл переменных окружения из примера:
   ```bash
   # Linux / macOS
   cp .env.example .env

   # Windows (PowerShell)
   Copy-Item .env.example .env
   ```
   При необходимости отредактируйте параметры подключения в созданном файле `.env`.

---

### 3. Запуск инфраструктуры (БД и MinIO через Docker)

Для быстрого поднятия базы данных PostgreSQL и MinIO выполните:
```bash
docker compose up -d postgres minio
```

---

### 4. Запуск Backend (FastAPI)

1. Перейдите в каталог бэкенда:
   ```bash
   cd backend
   ```
2. Создайте и активируйте виртуальное окружение:
   ```bash
   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Запустите сервер разработки:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   - Swagger интерактивная документация API: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### 5. Запуск Frontend (React + Vite)

1. В отдельном терминале перейдите в папку фронтенда:
   ```bash
   cd frontend
   ```
2. Установите зависимости:
   ```bash
   npm install
   ```
3. Запустите dev-сервер:
   ```bash
   npm run dev
   ```
   - Клиентская часть доступна по адресу: [http://localhost:5173](http://localhost:5173)

---

## 🌿 Регламент разработки (Git-flow)

Разработка в проекте ведётся строго по регламенту Git-flow:
- **`main`** — стабильная релизная ветка.
- **`develop`** — основная ветка интеграции.
- Все доработки выполняются в ветках `feature/<номер_wbs>-<описание>` и вливаются в `develop` через Pull Request с прохождением CI-проверок и ревью.
- Подробные правила ветвления, правила коммитов Conventional Commits и настройки защиты веток описаны в документе:  
  👉 **[Регламент ветвления Git-flow](docs/Git-flow.md)**

---

## 📚 Проектная документация

Все ключевые проектные артефакты находятся в каталоге `docs/`:
- [Use Cases (Спецификация прецедентов)](docs/Use%20Cases.md)
- [User Stories и критерии приёмки](docs/User%20Stories.md)
- [Definition of Done (DoD)](docs/Definition%20of%20Done.md)
- [Роли проектной команды](docs/Роли%20проектной%20команды.md)
