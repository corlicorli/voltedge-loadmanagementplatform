"""Read-side port (CQRS-lite).

Commands go through the LoadArea aggregate; queries are served from the
warehouse views and never load the aggregate. This keeps the read and write
models decoupled and lets the BI/analytics layer reuse the same projections.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LoadAreaQueries(ABC):
    @abstractmethod
    async def status(self, area_code: str) -> dict[str, Any] | None:
        """LoadAreaStatusView + CurrentLoadView for one area."""

    @abstractmethod
    async def active_sessions(self, area_code: str) -> list[dict[str, Any]]:
        """ActiveChargingSessionsView for one area."""

    @abstractmethod
    async def adjustments(self, area_code: str, limit: int = 100) -> list[dict[str, Any]]:
        """LoadAdjustmentView for one area."""
