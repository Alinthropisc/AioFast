from __future__ import annotations

import hashlib
import random


class SamplingFilter:
    """
    Sample logs — only pass through N% of messages.

    For high-traffic systems where logging everything
    would be too expensive.

    Usage:
        # Log only 10% of DEBUG messages
        sampler = SamplingFilter(rate=0.1, levels=["DEBUG", "TRACE"])
        log.add(sink, filter=sampler)

        # Deterministic sampling by message content
        sampler = SamplingFilter(rate=0.1, deterministic=True)
    """

    def __init__(self, rate: float = 1.0, *, levels: list[str] | None = None, deterministic: bool = False) -> None:
        """
        Args:
            rate: 0.0 to 1.0, fraction of messages to keep
            levels: only sample these levels (others always pass)
            deterministic: same message always same decision
        """
        self._rate = max(0.0, min(1.0, rate))
        self._levels = {lvl.upper() for lvl in levels} if levels else None
        self._deterministic = deterministic

    def __call__(self, record: dict) -> bool:
        """Filter function for loguru."""
        level = record["level"].name

        # If levels specified, only sample those
        if self._levels and level not in self._levels:
            return True  # always pass non-sampled levels

        if self._rate >= 1.0:
            return True
        if self._rate <= 0.0:
            return False

        if self._deterministic:
            # Hash-based: same message → same decision
            msg_hash = hashlib.md5(record["message"].encode()).hexdigest()
            # Convert first 8 hex chars to float 0..1
            value = int(msg_hash[:8], 16) / 0xFFFFFFFF
            return value < self._rate

        return random.random() < self._rate

    def __repr__(self) -> str:
        return f"<SamplingFilter rate={self._rate:.0%} levels={self._levels} deterministic={self._deterministic}>"


class RateLimiter:
    """
    Rate-limit specific log messages.

    Prevents log flooding — same message at most N times per interval.

    Usage:
        limiter = RateLimiter(max_count=5, interval_sec=60)
        log.add(sink, filter=limiter)
        # Same message logged max 5 times per minute
    """

    def __init__(self, max_count: int = 10, interval_sec: float = 60.0) -> None:
        import time

        self._max = max_count
        self._interval = interval_sec
        self._counts: dict[str, list[float]] = {}
        self._time = time

    def __call__(self, record: dict) -> bool:
        now = self._time.time()
        key = f"{record['level'].name}:{record['message'][:100]}"

        if key not in self._counts:
            self._counts[key] = [now]
            return True

        # Remove old timestamps
        cutoff = now - self._interval
        timestamps = [t for t in self._counts[key] if t > cutoff]

        if len(timestamps) >= self._max:
            # Suppressed — but log a note every Nx
            if len(timestamps) == self._max:
                self._counts[key] = timestamps
            return False

        timestamps.append(now)
        self._counts[key] = timestamps
        return True

    def reset(self) -> None:
        self._counts.clear()

    def __repr__(self) -> str:
        return f"<RateLimiter max={self._max}/{self._interval}s tracked={len(self._counts)}>"
