"""v1 API routers and dependencies."""

from fastapi import APIRouter

from . import analyze, suggest

router = APIRouter(prefix="/api")
router.include_router(analyze.router, prefix="/v1")
router.include_router(suggest.router, prefix="/v1")

__all__ = ["router"]
