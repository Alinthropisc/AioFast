from __future__ import annotations

import base64
import hashlib
import logging
import os
from typing import Any

from sqlalchemy import String, TypeDecorator

logger = logging.getLogger(__name__)


class EncryptedString(TypeDecorator):
    """
    Encrypted column — auto encrypt/decrypt.

    Uses Fernet (AES-128-CBC) from cryptography library.

    Usage:
        class User(BaseModel):
            __tablename__ = "users"
            name: Mapped[str]
            ssn: Mapped[str] = mapped_column(EncryptedString(key="your-secret-key"))
            credit_card: Mapped[Optional[str]] = mapped_column(
                EncryptedString(key_env="ENCRYPTION_KEY"), nullable=True
            )

        # Auto encrypts on write, decrypts on read
        user = User(name="Alice", ssn="123-45-6789")
        session.add(user)  # stored encrypted in DB
        print(user.ssn)    # "123-45-6789" (decrypted in Python)
    """

    impl = String
    cache_ok = True

    def __init__(self, key: str | None = None, key_env: str = "APP_ENCRYPTION_KEY", length: int = 500) -> None:
        self._raw_key = key
        self._key_env = key_env
        super().__init__(length)

    @property
    def _key(self) -> bytes:
        raw = self._raw_key or os.getenv(self._key_env, "")
        if not raw:
            raise ValueError(f"Encryption key not set. Set {self._key_env} env var or pass key= parameter.")
        # Derive 32-byte key from whatever user provides
        return base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())

    def _get_fernet(self):
        try:
            from cryptography.fernet import Fernet
        except ImportError as exc:
            raise ImportError("Install cryptography: pip install cryptography") from exc
        return Fernet(self._key)

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        """Encrypt before storing."""
        if value is None:
            return None
        fernet = self._get_fernet()
        encrypted = fernet.encrypt(str(value).encode())
        return encrypted.decode()

    def process_result_value(self, value: Any, dialect: Any) -> str | None:
        """Decrypt after reading."""
        if value is None:
            return None
        fernet = self._get_fernet()
        try:
            decrypted = fernet.decrypt(value.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error("Decryption failed: %s", e)
            return None


class HashedString(TypeDecorator):
    """
    One-way hashed column (bcrypt/sha256).

    Good for passwords, API keys.

    Usage:
        class User(BaseModel):
            password: Mapped[str] = mapped_column(HashedString())

        user = User(password="secret123")
        # Stored as hash, cannot be reversed
    """

    impl = String
    cache_ok = True

    def __init__(self, algorithm: str = "sha256", length: int = 255) -> None:
        self._algorithm = algorithm
        super().__init__(length)

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        if self._algorithm == "bcrypt":
            try:
                import bcrypt

                return bcrypt.hashpw(value.encode(), bcrypt.gensalt()).decode()
            except ImportError as exc:
                raise ImportError("Install bcrypt: pip install bcrypt") from exc
        # Default: SHA256
        return hashlib.sha256(value.encode()).hexdigest()

    def process_result_value(self, value: Any, dialect: Any) -> str | None:
        # Return raw hash (one-way)
        return value
