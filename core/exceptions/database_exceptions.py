from typing import Any

from .base import AioFastException


class ModelNotFoundError(AioFastException):
    def __init__(self, model_class: type, id: Any):
        super().__init__(f"{model_class.__name__} with id={id} not found")
        self.model_class = model_class
        self.id = id
