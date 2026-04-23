from __future__ import annotations

from pathlib import Path
from typing import Any

from ..foundation import ServiceProvider
from .cache import ConfigCache
from .environment import Environment
from .manager import ConfigurationManager
from .secrets import SecretsResolver


class ConfigServiceProvider(ServiceProvider):
    """
    Registers Environment, ConfigurationManager, SecretsResolver.

    Boot order:
      1. Load .env files → Environment
      2. Load config/*.py → ConfigurationManager
      3. Try config cache (production)
      4. Validate configs
      5. Freeze in production
    """

    async def register(self) -> None:
        base = self.app.base_path or Path.cwd()

        # ── Environment ───────────────────────────────
        env = Environment(base_path=base)
        self.app.instance("env", env)
        self.app.instance(Environment, env)

        # ── Secrets ───────────────────────────────────
        secrets = SecretsResolver()
        secrets_dir = base / "secrets"
        if secrets_dir.exists():
            secrets.add_file_backend(secrets_dir)
        docker_secrets = Path("/run/secrets")
        if docker_secrets.exists():
            secrets.add_file_backend(docker_secrets)
        self.app.instance("secrets", secrets)
        self.app.instance(SecretsResolver, secrets)

        # ── ConfigurationManager ──────────────────────
        log = await self.app.make_or("log")
        manager = ConfigurationManager(base_path=base, log=log)
        self.app.instance("config", manager)
        self.app.instance(ConfigurationManager, manager)

        # ── Config Cache ──────────────────────────────
        cache = ConfigCache(base / "bootstrap" / "cache")
        self.app.instance("config.cache", cache)
        self.app.instance(ConfigCache, cache)

    async def boot(self) -> None:
        manager: ConfigurationManager = await self.app.make("config")
        cache: ConfigCache = await self.app.make("config.cache")
        env: Environment = await self.app.make("env")
        base = self.app.base_path or Path.cwd()
        config_path = self.app.config_path or base / "config"

        # Try loading from cache first (production)
        is_production = env.string("APP_ENV", "local") == "production"
        if is_production and cache.is_cached():
            cached = cache.load()
            if cached is not None:
                self._log_info("Loaded config from cache")
                return

        # Load config files
        if config_path.exists():
            await manager.load_from_path(config_path)
        # Merge defaults
        manager.merge_defaults()
        # Validate
        errors = manager.validate_all()

        if errors:
            for name, errs in errors.items():
                self._log_error("Config validation error [%s]: %s", name, errs)

        # Freeze in production
        if is_production:
            manager.freeze()
            env.freeze()
            cache.store(manager.all())
            self._log_info("Config frozen and cached for production")

    def _log_info(self, msg: str, *args: Any) -> None:
        import logging

        logging.getLogger("aiofast.config").info(msg, *args)

    def _log_error(self, msg: str, *args: Any) -> None:
        import logging

        logging.getLogger("aiofast.config").error(msg, *args)
