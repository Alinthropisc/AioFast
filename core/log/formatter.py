from __future__ import annotations

FORMATS: dict[str, str] = {
    "simple": ("<level>[{level:<7}]</level> {message} {extra[context_str]}"),
    "detailed": (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> <level>[{level:<7}]</level> <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — <level>{message}</level> {extra[context_str]}"
    ),
    "minimal": "{message}",
    "production": ("{time:YYYY-MM-DD HH:mm:ss} [{level}] {name} — {message} {extra[context_str]}"),
    "file": ("{time:YYYY-MM-DD HH:mm:ss.SSS} [{level:<7}] {name}:{function}:{line} — {message} {extra[context_str]}"),
}


def get_format(name: str) -> str:
    """Get format by name or return as-is if custom."""
    return FORMATS.get(name, name)
