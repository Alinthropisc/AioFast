from __future__ import annotations

from core.registry import HealthCheck, HealthStatus, SystemHealth


class TestHealthCheck:
    def test_healthy(self):
        h = HealthCheck(name="test", status=HealthStatus.HEALTHY)
        d = h.to_dict()
        assert d["status"] == "healthy"
        assert d["name"] == "test"

    def test_with_details(self):
        h = HealthCheck(
            name="db",
            status=HealthStatus.HEALTHY,
            latency_ms=5.123,
            details={"connections": 10},
        )
        d = h.to_dict()
        assert d["latency_ms"] == 5.12
        assert d["details"]["connections"] == 10

    def test_unhealthy(self):
        h = HealthCheck(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message="Connection refused",
        )
        d = h.to_dict()
        assert d["status"] == "unhealthy"
        assert d["message"] == "Connection refused"


class TestSystemHealth:
    def test_all_healthy(self):
        checks = [
            HealthCheck(name="a", status=HealthStatus.HEALTHY),
            HealthCheck(name="b", status=HealthStatus.HEALTHY),
        ]
        sys = SystemHealth.from_checks(checks, version="1.0")
        assert sys.status == HealthStatus.HEALTHY
        assert sys.version == "1.0"

    def test_one_unhealthy(self):
        checks = [
            HealthCheck(name="a", status=HealthStatus.HEALTHY),
            HealthCheck(name="b", status=HealthStatus.UNHEALTHY),
        ]
        sys = SystemHealth.from_checks(checks)
        assert sys.status == HealthStatus.UNHEALTHY

    def test_one_degraded(self):
        checks = [
            HealthCheck(name="a", status=HealthStatus.HEALTHY),
            HealthCheck(name="b", status=HealthStatus.DEGRADED),
        ]
        sys = SystemHealth.from_checks(checks)
        assert sys.status == HealthStatus.DEGRADED

    def test_empty(self):
        sys = SystemHealth.from_checks([])
        assert sys.status == HealthStatus.UNKNOWN

    def test_to_dict(self):
        checks = [HealthCheck(name="a", status=HealthStatus.HEALTHY)]
        sys = SystemHealth.from_checks(checks, version="2.0")
        d = sys.to_dict()
        assert d["status"] == "healthy"
        assert d["version"] == "2.0"
        assert len(d["checks"]) == 1
