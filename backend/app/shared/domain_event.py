"""Base type for domain events shared across bounded contexts."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class DomainEvent:
    """Immutable record of something business-meaningful that happened.

    `event_id` and `occurred_at` are keyword-only with defaults so concrete
    events can declare their own required positional fields without ordering
    conflicts.
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()), kw_only=True)
    occurred_at: datetime = field(default_factory=utcnow, kw_only=True)

    @property
    def event_type(self) -> str:
        return type(self).__name__
