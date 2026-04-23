from __future__ import annotations

import functools
import inspect
from typing import TYPE_CHECKING, Any

from .errors import ValidationError
from .validator import Validator

if TYPE_CHECKING:
    from collections.abc import Callable

    from .dto import DTO


def validated(
    rules: dict[str, str | list[Any]] | None = None,
    *,
    dto_class: type[DTO] | None = None,
    arg_name: str = "data",
    error_status: int = 422,
) -> Callable:
    """
    Decorator to validate input data before calling handler/method.

    Two modes:
      1. Rules-based (Laravel-style)
      2. DTO-based (pydantic)

    Usage with rules:
        @validated(rules={
            "name": "required|string|min_length:2",
            "email": "required|email",
        })
        async def create_user(data: dict):
            # data is validated and clean
            ...

    Usage with DTO:
        @validated(dto_class=CreateUserDTO)
        async def create_user(data: CreateUserDTO):
            # data is a validated DTO instance
            ...

    On validation error → returns error response dict (422).
    """

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                raw = kwargs.get(arg_name)
                if raw is None and args:
                    # Try to find data in positional args
                    sig = inspect.signature(func)
                    params = list(sig.parameters.keys())
                    if arg_name in params:
                        idx = params.index(arg_name)
                        # Account for 'self'
                        if idx < len(args):
                            raw = args[idx]

                if raw is None:
                    raw = {}

                try:
                    if dto_class is not None:
                        validated_data = dto_class.create(raw if isinstance(raw, dict) else {})
                    elif rules is not None:
                        data_dict = raw if isinstance(raw, dict) else {}
                        validated_data = Validator(data_dict, rules).validate()
                    else:
                        validated_data = raw
                    kwargs[arg_name] = validated_data
                    return await func(*args, **kwargs)

                except ValidationError as e:
                    return e.to_response(error_status)

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                raw = kwargs.get(arg_name, {})
                try:
                    if dto_class is not None:
                        validated_data = dto_class.create(raw if isinstance(raw, dict) else {})
                    elif rules is not None:
                        data_dict = raw if isinstance(raw, dict) else {}
                        validated_data = Validator(data_dict, rules).validate()
                    else:
                        validated_data = raw
                    kwargs[arg_name] = validated_data
                    return func(*args, **kwargs)

                except ValidationError as e:
                    return e.to_response(error_status)

            return sync_wrapper

    return decorator


def validate_input(rules: dict[str, str | list[Any]], *, messages: dict[str, str] | None = None) -> Callable:
    """
    Simple decorator — validates kwargs matching rule keys.

    @validate_input({"name": "required|string", "email": "required|email"})
    async def handler(name: str, email: str):
        ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Build data dict from kwargs
            data = {k: kwargs.get(k) for k in rules}
            try:
                Validator(data, rules, messages=messages).validate()
            except ValidationError as e:
                return e.to_response()
            return await func(*args, **kwargs)

        return wrapper

    return decorator
