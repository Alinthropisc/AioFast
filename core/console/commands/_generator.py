"""Shared base for ``make:*`` generator commands.

Files prefixed with ``_`` are skipped by the command loader, so this module
holds the reusable :class:`GeneratorCommand` without registering a command.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from core.console import Command
from core.console.descriptors import Argument, Option
from core.console.stub_engine import StubEngine


def studly(value: str) -> str:
    """``user_profile`` / ``user-profile`` / ``user profile`` → ``UserProfile``."""
    parts = re.split(r"[_\-\s]+", value.strip())
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


def snake(value: str) -> str:
    """``UserProfile`` → ``user_profile``."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).replace("-", "_").replace(" ", "_").lower()


class GeneratorCommand(Command):
    """Base class for code generators.

    Subclasses set ``stub``, ``target_dir`` (relative to base path), ``suffix``
    (appended to the class name when missing) and ``type_label``.
    """

    stub: str = ""
    target_dir: str = ""
    suffix: str = ""
    type_label: str = "File"

    target = Argument(str, description="Name of the class to generate")
    force = Option("--force", type=bool, description="Overwrite if the file already exists")

    def __init_subclass__(cls, **kwargs) -> None:
        # Command collects descriptors from ``cls.__dict__`` only, so a
        # subclass would otherwise drop the inherited ``target``/``force``.
        super().__init_subclass__(**kwargs)
        seen_args = {a.attr_name for a in cls._arg_defs}
        seen_opts = {o.attr_name for o in cls._opt_defs}
        for base in cls.__mro__[1:]:
            for arg in getattr(base, "_arg_defs", []):
                if arg.attr_name not in seen_args:
                    cls._arg_defs.append(arg)
                    seen_args.add(arg.attr_name)
            for opt in getattr(base, "_opt_defs", []):
                if opt.attr_name not in seen_opts:
                    cls._opt_defs.append(opt)
                    seen_opts.add(opt.attr_name)

    def class_name(self) -> str:
        name = studly(str(self.target))
        if self.suffix and not name.endswith(self.suffix):
            name += self.suffix
        return name

    def output_path(self, base: Path) -> Path:
        return base / self.target_dir / f"{snake(self.class_name())}.py"

    def variables(self) -> dict[str, str]:
        """Extra stub variables. Override to add more."""
        return {}

    async def handle(self, **kwargs: Any) -> int:
        if not self.target:
            self.error("A name is required, e.g. `aiocraft make:... Name`.")
            return self.INVALID

        container = self._app.container if self._app else None
        base = Path(getattr(container, "base_path", None) or os.getcwd())
        path = self.output_path(base)

        if path.exists() and not self.force:
            self.error(f"{self.type_label} already exists: {path}. Use --force to overwrite.")
            return self.FAILURE

        variables = {
            "className": self.class_name(),
            "snakeName": snake(self.class_name()),
            **self.variables(),
        }

        engine = StubEngine()
        if not engine.stub_exists(self.stub):
            self.error(f"Stub '{self.stub}' not found.")
            return self.FAILURE

        engine.generate(self.stub, str(path), variables)
        rel = path.relative_to(base) if path.is_relative_to(base) else path
        self.success(f"{self.type_label} created: {rel}")
        return self.SUCCESS
