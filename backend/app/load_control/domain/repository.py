"""Repository port for the LoadArea aggregate (Repository Pattern).

The domain depends on this abstraction, not on any storage technology. The
concrete asyncpg/PostgreSQL implementation lives in the infrastructure layer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.load_control.domain.load_area import LoadArea
from app.load_control.domain.value_objects import AreaCode


class LoadAreaNotFound(Exception):
    """Raised when a requested LoadArea does not exist."""


class LoadAreaRepository(ABC):
    @abstractmethod
    async def get(self, area_code: AreaCode) -> LoadArea:
        """Load the aggregate, or raise LoadAreaNotFound."""

    @abstractmethod
    async def save(self, area: LoadArea) -> None:
        """Persist aggregate state (status, session powers) and new adjustments."""

    @abstractmethod
    async def exists(self, area_code: AreaCode) -> bool:
        ...
