from typing import Annotated, Any, List

from pydantic import AnyUrl, BeforeValidator

from core.configuration import BaseConfiguration


def parse_cors(v: Any) -> list[str] | str:
    """Parse CORS origins from string or list"""
    if isinstance(v, str):
        if v.startswith("["):
            # JSON array string
            import json

            return json.loads(v)
        # Comma-separated string
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list):
        return v
    raise ValueError(f"Invalid CORS value: {v}")


class Cors(BaseConfiguration):
    __config_name__ = "cors"
    __env_prefix__ = "CORS_"

    origins: Annotated[list[AnyUrl] | list[str], BeforeValidator(parse_cors)] = []

    allow_credentials: bool = True
    allow_methods: list[str] = ["*"]
    allow_headers: list[str] = ["*"]
