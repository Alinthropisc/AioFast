from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import struct
import time

logger = logging.getLogger(__name__)


class TOTP:
    """
    Time-based One-Time Password (RFC 6238).

    Usage:
        totp = TOTP()

        # Setup:
        secret = totp.generate_secret()
        uri = totp.provisioning_uri(secret, "user@app.com", "MyApp")
        # → Generate QR code from uri

        # Verify:
        is_valid = totp.verify(secret, "123456")

        # With drift (allow ±1 time step):
        is_valid = totp.verify(secret, "123456", drift=1)
    """

    def __init__(self, digits: int = 6, period: int = 30, algorithm: str = "sha1") -> None:
        self.digits = digits
        self.period = period
        self.algorithm = algorithm

    def generate_secret(self, length: int = 32) -> str:
        """Generate random base32 secret."""
        random_bytes = secrets.token_bytes(length)
        return base64.b32encode(random_bytes).decode("utf-8").rstrip("=")

    def generate_code(self, secret: str, timestamp: int | None = None) -> str:
        """Generate TOTP code for current time."""
        if timestamp is None:
            timestamp = int(time.time())
        counter = timestamp // self.period
        secret_bytes = base64.b32decode(secret.upper() + "=" * (-len(secret) % 8))
        # HOTP
        counter_bytes = struct.pack(">Q", counter)
        hash_name = self.algorithm
        mac = hmac.new(secret_bytes, counter_bytes, hash_name)
        digest = mac.digest()
        # Dynamic truncation
        offset = digest[-1] & 0x0F
        code_int = struct.unpack(">I", digest[offset : offset + 4])[0]
        code_int &= 0x7FFFFFFF
        code_int %= 10**self.digits

        return str(code_int).zfill(self.digits)

    def verify(self, secret: str, code: str, drift: int = 1, timestamp: int | None = None) -> bool:
        """Verify TOTP code with optional drift."""
        if timestamp is None:
            timestamp = int(time.time())

        for offset in range(-drift, drift + 1):
            t = timestamp + (offset * self.period)
            expected = self.generate_code(secret, t)
            if hmac.compare_digest(expected, code):
                return True
        return False

    def provisioning_uri(self, secret: str, account: str, issuer: str) -> str:
        """Generate otpauth:// URI for QR code."""
        import urllib.parse

        params = {
            "secret": secret,
            "issuer": issuer,
            "algorithm": self.algorithm.upper(),
            "digits": str(self.digits),
            "period": str(self.period),
        }
        label = urllib.parse.quote(f"{issuer}:{account}")
        query = urllib.parse.urlencode(params)
        return f"otpauth://totp/{label}?{query}"


class BackupCodes:
    """
    Backup codes for MFA recovery.

    Usage:
        backup = BackupCodes()

        # Generate:
        codes = backup.generate(count=10)
        # ["abc123de", "fg456hij", ...]

        # Store hashed:
        hashed = backup.hash_codes(codes)

        # Verify (consume):
        is_valid = backup.verify("abc123de", hashed)
        # Returns True and removes from list
    """

    def __init__(self, code_length: int = 8) -> None:
        self.code_length = code_length

    def generate(self, count: int = 10) -> list[str]:
        """Generate backup codes."""
        return [secrets.token_hex(self.code_length // 2) for _ in range(count)]

    def hash_codes(self, codes: list[str]) -> list[str]:
        """Hash backup codes for storage."""
        return [hashlib.sha256(c.encode()).hexdigest() for c in codes]

    def verify(self, code: str, hashed_codes: list[str]) -> tuple:
        """
        Verify a backup code. Returns (is_valid, remaining_hashes).
        Consumes the code if valid.
        """
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        if code_hash in hashed_codes:
            remaining = [h for h in hashed_codes if h != code_hash]
            return True, remaining
        return False, hashed_codes

    def remaining_count(self, hashed_codes: list[str]) -> int:
        return len(hashed_codes)


class MFAManager:
    """
    Multi-factor authentication manager.

    Usage:
        mfa = MFAManager()

        # Enable MFA for user:
        secret = mfa.setup("user_123")
        uri = mfa.get_provisioning_uri("user_123", "alice@app.com", "MyApp")
        backup_codes = mfa.get_backup_codes("user_123")

        # Confirm setup (user enters code from authenticator):
        if mfa.confirm_setup("user_123", "123456"):
            # MFA enabled!

        # Verify during login:
        if mfa.verify("user_123", "654321"):
            # MFA passed!

        # Use backup code:
        if mfa.verify_backup("user_123", "abc123de"):
            # Backup code used
    """

    def __init__(self) -> None:
        self._totp = TOTP()
        self._backup = BackupCodes()
        self._secrets: dict = {}  # user_id → {secret, backup_hashes, confirmed}

    def setup(self, user_id: str) -> str:
        """Start MFA setup — returns secret."""
        secret = self._totp.generate_secret()
        backup_codes = self._backup.generate()
        backup_hashes = self._backup.hash_codes(backup_codes)

        self._secrets[user_id] = {
            "secret": secret,
            "backup_hashes": backup_hashes,
            "backup_codes_plain": backup_codes,  # Show once
            "confirmed": False,
        }

        return secret

    def get_provisioning_uri(self, user_id: str, account: str, issuer: str) -> str | None:
        data = self._secrets.get(user_id)
        if data is None:
            return None
        return self._totp.provisioning_uri(data["secret"], account, issuer)

    def get_backup_codes(self, user_id: str) -> list[str] | None:
        """Get plain backup codes (only available during setup)."""
        data = self._secrets.get(user_id)
        if data:
            codes = data.pop("backup_codes_plain", None)
            return codes
        return None

    def confirm_setup(self, user_id: str, code: str) -> bool:
        """Confirm MFA setup by verifying a code."""
        data = self._secrets.get(user_id)
        if data is None:
            return False
        if self._totp.verify(data["secret"], code):
            data["confirmed"] = True
            return True
        return False

    def is_enabled(self, user_id: str) -> bool:
        data = self._secrets.get(user_id)
        return data is not None and data.get("confirmed", False)

    def verify(self, user_id: str, code: str) -> bool:
        """Verify TOTP code."""
        data = self._secrets.get(user_id)
        if data is None or not data.get("confirmed"):
            return False
        return self._totp.verify(data["secret"], code)

    def verify_backup(self, user_id: str, code: str) -> bool:
        """Verify and consume a backup code."""
        data = self._secrets.get(user_id)
        if data is None:
            return False

        valid, remaining = self._backup.verify(code, data["backup_hashes"])
        if valid:
            data["backup_hashes"] = remaining
        return valid

    def disable(self, user_id: str) -> bool:
        """Disable MFA for user."""
        return self._secrets.pop(user_id, None) is not None

    def regenerate_backup(self, user_id: str) -> list[str] | None:
        """Regenerate backup codes."""
        data = self._secrets.get(user_id)
        if data is None:
            return None
        codes = self._backup.generate()
        data["backup_hashes"] = self._backup.hash_codes(codes)
        return codes
