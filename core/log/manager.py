from __future__ import annotations

from typing import Any

from loguru import logger as _loguru

from .channel import CHANNEL_DRIVERS, Channel
from .context import LogContext, context_patcher
from .formatter import get_format
from .interceptor import LoguruInterceptor
from .profiler import Profiler
from .sampling import RateLimiter, SamplingFilter
from .sanitizer import Sanitizer


class LogManager:
    """
    Config example:
        {
            "default": "stack",
            "channels": {
                "stack": {
                    "driver": "stack",
                    "channels": ["console", "daily"],
                },
                "console": {
                    "driver": "console",
                    "level": "DEBUG",
                },
                "daily": {
                    "driver": "rotating",
                    "path": "storage/logs/app.log",
                    "level": "INFO",
                    "rotation": "00:00",
                    "retention": "30 days",
                },
                "json": {
                    "driver": "json",
                    "path": "storage/logs/app.json",
                    "level": "WARNING",
                },
            }
        }
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or self._default_config()
        self._channels: dict[str, Channel] = {}
        self._active_sinks: dict[str, int] = {}
        self._custom_drivers: dict[str, type[Channel]] = {}
        self._log = _loguru
        self._sanitizer: Sanitizer | None = None
        self._profiler: Profiler | None = None
        self._configured = False

    def configure(self) -> LogManager:
        if self._configured:
            return self
        self._log.remove()
        self._log = self._log.patch(context_patcher)  # ty:ignore[invalid-argument-type]
        default = self._config.get("default", "console")
        self._resolve_channel(default)
        self._configured = True
        return self

    def channel(self, name: str) -> ChannelLogger:
        self._ensure_configured()
        self._resolve_channel(name)
        return ChannelLogger(self, name)

    def stack(self, *channel_names: str) -> ChannelLogger:
        self._ensure_configured()
        for name in channel_names:
            self._resolve_channel(name)
        key = "+".join(sorted(channel_names))
        return ChannelLogger(self, key, list(channel_names))

    def trace(self, msg: str, *args: Any, **kw: Any) -> None:
        self._ensure_configured()
        self._log.opt(depth=1).trace(msg, *args, **kw)

    def debug(self, msg: str, *args: Any, **kw: Any) -> None:
        self._ensure_configured()
        self._log.opt(depth=1).debug(msg, *args, **kw)

    def info(self, msg: str, *args: Any, **kw: Any) -> None:
        self._ensure_configured()
        self._log.opt(depth=1).info(msg, *args, **kw)

    def success(self, msg: str, *args: Any, **kw: Any) -> None:
        self._ensure_configured()
        self._log.opt(depth=1).success(msg, *args, **kw)

    def warning(self, msg: str, *args: Any, **kw: Any) -> None:
        self._ensure_configured()
        self._log.opt(depth=1).warning(msg, *args, **kw)

    def error(self, msg: str, *args: Any, **kw: Any) -> None:
        self._ensure_configured()
        self._log.opt(depth=1).error(msg, *args, **kw)

    def critical(self, msg: str, *args: Any, **kw: Any) -> None:
        self._ensure_configured()
        self._log.opt(depth=1).critical(msg, *args, **kw)

    def exception(self, msg: str, *args: Any, **kw: Any) -> None:
        self._ensure_configured()
        self._log.opt(depth=1, exception=True).error(msg, *args, **kw)

    def with_context(self, **kwargs: Any) -> LogManager:
        LogContext.push(**kwargs)
        return self

    def without_context(self, *keys: str) -> LogManager:
        if keys:
            LogContext.forget(*keys)
        else:
            LogContext.clear()
        return self

    def context(self, **kwargs: Any) -> LogContext:
        return LogContext(**kwargs)

    def extend(self, driver: str, channel_class: type[Channel]) -> LogManager:
        self._custom_drivers[driver] = channel_class
        return self

    def intercept_stdlib(self, modules: list[str] | None = None) -> LogManager:
        """Route stdlib logging through loguru."""
        if modules:
            LoguruInterceptor.setup(modules=modules)
        else:
            LoguruInterceptor.setup_common()
        return self

    @property
    def sanitizer(self) -> Sanitizer:
        """Get or create sanitizer."""
        if self._sanitizer is None:
            self._sanitizer = Sanitizer()
        return self._sanitizer

    def use_sanitizer(self, sanitizer: Sanitizer | None = None) -> LogManager:
        """Enable log sanitization."""
        self._sanitizer = sanitizer or Sanitizer()
        self._log = self._log.patch(self._sanitizer.patcher)  # ty:ignore[invalid-argument-type]
        return self

    @property
    def profiler(self) -> Profiler:
        """Get or create profiler."""
        if self._profiler is None:
            threshold = self._config.get("slow_threshold_ms", 1000.0)
            self._profiler = Profiler(self, slow_threshold_ms=threshold)
        return self._profiler

    def measure(self, label: str, **extra):
        """Shortcut for profiler.measure()."""
        return self.profiler.measure(label, **extra)

    def ameasure(self, label: str, **extra):
        """Shortcut for profiler.ameasure()."""
        return self.profiler.ameasure(label, **extra)

    def with_sampling(self, rate: float, *, levels: list[str] | None = None) -> SamplingFilter:
        """Create and return a sampling filter."""
        return SamplingFilter(rate=rate, levels=levels)

    def with_rate_limit(self, max_count: int = 10, interval: float = 60.0) -> RateLimiter:
        """Create and return a rate limiter."""
        return RateLimiter(max_count=max_count, interval_sec=interval)

    def _resolve_channel(self, name: str) -> None:
        if name in self._channels:
            return
        channels_cfg = self._config.get("channels", {})
        cfg = channels_cfg.get(name)

        if cfg is None:
            if name == "console":
                cfg = {"driver": "console", "level": "DEBUG"}
            else:
                raise ValueError(f"Log channel '{name}' not configured")
        driver = cfg.get("driver", name)

        if driver == "stack":
            sub_names = cfg.get("channels", [])
            for sub in sub_names:
                self._resolve_channel(sub)
            return
        driver_cls = self._custom_drivers.get(driver) or CHANNEL_DRIVERS.get(driver)

        if driver_cls is None:
            raise ValueError(f"Unknown log driver '{driver}'. Available: {list(CHANNEL_DRIVERS.keys())}")

        if "format" in cfg:
            cfg = {**cfg, "format": get_format(cfg["format"])}
        ch = driver_cls(name, cfg)
        ch.setup(self._log)
        self._channels[name] = ch

    def _ensure_configured(self) -> None:
        if not self._configured:
            self.configure()

    def shutdown(self) -> None:
        for ch in self._channels.values():
            ch.teardown(self._log)
        self._channels.clear()
        self._configured = False

    async def aclose(self) -> None:
        self.shutdown()

    @staticmethod
    def _default_config() -> dict[str, Any]:
        return {
            "default": "console",
            "channels": {
                "console": {
                    "driver": "console",
                    "level": "DEBUG",
                },
            },
        }

    @property
    def raw(self) -> Any:
        return self._log

    def __repr__(self) -> str:
        ch_names = list(self._channels.keys())
        return f"<LogManager channels={ch_names}>"


class ChannelLogger:
    def __init__(self, manager: LogManager, key: str, channel_names: list[str] | None = None) -> None:
        self._manager = manager
        self._key = key
        self._names = channel_names or [key]

    def debug(self, msg: str, *a: Any, **kw: Any) -> None:
        self._manager._log.opt(depth=1).debug(msg, *a, **kw)

    def info(self, msg: str, *a: Any, **kw: Any) -> None:
        self._manager._log.opt(depth=1).info(msg, *a, **kw)

    def warning(self, msg: str, *a: Any, **kw: Any) -> None:
        self._manager._log.opt(depth=1).warning(msg, *a, **kw)

    def error(self, msg: str, *a: Any, **kw: Any) -> None:
        self._manager._log.opt(depth=1).error(msg, *a, **kw)

    def critical(self, msg: str, *a: Any, **kw: Any) -> None:
        self._manager._log.opt(depth=1).critical(msg, *a, **kw)

    def exception(self, msg: str, *a: Any, **kw: Any) -> None:
        self._manager._log.opt(depth=1, exception=True).error(msg, *a, **kw)

    def __repr__(self) -> str:
        return f"<ChannelLogger {self._key}>"
