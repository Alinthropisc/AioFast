from pydantic import Field

from core.configuration import BaseConfiguration


class Logger(BaseConfiguration):
    __config_name__ = "logger"
    __env_prefix__ = "LOG_"

    # Убрал префикс LOG_ из имён полей - он добавится автоматически!
    channel: str = Field(default="stack")
    stack: str = Field(default="single")
    deprecations_channel: str = Field(default="null")
    level: str = Field(default="debug")

    # Optional fields с дефолтами
    rotation: str = Field(default="daily")
    retention: str = Field(default="14 days")
    compression: str = Field(default="gz")

    colorize: bool = Field(default=True)
    enqueue: bool = Field(default=False)
    diagnose: bool = Field(default=True)
    backtrace: bool = Field(default=True)
    serialize: bool = Field(default=False)
    lazy: bool = Field(default=False)
