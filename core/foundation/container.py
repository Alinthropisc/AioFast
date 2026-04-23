from __future__ import annotations

import contextlib
import inspect
import logging
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    get_type_hints,
)

from ..exceptions import (
    BindingNotFoundException,
    BindingResolutionException,
    CircularDependencyException,
    StrictContainerException,
)
from .binding import Binding, BindingType
from .contextual import ContextualBindingBuilder
from .scoped import ScopedContainer

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")
logger = logging.getLogger(__name__)


class Container:
    def __init__(self, *, strict: bool = False, override: bool = True) -> None:
        self._bindings: dict[Any, Binding] = {}
        self._aliases: dict[str, Any] = {}
        self._tags: dict[str, list[Any]] = {}
        self._swaps: dict[Any, Any] = {}
        self._contextual: dict[Any, dict[Any, Any]] = {}

        self._hooks: dict[str, dict[Any, list[Callable]]] = {
            "bind": {},
            "make": {},
            "resolve": {},
        }
        self._global_resolving_callbacks: list[Callable] = []
        self._global_after_resolving_callbacks: list[Callable] = []
        self._strict = strict
        self._override = override
        self._resolving_stack: list[Any] = []
        self._dishka_container = None
        self._dishka_providers: list = []

    def bind(self, abstract: Any, concrete: Any = None) -> Container:
        concrete = concrete or abstract
        self._register_binding(abstract, concrete, BindingType.TRANSIENT)
        return self

    def singleton(self, abstract: Any, concrete: Any = None) -> Container:
        concrete = concrete or abstract
        self._register_binding(abstract, concrete, BindingType.SINGLETON)
        return self

    def instance(self, abstract: Any, obj: Any) -> Container:
        binding = Binding(abstract=abstract, concrete=type(obj), binding_type=BindingType.INSTANCE, instance=obj)
        self._bindings[abstract] = binding
        self._fire_hook("bind", abstract, obj)
        return self

    def scoped(self, abstract: Any, concrete: Any = None) -> Container:
        concrete = concrete or abstract
        self._register_binding(abstract, concrete, BindingType.SCOPED)
        return self

    def bind_if(self, abstract: Any, concrete: Any = None) -> Container:
        if not self.has(abstract):
            self.bind(abstract, concrete)
        return self

    def singleton_if(self, abstract: Any, concrete: Any = None) -> Container:
        if not self.has(abstract):
            self.singleton(abstract, concrete)
        return self

    def alias(self, abstract: Any, alias_name: str) -> Container:
        self._aliases[alias_name] = abstract
        return self

    def tag(self, abstracts: list[Any], tag_name: str) -> Container:
        if tag_name not in self._tags:
            self._tags[tag_name] = []
        self._tags[tag_name].extend(abstracts)
        return self

    def swap(self, abstract: Any, concrete: Any) -> Container:
        self._swaps[abstract] = concrete
        return self

    def when(self, concrete: Any) -> ContextualBindingBuilder:
        return ContextualBindingBuilder(self, concrete)

    def unbind(self, abstract: Any) -> bool:
        if abstract in self._bindings:
            del self._bindings[abstract]
            return True
        return False

    async def make(self, abstract: Any, *args: Any, **kwargs: Any) -> Any:
        # 1) Swaps
        if abstract in self._swaps:
            return await self._resolve_swap(abstract)
        abstract = self._resolve_alias(abstract)

        if abstract in self._bindings:
            binding = self._bindings[abstract]
            self._fire_hook("make", abstract, binding.concrete)

            if binding.is_shared and binding.is_resolved:
                return binding.instance
            obj = await self._resolve_binding(binding, *args, **kwargs)

            if binding.binding_type == BindingType.SINGLETON:
                binding.instance = obj
            return obj

        if inspect.isclass(abstract):
            logger.debug("Auto-resolving class: %s", abstract)
            return await self.resolve(abstract, *args, **kwargs)

        if self._dishka_container is not None:
            try:
                return await self._dishka_container.get(abstract)
            except Exception:
                pass
        raise BindingNotFoundException(abstract)

    async def make_or(self, abstract: Any, default: Any = None, *args: Any, **kwargs: Any) -> Any:
        try:
            return await self.make(abstract, *args, **kwargs)
        except (BindingNotFoundException, BindingResolutionException):
            if callable(default) and not isinstance(default, type):
                result = default()
                if inspect.isawaitable(result):
                    return await result
                return result
            return default

    async def resolve(self, obj: Any, *args: Any, **kwargs: Any) -> Any:
        if not callable(obj):
            return obj

        if obj in self._resolving_stack:
            chain = [*self._resolving_stack, obj]
            raise CircularDependencyException(chain)
        self._resolving_stack.append(obj)

        try:
            for cb in self._global_resolving_callbacks:
                cb(obj, self)
            resolved = await self._resolve_parameters(obj, *args, **kwargs)
            instance = obj(*resolved["args"], **resolved["kwargs"])

            if inspect.isawaitable(instance):
                instance = await instance
            self._fire_hook("resolve", obj, instance)

            for cb in self._global_after_resolving_callbacks:
                cb(instance, self)
            return instance

        except TypeError as e:
            raise BindingResolutionException(obj, str(e)) from e
        finally:
            self._resolving_stack.pop()

    async def call(self, callback: Callable, *args: Any, **kwargs: Any) -> Any:
        resolved = await self._resolve_parameters(callback, *args, **kwargs)
        result = callback(*resolved["args"], **resolved["kwargs"])

        if inspect.isawaitable(result):
            result = await result
        return result

    async def tagged(self, tag_name: str) -> list[Any]:
        if tag_name not in self._tags:
            return []
        results = []
        for abstract in self._tags[tag_name]:
            results.append(await self.make(abstract))
        return results

    async def factory(self, abstract: Any) -> Callable:
        async def _factory(*args, **kwargs):
            return await self.make(abstract, *args, **kwargs)

        return _factory

    def has(self, abstract: Any) -> bool:
        resolved = self._resolve_alias(abstract) if isinstance(abstract, str) else abstract
        return resolved in self._bindings or resolved in self._swaps

    def bound(self, abstract: Any) -> bool:
        return self.has(abstract)

    def is_shared(self, abstract: Any) -> bool:
        abstract = self._resolve_alias(abstract) if isinstance(abstract, str) else abstract
        if abstract in self._bindings:
            return self._bindings[abstract].is_shared
        return False

    def is_resolved(self, abstract: Any) -> bool:
        abstract = self._resolve_alias(abstract) if isinstance(abstract, str) else abstract
        if abstract in self._bindings:
            return self._bindings[abstract].is_resolved
        return False

    def get_bindings(self) -> dict[Any, Binding]:
        return dict(self._bindings)

    def collect(self, search: str | type) -> dict[Any, Any]:
        results = {}
        if isinstance(search, str):
            for key, binding in self._bindings.items():
                if isinstance(key, str) and self._match_pattern(key, search):
                    results[key] = binding.concrete
        elif inspect.isclass(search):
            for key, binding in self._bindings.items():
                concrete = binding.concrete
                try:
                    if inspect.isclass(concrete) and issubclass(concrete, search):
                        results[key] = concrete
                    elif isinstance(binding.instance, search):
                        results[key] = binding.instance
                except TypeError:
                    pass
        return results

    def on_bind(self, key: Any, callback: Callable) -> Container:
        return self._register_hook("bind", key, callback)

    def on_make(self, key: Any, callback: Callable) -> Container:
        return self._register_hook("make", key, callback)

    def on_resolve(self, key: Any, callback: Callable) -> Container:
        return self._register_hook("resolve", key, callback)

    def resolving(self, callback: Callable) -> Container:
        self._global_resolving_callbacks.append(callback)
        return self

    def after_resolving(self, callback: Callable) -> Container:
        self._global_after_resolving_callbacks.append(callback)
        return self

    def create_scope(self, name: str = "request") -> ScopedContainer:
        return ScopedContainer(self, name)

    def flush(self) -> Container:
        self._bindings.clear()
        self._aliases.clear()
        self._tags.clear()
        self._swaps.clear()
        self._contextual.clear()

        for action_hooks in self._hooks.values():
            action_hooks.clear()
        self._global_resolving_callbacks.clear()
        self._global_after_resolving_callbacks.clear()
        return self

    def forget_instances(self) -> Container:
        for binding in self._bindings.values():
            binding.reset()
        return self

    def forget_swap(self, abstract: Any) -> Container:
        self._swaps.pop(abstract, None)
        return self

    def forget_swaps(self) -> Container:
        self._swaps.clear()
        return self

    async def close(self) -> None:
        """Shutdown — cleanup resources. Skip self to avoid recursion."""
        for binding in self._bindings.values():
            if binding.instance is not None and binding.instance is not self:
                await self._try_close(binding.instance)

        if self._dishka_container is not None:
            await self._dishka_container.close()
            self._dishka_container = None

    def register_dishka_provider(self, provider: Any) -> Container:
        self._dishka_providers.append(provider)
        return self

    async def build_dishka(self) -> None:
        if not self._dishka_providers:
            return
        try:
            from dishka import make_async_container

            self._dishka_container = make_async_container(*self._dishka_providers)
            logger.info("Dishka container built with %d providers", len(self._dishka_providers))
        except ImportError:
            logger.warning("Dishka is not installed — bridge not available")

    def _register_binding(self, abstract: Any, concrete: Any, binding_type: BindingType) -> None:
        if inspect.ismodule(concrete):
            raise StrictContainerException(f"Cannot bind module '{concrete}' into the container")
        if self._strict and abstract in self._bindings:
            raise StrictContainerException(f"Cannot override '{abstract}' in strict mode")
        if self._override or abstract not in self._bindings:
            binding = Binding(abstract=abstract, concrete=concrete, binding_type=binding_type)
            self._bindings[abstract] = binding
            self._fire_hook("bind", abstract, concrete)
            logger.debug("Bound %s -> %s [%s]", abstract, concrete, binding_type.name)

    def _resolve_alias(self, abstract: Any) -> Any:
        """Resolve alias chain. Detect circular aliases."""
        if not isinstance(abstract, str):
            return abstract

        seen: set[str] = set()
        current = abstract
        while isinstance(current, str) and current in self._aliases:
            if current in seen:
                raise BindingResolutionException(abstract, "Circular alias detected")
            seen.add(current)
            current = self._aliases[current]
        return current

    async def _resolve_swap(self, abstract: Any) -> Any:
        swap = self._swaps[abstract]
        if callable(swap) and not isinstance(swap, type):
            result = swap(self)
            if inspect.isawaitable(result):
                return await result
            return result
        return swap

    async def _resolve_binding(self, binding: Binding, *args: Any, **kwargs: Any) -> Any:
        concrete = binding.concrete

        if binding.is_resolved:
            return binding.instance

        if callable(concrete) and not inspect.isclass(concrete):
            result = concrete(self)
            if inspect.isawaitable(result):
                result = await result
            return result

        if inspect.isclass(concrete):
            return await self.resolve(concrete, *args, **kwargs)
        return concrete

    async def _resolve_parameters(self, obj: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        target = obj.__init__ if inspect.isclass(obj) else obj

        try:
            sig = inspect.signature(target)
        except (ValueError, TypeError):
            return {"args": list(args), "kwargs": kwargs}

        try:
            hints = get_type_hints(target)
        except Exception:
            hints = {}
        resolved_args: list[Any] = []
        resolved_kwargs: dict[str, Any] = dict(kwargs)
        positional = list(args)
        SKIP_TYPES = (str, int, float, bool, bytes, dict, list, tuple, set, type(None))

        for name, param in sig.parameters.items():
            if name == "self":
                if positional:
                    resolved_args.append(positional.pop(0))
                continue

            if name in resolved_kwargs:
                continue

            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                resolved_args.extend(positional)
                positional.clear()
                continue
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                continue
            annotation = hints.get(name, param.annotation)

            if positional:
                resolved_args.append(positional.pop(0))
                continue

            if annotation not in (inspect.Parameter.empty, None):
                if annotation in SKIP_TYPES or (isinstance(annotation, type) and annotation in SKIP_TYPES):
                    if param.default != inspect.Parameter.empty:
                        resolved_args.append(param.default)
                    continue

                if isinstance(annotation, str):
                    if param.default != inspect.Parameter.empty:
                        resolved_args.append(param.default)
                        continue
                    raise BindingResolutionException(
                        obj,
                        f"Cannot resolve parameter '{name}' with string annotation '{annotation}' — use actual types",
                    )

                if obj in self._contextual and annotation in self._contextual[obj]:
                    ctx_concrete = self._contextual[obj][annotation]
                    if inspect.isclass(ctx_concrete):
                        resolved_args.append(await self.resolve(ctx_concrete))
                    else:
                        resolved_args.append(ctx_concrete)
                    continue

                try:
                    resolved_args.append(await self.make(annotation))
                    continue
                except (BindingNotFoundException, BindingResolutionException):
                    pass

            if param.default != inspect.Parameter.empty:
                resolved_args.append(param.default)
                continue
            raise BindingResolutionException(obj, f"Cannot resolve parameter '{name}' (annotation={annotation!r})")

        return {"args": resolved_args, "kwargs": resolved_kwargs}

    def _fire_hook(self, action: str, key: Any, obj: Any) -> None:
        hooks = self._hooks.get(action, {})
        for hook_key, callbacks in hooks.items():
            should_fire = (
                hook_key == key
                or (inspect.isclass(obj) and hook_key is obj)
                or (not inspect.isclass(obj) and hook_key is type(obj))
            )
            if should_fire:
                for callback in callbacks:
                    callback(obj, self)

    def _register_hook(self, action: str, key: Any, callback: Callable) -> Container:
        if key not in self._hooks[action]:
            self._hooks[action][key] = []
        self._hooks[action][key].append(callback)
        return self

    @staticmethod
    def _match_pattern(key: str, pattern: str) -> bool:
        if "*" not in pattern:
            return key == pattern
        parts = pattern.split("*", 1)
        if pattern.startswith("*"):
            return key.endswith(parts[1])
        if pattern.endswith("*"):
            return key.startswith(parts[0])
        return key.startswith(parts[0]) and key.endswith(parts[1])

    @staticmethod
    async def _try_close(obj: Any) -> None:
        """Try to close an object gracefully."""
        if hasattr(obj, "aclose"):
            with contextlib.suppress(Exception):
                await obj.aclose()
        elif hasattr(obj, "close"):
            try:
                result = obj.close()
                if inspect.isawaitable(result):
                    await result
            except Exception:
                pass

    def __contains__(self, abstract: Any) -> bool:
        return self.has(abstract)

    def __repr__(self) -> str:
        b = len(self._bindings)
        a = len(self._aliases)
        s = sum(1 for x in self._bindings.values() if x.is_resolved)
        return f"<Container bindings={b} aliases={a} resolved={s}>"
