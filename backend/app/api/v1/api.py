from fastapi import APIRouter
from app.api.v1.endpoints import auth, works

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth (4.1.2)"])
api_router.include_router(works.router, prefix="/works", tags=["Works & Deadlines (CRUD)"])
