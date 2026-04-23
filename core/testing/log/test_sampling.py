from __future__ import annotations

from core.log import RateLimiter, SamplingFilter


class TestSamplingFilter:
    def test_rate_1_passes_all(self):
        f = SamplingFilter(rate=1.0)
        record = {"level": type("L", (), {"name": "INFO"})(), "message": "test"}
        results = [f(record) for _ in range(100)]
        assert all(results)

    def test_rate_0_blocks_all(self):
        f = SamplingFilter(rate=0.0)
        record = {"level": type("L", (), {"name": "INFO"})(), "message": "test"}
        results = [f(record) for _ in range(100)]
        assert not any(results)

    def test_rate_partial(self):
        f = SamplingFilter(rate=0.5)
        record = {"level": type("L", (), {"name": "INFO"})(), "message": "test"}
        results = [f(record) for _ in range(1000)]
        passed = sum(results)
        # Should be roughly 50% (with tolerance)
        assert 300 < passed < 700

    def test_levels_filter(self):
        f = SamplingFilter(rate=0.0, levels=["DEBUG"])
        debug_rec = {"level": type("L", (), {"name": "DEBUG"})(), "message": "x"}
        info_rec = {"level": type("L", (), {"name": "INFO"})(), "message": "x"}
        assert not f(debug_rec)  # sampled out
        assert f(info_rec)  # not sampled, always passes

    def test_deterministic(self):
        f = SamplingFilter(rate=0.5, deterministic=True)
        record = {"level": type("L", (), {"name": "INFO"})(), "message": "same message"}
        results = [f(record) for _ in range(10)]
        # All should be same (deterministic)
        assert len(set(results)) == 1

    def test_repr(self):
        f = SamplingFilter(rate=0.5, levels=["DEBUG"])
        r = repr(f)
        assert "SamplingFilter" in r
        assert "50%" in r


class TestRateLimiter:
    def test_allows_under_limit(self):
        limiter = RateLimiter(max_count=5, interval_sec=60)
        record = {"level": type("L", (), {"name": "INFO"})(), "message": "test"}
        results = [limiter(record) for _ in range(5)]
        assert all(results)

    def test_blocks_over_limit(self):
        limiter = RateLimiter(max_count=3, interval_sec=60)
        record = {"level": type("L", (), {"name": "INFO"})(), "message": "test"}
        results = [limiter(record) for _ in range(10)]
        assert sum(results) == 3

    def test_different_messages_independent(self):
        limiter = RateLimiter(max_count=2, interval_sec=60)
        rec_a = {"level": type("L", (), {"name": "INFO"})(), "message": "aaa"}
        rec_b = {"level": type("L", (), {"name": "INFO"})(), "message": "bbb"}
        assert limiter(rec_a)
        assert limiter(rec_a)
        assert not limiter(rec_a)  # blocked
        assert limiter(rec_b)  # different message, still ok

    def test_reset(self):
        limiter = RateLimiter(max_count=1, interval_sec=60)
        record = {"level": type("L", (), {"name": "INFO"})(), "message": "test"}
        limiter(record)
        assert not limiter(record)
        limiter.reset()
        assert limiter(record)

    def test_repr(self):
        limiter = RateLimiter(max_count=5, interval_sec=30)
        assert "RateLimiter" in repr(limiter)
