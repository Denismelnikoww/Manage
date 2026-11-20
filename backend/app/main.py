import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.core.seed import seed_roles_on_startup
from app.core.storage import get_storage
from app.api.v1.api import api_router
from app.models import (  # noqa: F401  (нужны для Base.metadata)
    Comment,
    LabWork,
    Report,
    Role,
    StudentSubmission,
    User,
)

logger = logging.getLogger(__name__)


def _ensure_storage_bucket() -> None:
    """Создаёт приватный бакет MinIO при старте (WBS 4.4.2).

    Приложение не падает, если хранилище ещё недоступно: модуль отчётов
    вернёт 500 STORAGE_ERROR при попытке загрузки.
    """
    try:
        get_storage().ensure_bucket()
    except Exception:  # noqa: BLE001 - старт не должен зависеть от MinIO
        logger.exception("MinIO недоступен: бакет не проверен")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on application startup
    Base.metadata.create_all(bind=engine)
    seed_roles_on_startup()
    _ensure_storage_bucket()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="LabFlow — REST API для управления лабораторными работами и дедлайнами группы ВПР42",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}