"""v1 API routers and dependencies."""

from fastapi import APIRouter

from . import analyze, suggest

router = APIRouter(prefix="/api")
router.include_router(analyze.router)
router.include_router(suggest.router)

__all__ = ["router"]
