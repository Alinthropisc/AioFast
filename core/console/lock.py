from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class CommandLock:
    def __init__(self, locks_dir: str = "storage/locks") -> None:
        self._dir = Path(locks_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _lock_path(self, key: str) -> Path:
        safe = key.replace(":", "_").replace("/", "_")
        return self._dir / f"{safe}.lock"

    async def acquire(self, key: str, timeout: int = 0, owner: str = "") -> bool:
        path = self._lock_path(key)

        if path.exists():
            info = self._read_lock(path)
            if info and self._is_stale(info):
                logger.debug("Removing stale lock: %s", key)
                path.unlink(missing_ok=True)
            elif timeout > 0:
                import asyncio

                deadline = time.monotonic() + timeout
                while path.exists() and time.monotonic() < deadline:
                    await asyncio.sleep(0.5)
                if path.exists():
                    return False
            else:
                return False

        self._write_lock(path, owner)
        logger.debug("Lock acquired: %s", key)
        return True

    async def release(self, key: str) -> bool:
        path = self._lock_path(key)
        if path.exists():
            path.unlink(missing_ok=True)
            logger.debug("Lock released: %s", key)
            return True
        return False

    def is_locked(self, key: str) -> bool:
        path = self._lock_path(key)
        if not path.exists():
            return False
        info = self._read_lock(path)
        if info and self._is_stale(info):
            path.unlink(missing_ok=True)
            return False
        return True

    def _write_lock(self, path: Path, owner: str = "") -> None:
        data = {
            "pid": os.getpid(),
            "time": time.time(),
            "owner": owner or str(os.getpid()),
        }
        path.write_text(json.dumps(data), encoding="utf-8")

    def _read_lock(self, path: Path) -> dict | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _is_stale(info: dict, max_age: int = 86400) -> bool:
        pid = info.get("pid")
        created = info.get("time", 0)

        if time.time() - created > max_age:
            return True
        if pid is not None:
            try:
                os.kill(pid, 0)
            except OSError:
                return True
        return False

    async def clear_all(self) -> int:
        count = 0
        for f in self._dir.glob("*.lock"):
            f.unlink(missing_ok=True)
            count += 1
        return count
