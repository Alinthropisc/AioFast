from typing import Any


class Log(Facade):
    @classmethod
    def get_facade_accessor(cls) -> Any:
        return "log"
