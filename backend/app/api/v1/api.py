from fastapi import APIRouter
from app.api.v1.endpoints import auth, submissions, works

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth (4.1.2)"])
api_router.include_router(works.router, prefix="/works", tags=["Works & Deadlines (CRUD)"])
api_router.include_router(
    submissions.router,
    prefix="/submissions",
    tags=["Submissions / Reports (4.4.3)"],
)