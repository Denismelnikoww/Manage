from fastapi import APIRouter
from app.api.v1.endpoints import works

api_router = APIRouter()
api_router.include_router(works.router, prefix="/works", tags=["Works & Deadlines (CRUD)"])
