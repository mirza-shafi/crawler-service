"""V1 API Package"""
from fastapi import APIRouter
from .endpoints import crawler, ingestion

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(crawler.router, tags=["crawler"])
api_router.include_router(ingestion.router, tags=["ingestion"])
