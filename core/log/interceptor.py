from __future__ import annotations

import logging
import sys

from loguru import logger as _loguru


class LoguruInterceptor(logging.Handler):
    """
    Intercept stdlib logging → route to loguru.

    All third-party libs (uvicorn, sqlalchemy, httpx, etc.)
    will go through our LogManager channels.

    Usage:
        LoguruInterceptor.setup()
        # Now logging.getLogger("uvicorn").info("...") → loguru
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _loguru.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = sys._getframe(6), 6

        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        _loguru.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    @classmethod
    def setup(cls, level: int = logging.DEBUG, modules: list[str] | None = None) -> None:
        """
        Install interceptor globally or for specific modules.

        Args:
            level: minimum level to intercept
            modules: list of logger names to intercept (None = root)
        """
        handler = cls()

        if modules:
            for name in modules:
                stdlib_logger = logging.getLogger(name)
                stdlib_logger.handlers.clear()
                stdlib_logger.addHandler(handler)
                stdlib_logger.setLevel(level)
                stdlib_logger.propagate = False
        else:
            logging.root.handlers.clear()
            logging.root.addHandler(handler)
            logging.root.setLevel(level)

    @classmethod
    def setup_common(cls) -> None:
        cls.setup(
            modules=[
                "uvicorn",
                "uvicorn.access",
                "uvicorn.error",
                "litestar",
                "sqlalchemy",
                "sqlalchemy.engine",
                "httpx",
                "httpcore",
                "asyncio",
                "watchfiles",
            ]
        )
