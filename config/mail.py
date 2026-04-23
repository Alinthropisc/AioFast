from typing import Literal

from pydantic import Field, SecretStr

from core.configuration import BaseConfiguration


class Mail(BaseConfiguration):
    __config_name__ = "mail"
    __env_prefix__ = "MAIL_"

    # Без префикса MAIL_ в именах - добавится автоматически!
    mailer: Literal["smtp", "ses", "mailgun", "log"] = Field(default="smtp")
    scheme: str = Field(default="smtp")
    host: str = Field(default="localhost")
    port: int = Field(default=587)
    username: str = Field(default="")
    password: SecretStr = Field(default=SecretStr(""))
    encryption: Literal["tls", "ssl", "none"] = Field(default="tls")
    from_address: str = Field(default="noreply@example.com")
    from_name: str = Field(default="Application")
