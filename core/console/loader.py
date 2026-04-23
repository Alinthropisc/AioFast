from __future__ import annotations

import importlib
import inspect
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from .command import Command

logger = logging.getLogger(__name__)


@dataclass
class LazyCommand:
    """Proxy — stores metadata, loads class on demand."""

    name: str
    module_path: str
    class_name: str
    description: str = ""
    aliases: list[str] = None  # ty:ignore[invalid-assignment]
    hidden: bool = False
    _resolved: type[Command] | None = None

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []

    def resolve(self) -> type[Command]:
        if self._resolved is None:
            module = importlib.import_module(self.module_path)
            self._resolved = getattr(module, self.class_name)
        return self._resolved


class CommandLoader:
    def __init__(self) -> None:
        self._commands: dict[str, type[Command]] = {}
        self._lazy: dict[str, LazyCommand] = {}
        self._aliases: dict[str, str] = {}

    def discover(self, path: str, base_module: str = "") -> None:
        root = Path(path)
        if not root.exists():
            logger.debug("Commands path not found: %s", path)
            return

        parent = str(root.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)

        for file in root.rglob("*.py"):
            if file.name.startswith("_"):
                continue
            relative = file.relative_to(root)
            parts = list(relative.parts)
            parts[-1] = parts[-1][:-3]

            module_path = f"{base_module}.{'.'.join(parts)}" if base_module else ".".join(parts)

            self._load_module(module_path)

    def _load_module(self, module_path: str) -> None:
        try:
            module = importlib.import_module(module_path)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, Command)
                    and obj is not Command
                    and not inspect.isabstract(obj)
                    and getattr(obj, "name", "")
                ):
                    self.register(obj)
        except Exception as e:
            logger.warning("Failed to load commands from %s: %s", module_path, e)

    def register(self, command_cls: type[Command]) -> None:
        self._commands[command_cls.name] = command_cls
        for alias in getattr(command_cls, "aliases", []):
            self._aliases[alias] = command_cls.name
        logger.debug("Loaded command: %s", command_cls.name)

    def register_lazy(self, lazy: LazyCommand) -> None:
        self._lazy[lazy.name] = lazy
        for alias in lazy.aliases:
            self._aliases[alias] = lazy.name
        logger.debug("Lazy registered: %s", lazy.name)

    def get(self, name: str) -> type[Command] | None:
        real_name = self._aliases.get(name, name)

        if real_name in self._commands:
            return self._commands[real_name]

        if real_name in self._lazy:
            cls = self._lazy[real_name].resolve()
            self._commands[real_name] = cls
            del self._lazy[real_name]
            return cls

        return None

    def all(self) -> dict[str, type[Command]]:
        for name, lazy in list(self._lazy.items()):
            self._commands[name] = lazy.resolve()
        self._lazy.clear()
        return dict(self._commands)

    def names(self) -> list[str]:
        return list(self._commands.keys()) + list(self._lazy.keys())

    def grouped(self) -> dict[str, list[type[Command]]]:
        all_cmds = self.all()
        groups: dict[str, list[type[Command]]] = {}
        for name, cmd_cls in all_cmds.items():
            group = name.split(":")[0] if ":" in name else ""
            groups.setdefault(group, []).append(cmd_cls)

        for group in groups:
            groups[group].sort(key=lambda c: c.name)
        return groups

    def has(self, name: str) -> bool:
        real = self._aliases.get(name, name)
        return real in self._commands or real in self._lazy

    def __len__(self) -> int:
        return len(self._commands) + len(self._lazy)
