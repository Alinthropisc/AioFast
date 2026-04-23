from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .errors import ErrorBag, ValidationError
from .sanitizer import Sanitizer
from .validator import Validator

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..foundation import Application


class FormRequest:
    """
    Laravel-like FormRequest — combines authorize + sanitize + validate.

    Single object that handles the entire request validation lifecycle.

    Usage:
        class CreateUserRequest(FormRequest):
            def authorize(self) -> bool:
                # Check if user can perform this action
                return self.user is not None

            def rules(self) -> dict:
                return {
                    "name": "required|string|min_length:2|max_length:50",
                    "email": "required|email",
                    "password": "required|min_length:8|confirmed",
                    "role": "in:user,admin",
                }

            def messages(self) -> dict:
                return {
                    "name.required": "Please enter your name",
                    "email.email": "Please enter a valid email",
                    "password.min_length": "Password must be at least 8 characters",
                }

            def sanitizers(self) -> dict:
                return {
                    "name": ["trim", "title_case"],
                    "email": ["trim", "lowercase"],
                }

            def after_validation(self, data: dict) -> dict:
                # Transform data after validation
                data["name_slug"] = data["name"].lower().replace(" ", "-")
                return data

        # Usage in controller:
        async def store(self, data: dict):
            request = CreateUserRequest(data, app=self.app)
            clean = await request.validate()
            # clean is sanitized + validated + transformed
    """

    def __init__(self, data: dict[str, Any], *, app: Application | None = None, user: Any = None) -> None:
        self._data = data
        self.app = app
        self.user = user
        self._errors: ErrorBag | None = None
        self._validated: dict[str, Any] | None = None

    # ── Override these ────────────────────────────────────

    def authorize(self) -> bool:
        """Override to check authorization. Return False → 403."""
        return True

    def rules(self) -> dict[str, str | list[Any]]:
        """Override to define validation rules."""
        return {}

    def messages(self) -> dict[str, str]:
        """Override to define custom error messages."""
        return {}

    def sanitizers(self) -> dict[str, list[str | Callable]]:
        """Override to define field sanitizers (applied before validation)."""
        return {}

    def after_validation(self, data: dict[str, Any]) -> dict[str, Any]:
        """Override to transform data after validation."""
        return data

    # ── Validation ────────────────────────────────────────

    async def validate(self) -> dict[str, Any]:
        """
        Full lifecycle: authorize → sanitize → validate → transform.

        Raises ValidationError on failure.
        Raises PermissionError if not authorized.
        """
        # 1. Authorize
        if not self.authorize():
            raise PermissionError("Unauthorized")
        # 2. Sanitize
        sanitizer_defs = self.sanitizers()

        if sanitizer_defs:
            sanitizer = Sanitizer(sanitizer_defs)
            self._data = sanitizer.sanitize(self._data)
        # 3. Validate (sync rules)
        rule_defs = self.rules()

        if rule_defs:
            v = Validator(self._data, rule_defs, messages=self.messages())
            clean = v.validate()  # raises ValidationError
        else:
            clean = dict(self._data)
        # 4. Async rules
        async_errors = await self._run_async_rules(clean)

        if async_errors.has_errors:
            raise async_errors.to_exception()
        # 5. After validation transform
        clean = self.after_validation(clean)
        self._validated = clean
        return clean

    async def validate_or_error(self) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """
        Validate without raising. Returns (data, None) or (None, error_response).

        Usage:
            data, error = await request.validate_or_error()
            if error:
                return error
        """
        try:
            data = await self.validate()
            return data, None
        except ValidationError as e:
            return None, e.to_response()
        except PermissionError:
            return None, {
                "success": False,
                "message": "Forbidden",
                "status": 403,
            }

    async def _run_async_rules(self, data: dict[str, Any]) -> ErrorBag:
        """Run async rules from rules() definition."""
        from .async_rules import AsyncRule

        bag = ErrorBag()
        for field, rules_def in self.rules().items():
            if isinstance(rules_def, str):
                continue
            if not isinstance(rules_def, list):
                continue

            value = data.get(field)
            for r in rules_def:
                if isinstance(r, AsyncRule):
                    if self.app:
                        r.set_app(self.app)
                    if not await r.passes_async(field, value):
                        bag.add(field, r.get_message(field, value))
        return bag

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    @property
    def validated_data(self) -> dict[str, Any] | None:
        return self._validated

    def __repr__(self) -> str:
        fields = len(self.rules())
        return f"<{self.__class__.__name__} fields={fields}>"
