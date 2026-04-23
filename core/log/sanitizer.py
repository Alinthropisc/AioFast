from __future__ import annotations

import re


class Sanitizer:
    """
    Mask sensitive data in log messages.

    Prevents passwords, tokens, credit cards, emails
    from leaking into log files.

    Usage:
        sanitizer = Sanitizer()
        sanitizer.add_keys("password", "secret", "token", "api_key")
        sanitizer.add_pattern(r'\b\\d{4}[- ]?\\d{4}[- ]?\\d{4}[- ]?\\d{4}\b', "****-****-****-****")

        clean = sanitizer.clean("password=qwerty123&token=abc")
        # → "password=******&token=******"
    """

    # Default keys to mask
    DEFAULT_KEYS: set[str] = {
        "password",
        "passwd",
        "pwd",
        "secret",
        "secret_key",
        "token",
        "access_token",
        "refresh_token",
        "api_token",
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "session",
        "credit_card",
        "card_number",
        "cvv",
        "ssn",
        "private_key",
    }

    MASK = "******"

    def __init__(self, *, use_defaults: bool = True) -> None:
        self._keys: set[str] = set()
        self._patterns: list[tuple[re.Pattern, str]] = []
        self._enabled: bool = True

        if use_defaults:
            self._keys.update(self.DEFAULT_KEYS)
            self._add_default_patterns()

    def add_keys(self, *keys: str) -> Sanitizer:
        """Add key names to mask (case-insensitive matching)."""
        self._keys.update(k.lower() for k in keys)
        return self

    def add_pattern(self, pattern: str, replacement: str = "******") -> Sanitizer:
        """Add regex pattern to mask."""
        self._patterns.append((re.compile(pattern), replacement))
        return self

    def enable(self) -> Sanitizer:
        self._enabled = True
        return self

    def disable(self) -> Sanitizer:
        self._enabled = False
        return self

    def clean(self, message: str) -> str:
        """Sanitize a log message string."""
        if not self._enabled:
            return message
        result = message

        # 1. Apply regex patterns FIRST (Bearer, credit cards, etc.)
        for pattern, replacement in self._patterns:
            result = pattern.sub(replacement, result)
        # 2. Then mask key=value pairs
        #    Skip keys already handled by patterns above
        skip_keys = {"authorization"}  # handled by Bearer pattern

        for key in self._keys:
            if key in skip_keys:
                continue
            result = re.sub(
                rf'({re.escape(key)})\s*[=:]\s*["\']?(\S+?)["\']?(?=[\s&,;}})\]]|$)',
                rf"\1={self.MASK}",
                result,
                flags=re.IGNORECASE,
            )
        return result

    def clean_dict(self, data: dict, *, depth: int = 5) -> dict:
        """Recursively mask values in a dict."""
        if depth <= 0 or not self._enabled:
            return data

        cleaned = {}
        for key, value in data.items():
            if key.lower() in self._keys:
                cleaned[key] = self.MASK
            elif isinstance(value, dict):
                cleaned[key] = self.clean_dict(value, depth=depth - 1)
            elif isinstance(value, list):
                cleaned[key] = [self.clean_dict(v, depth=depth - 1) if isinstance(v, dict) else v for v in value]
            elif isinstance(value, str):
                cleaned[key] = self.clean(value)
            else:
                cleaned[key] = value
        return cleaned

    def patcher(self, record: dict) -> None:
        """Loguru patcher — auto-sanitize all messages."""
        record["message"] = self.clean(record["message"])

    def _add_default_patterns(self) -> None:
        # Credit card numbers
        self._patterns.append((re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"), "****-****-****-****"))
        # Authorization header with Bearer (полная замена)
        self._patterns.append((re.compile(r"(Authorization\s*[=:]\s*)(Bearer\s+)\S+", re.IGNORECASE), r"\1\2******"))
        # Email partial masking
        self._patterns.append(
            (re.compile(r"\b([a-zA-Z0-9._%+-])([a-zA-Z0-9._%+-]*)@" r"([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b"), r"\1***@\3")
        )
