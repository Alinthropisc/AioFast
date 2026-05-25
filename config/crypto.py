
from typing import Literal

from pydantic import Field, SecretStr

from core.configuration import BaseConfiguration, NestedConfig


class BcryptConfig(NestedConfig):
    rounds: int = Field(default=12, ge=4, le=31)


class Argon2Config(NestedConfig):
    memory_cost: int = Field(default=65536, description="Memory in KiB")
    time_cost: int = Field(default=3, description="Iterations")
    parallelism: int = Field(default=4, description="Threads")
    hash_len: int = Field(default=32)
    salt_len: int = Field(default=16)


class ScryptConfig(NestedConfig):
    n: int = Field(default=16384, description="CPU/memory cost")
    r: int = Field(default=8, description="Block size")
    p: int = Field(default=1, description="Parallelism")
    key_length: int = Field(default=64)


class CryptoConfiguration(BaseConfiguration):
    """Configuration for hashing and encryption.

    Env vars: CRYPTO_HASH_DRIVER, CRYPTO_ENCRYPTION_KEY, etc.
    """

    __config_name__ = "crypto"
    __env_prefix__ = "CRYPTO_"

    # Hashing
    hash_driver: Literal["bcrypt", "argon2", "scrypt"] = Field(
        default="bcrypt", description="Default hashing algorithm"
    )
    bcrypt: BcryptConfig = Field(default_factory=BcryptConfig)
    argon2: Argon2Config = Field(default_factory=Argon2Config)
    scrypt: ScryptConfig = Field(default_factory=ScryptConfig)
    # Encryption
    encryption_key: SecretStr = Field(
        default="", description="Fernet encryption key (base64). Generate with: Encryptor.generate_key()"
    )  # ty:ignore[invalid-assignment]
