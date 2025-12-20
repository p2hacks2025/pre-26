"""Shared dependencies for API routes.

Modules importing this file should only declare lightweight dependency
functions (e.g., retrieving services, repositories, or config instances).
Concrete implementations will be wired during app startup.
"""

from typing import Annotated
from fastapi import Depends

# Placeholder dependency example; will be replaced with real wiring later.

def get_dummy_service() -> str:
    return "placeholder"

DummyService = Annotated[str, Depends(get_dummy_service)]

__all__ = ["DummyService", "get_dummy_service"]
