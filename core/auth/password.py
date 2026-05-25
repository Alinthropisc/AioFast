from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PasswordValidation:
    """Result of password validation."""

    valid: bool
    errors: list[str]

    def __bool__(self) -> bool:
        return self.valid


class PasswordHasher:
    """
    Password hashing — bcrypt by default, supports argon2, scrypt.

    Usage:
        hasher = PasswordHasher()

        hashed = hasher.hash("my_password")
        is_valid = hasher.verify("my_password", hashed)
        needs_rehash = hasher.needs_rehash(hashed)
    """

    def __init__(self, algorithm: str = "bcrypt", rounds: int = 12) -> None:
        self._algorithm = algorithm
        self._rounds = rounds

    def hash(self, password: str) -> str:
        """Hash a password."""
        if self._algorithm == "bcrypt":
            return self._hash_bcrypt(password)
        elif self._algorithm == "argon2":
            return self._hash_argon2(password)
        elif self._algorithm == "scrypt":
            return self._hash_scrypt(password)
        else:
            raise ValueError(f"Unknown algorithm: {self._algorithm}")

    def verify(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        if hashed.startswith("$2b$") or hashed.startswith("$2a$"):
            return self._verify_bcrypt(password, hashed)
        elif hashed.startswith("$argon2"):
            return self._verify_argon2(password, hashed)
        elif hashed.startswith("scrypt:"):
            return self._verify_scrypt(password, hashed)
        return False

    def needs_rehash(self, hashed: str) -> bool:
        """Check if hash needs to be upgraded (algorithm or rounds changed)."""
        if self._algorithm == "bcrypt":
            import importlib.util

            if importlib.util.find_spec("bcrypt") is None:
                return False
            prefix = f"$2b${self._rounds:02d}$"
            return not hashed.startswith(prefix)
        return False

    # ── Bcrypt ────────────────────────────────────────────

    def _hash_bcrypt(self, password: str) -> str:
        try:
            import bcrypt
        except ImportError as exc:
            raise ImportError("Install bcrypt: pip install bcrypt") from exc
        salt = bcrypt.gensalt(rounds=self._rounds)
        return bcrypt.hashpw(password.encode(), salt).decode()

    def _verify_bcrypt(self, password: str, hashed: str) -> bool:
        try:
            import bcrypt

            return bcrypt.checkpw(password.encode(), hashed.encode())
        except Exception:
            return False

    # ── Argon2 ────────────────────────────────────────────

    def _hash_argon2(self, password: str) -> str:
        try:
            from argon2 import PasswordHasher as A2Hasher
        except ImportError as exc:
            raise ImportError("Install argon2: pip install argon2-cffi") from exc
        return A2Hasher().hash(password)

    def _verify_argon2(self, password: str, hashed: str) -> bool:
        try:
            from argon2 import PasswordHasher as A2Hasher

            return A2Hasher().verify(hashed, password)
        except Exception:
            return False

    # ── Scrypt ────────────────────────────────────────────

    def _hash_scrypt(self, password: str) -> str:
        salt = secrets.token_hex(16)
        derived = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1)
        return f"scrypt:{salt}:{derived.hex()}"

    def _verify_scrypt(self, password: str, hashed: str) -> bool:
        try:
            _, salt, hash_hex = hashed.split(":")
            derived = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1)
            return hmac.compare_digest(derived.hex(), hash_hex)
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"<PasswordHasher algorithm={self._algorithm} rounds={self._rounds}>"


class PasswordValidator:
    """
    Password strength validation.

    Usage:
        validator = PasswordValidator(
            min_length=8,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
            require_special=True,
            max_length=128,
            disallow_common=True,
        )

        result = validator.validate("mypassword")
        if not result:
            print(result.errors)
    """

    COMMON_PASSWORDS = {
        "password",
        "123456",
        "12345678",
        "qwerty",
        "abc123",
        "monkey",
        "1234567",
        "letmein",
        "trustno1",
        "dragon",
        "baseball",
        "iloveyou",
        "master",
        "sunshine",
        "ashley",
        "bailey",
        "shadow",
        "123123",
        "654321",
        "superman",
        "qazwsx",
        "michael",
        "football",
        "password1",
        "password123",
    }

    def __init__(
        self,
        min_length: int = 8,
        max_length: int = 128,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = False,
        disallow_common: bool = True,
        custom_rules: list | None = None,
    ) -> None:
        self.min_length = min_length
        self.max_length = max_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special
        self.disallow_common = disallow_common
        self._custom_rules = custom_rules or []

    def validate(self, password: str) -> PasswordValidation:
        errors = []

        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters.")

        if len(password) > self.max_length:
            errors.append(f"Password must be at most {self.max_length} characters.")

        if self.require_uppercase and not re.search(r"[A-Z]", password):
            errors.append("Password must contain an uppercase letter.")

        if self.require_lowercase and not re.search(r"[a-z]", password):
            errors.append("Password must contain a lowercase letter.")

        if self.require_digit and not re.search(r"\d", password):
            errors.append("Password must contain a digit.")

        if self.require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must contain a special character.")

        if self.disallow_common and password.lower() in self.COMMON_PASSWORDS:
            errors.append("This password is too common.")

        for rule in self._custom_rules:
            error = rule(password)
            if error:
                errors.append(error)

        return PasswordValidation(valid=len(errors) == 0, errors=errors)


class PasswordResetManager:
    """
    Password reset token management.

    Usage:
        reset = PasswordResetManager(hasher)

        # Create reset token:
        token = await reset.create("user@example.com")
        # Send token via email...

        # Verify and reset:
        if await reset.verify("user@example.com", token):
            new_hash = hasher.hash("new_password")
            # Update user password...
            await reset.consume("user@example.com", token)
    """

    def __init__(self, ttl: int = 3600) -> None:
        self._ttl = ttl
        self._tokens: dict[str, dict] = {}  # email → {token_hash, expires}

    async def create(self, email: str) -> str:
        """Create a password reset token."""
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        self._tokens[email.lower()] = {
            "hash": token_hash,
            "expires": time.time() + self._ttl,
        }

        logger.info("Password reset token created for: %s", email)
        return token

    async def verify(self, email: str, token: str) -> bool:
        """Verify a reset token."""
        data = self._tokens.get(email.lower())
        if data is None:
            return False

        if time.time() > data["expires"]:
            del self._tokens[email.lower()]
            return False

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return hmac.compare_digest(data["hash"], token_hash)

    async def consume(self, email: str, token: str) -> bool:
        """Verify and consume (delete) the token."""
        if await self.verify(email, token):
            del self._tokens[email.lower()]
            return True
        return False

    async def clear_expired(self) -> int:
        """Remove expired tokens."""
        now = time.time()
        expired = [e for e, d in self._tokens.items() if now > d["expires"]]
        for e in expired:
            del self._tokens[e]
        return len(expired)
