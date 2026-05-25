"""``key:generate`` — generate the application encryption key into ``.env``."""

from __future__ import annotations

import base64
import os
import re
import secrets
from pathlib import Path
from typing import Any

from core.console import Command
from core.console.descriptors import Option


class KeyGenerateCommand(Command):
    name = "key:generate"
    description = "Generate and set the APP_KEY in your .env file"

    show = Option("--show", type=bool, description="Display the key instead of writing it")

    async def handle(self, **kwargs: Any) -> int:
        key = "base64:" + base64.b64encode(secrets.token_bytes(32)).decode()

        if self.show:
            self.line(key)
            return self.SUCCESS

        container = self._app.container if self._app else None
        base = Path(getattr(container, "base_path", None) or os.getcwd())
        env_file = base / ".env"

        if not env_file.exists():
            env_file.write_text(f"APP_KEY={key}\n", encoding="utf-8")
            self.success(f"Created {env_file} with a fresh APP_KEY.")
            return self.SUCCESS

        content = env_file.read_text(encoding="utf-8")
        if re.search(r"^APP_KEY=", content, flags=re.MULTILINE):
            content = re.sub(r"^APP_KEY=.*$", f"APP_KEY={key}", content, flags=re.MULTILINE)
        else:
            content = content.rstrip("\n") + f"\nAPP_KEY={key}\n"
        env_file.write_text(content, encoding="utf-8")

        self.success("Application key set successfully.")
        return self.SUCCESS
