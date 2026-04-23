from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        result = {
            "name": self.name,
            "status": self.status.value,
            "checked_at": self.checked_at.isoformat(),
        }
        if self.message:
            result["message"] = self.message
        if self.latency_ms is not None:
            result["latency_ms"] = round(self.latency_ms, 2)
        if self.details:
            result["details"] = self.details  # ty:ignore[invalid-assignment]
        return result


@dataclass
class SystemHealth:
    status: HealthStatus
    checks: list[HealthCheck]
    version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "version": self.version,
            "checks": [c.to_dict() for c in self.checks],
        }

    @classmethod
    def from_checks(cls, checks: list[HealthCheck], version: str = "") -> SystemHealth:
        if not checks:
            return cls(status=HealthStatus.UNKNOWN, checks=[], version=version)
        if any(c.status == HealthStatus.UNHEALTHY for c in checks):
            status = HealthStatus.UNHEALTHY
        elif any(c.status == HealthStatus.DEGRADED for c in checks):
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        return cls(status=status, checks=checks, version=version)
