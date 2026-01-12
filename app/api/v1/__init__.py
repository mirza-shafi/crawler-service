"""V1 API Package"""
from fastapi import APIRouter
from .endpoints import crawler

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(crawler.router, tags=["crawler"])
