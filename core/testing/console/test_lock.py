import pytest

from core.console.lock import CommandLock


class TestCommandLock:
    @pytest.mark.asyncio
    async def test_acquire_and_release(self, tmp_path):
        lock = CommandLock(str(tmp_path))
        acquired = await lock.acquire("test:cmd")
        assert acquired is True
        assert lock.is_locked("test:cmd") is True

        released = await lock.release("test:cmd")
        assert released is True
        assert lock.is_locked("test:cmd") is False

    @pytest.mark.asyncio
    async def test_double_acquire_fails(self, tmp_path):
        lock = CommandLock(str(tmp_path))
        await lock.acquire("test:cmd")
        second = await lock.acquire("test:cmd")
        assert second is False
        await lock.release("test:cmd")

    @pytest.mark.asyncio
    async def test_release_nonexistent(self, tmp_path):
        lock = CommandLock(str(tmp_path))
        released = await lock.release("nonexistent")
        assert released is False

    @pytest.mark.asyncio
    async def test_is_locked_false_initially(self, tmp_path):
        lock = CommandLock(str(tmp_path))
        assert lock.is_locked("test:cmd") is False

    @pytest.mark.asyncio
    async def test_clear_all(self, tmp_path):
        lock = CommandLock(str(tmp_path))
        await lock.acquire("cmd1")
        await lock.acquire("cmd2")
        count = await lock.clear_all()
        assert count == 2
        assert lock.is_locked("cmd1") is False
        assert lock.is_locked("cmd2") is False

    @pytest.mark.asyncio
    async def test_lock_creates_directory(self, tmp_path):
        deep = tmp_path / "a" / "b" / "locks"
        lock = CommandLock(str(deep))
        await lock.acquire("test")
        assert deep.exists()
        await lock.release("test")

    @pytest.mark.asyncio
    async def test_lock_key_sanitized(self, tmp_path):
        lock = CommandLock(str(tmp_path))
        await lock.acquire("cache:clear")
        lock_file = tmp_path / "cache_clear.lock"
        assert lock_file.exists()
        await lock.release("cache:clear")

    @pytest.mark.asyncio
    async def test_stale_lock_detected(self, tmp_path):
        import json
        import time

        lock = CommandLock(str(tmp_path))
        lock_file = tmp_path / "stale.lock"
        lock_file.write_text(
            json.dumps(
                {
                    "pid": 999999999,  # non-existent PID
                    "time": time.time() - 100000,
                    "owner": "old",
                }
            )
        )

        acquired = await lock.acquire("stale")
        assert acquired is True
        await lock.release("stale")
