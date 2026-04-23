import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import pytest
import pytest_asyncio

from core.foundation import Application, Container, Platform

root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "sourcefiles"))


@runtime_checkable
class DatabaseInterface(Protocol):
    async def query(self, sql: str) -> list: ...

    async def close(self) -> None: ...


@runtime_checkable
class CacheInterface(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str) -> None: ...


@runtime_checkable
class RepositoryInterface(Protocol):
    async def find(self, id: int) -> dict | None: ...


class Logger:
    def __init__(self):
        self.logs: list[str] = []

    def info(self, message: str) -> None:
        self.logs.append(f"INFO: {message}")

    def error(self, message: str) -> None:
        self.logs.append(f"ERROR: {message}")


class FakeDatabase:
    def __init__(self, connection_string: str = "fake://localhost"):
        self.connection_string = connection_string
        self.connected = True
        self.queries: list[str] = []

    async def query(self, sql: str) -> list:
        self.queries.append(sql)
        return [{"id": 1, "name": "test"}]

    async def close(self) -> None:
        self.connected = False


class FakeCache:
    def __init__(self):
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        self._store[key] = value


class UserRepository:
    def __init__(self, db: FakeDatabase, cache: FakeCache):
        self.db = db
        self.cache = cache

    async def find(self, id: int) -> dict | None:
        cached = await self.cache.get(f"user:{id}")
        if cached:
            return {"id": id, "name": cached}

        result = await self.db.query(f"SELECT * FROM users WHERE id = {id}")
        return result[0] if result else None


class UserService:
    def __init__(self, repo: UserRepository, logger: Logger):
        self.repo = repo
        self.logger = logger

    async def get_user(self, id: int) -> dict | None:
        self.logger.info(f"Getting user {id}")
        return await self.repo.find(id)


@dataclass
class Config:
    debug: bool = False
    database_url: str = "postgres://localhost/test"


class ServiceA:
    def __init__(self, b: "ServiceB"):
        self.b = b


class ServiceB:
    def __init__(self, a: ServiceA):
        self.a = a


class ServiceC:
    def __init__(self, d: "ServiceD"):
        self.d = d


class ServiceD:
    def __init__(self, e: "ServiceE"):
        self.e = e


class ServiceE:
    def __init__(self, c: ServiceC):
        self.c = c


@pytest.fixture
def fake_db() -> FakeDatabase:
    return FakeDatabase()


@pytest.fixture
def fake_cache() -> FakeCache:
    return FakeCache()


@pytest.fixture
def logger() -> Logger:
    return Logger()


@pytest.fixture
def config() -> Config:
    return Config(debug=True)


@pytest.fixture
async def test_server(aiohttp_server, app):
    """Create test HTTP server"""
    server = await aiohttp_server(app)
    return server


@pytest.fixture
def server_url(test_server):
    """Get test server URL"""
    return f"http://{test_server.host}:{test_server.port}"


class DummyConfig:
    db_url: str = "sqlite+aiosqlite:///test.db"
    redis_url: str = "redis://localhost"
    debug: bool = True


class DummyCache:
    def __init__(self, config: DummyConfig):
        self.config = config
        self.closed = False

    async def get(self, key: str) -> str | None:
        return f"cached:{key}"

    async def close(self):
        self.closed = True


class DummyDatabase:
    def __init__(self, config: DummyConfig):
        self.config = config
        self.connected = False
        self.closed = False

    async def query(self, sql: str) -> list:
        return [{"id": 1}]

    async def connect(self):
        self.connected = True

    async def close(self):
        self.closed = True


class DummyMailer:
    def __init__(self, config: DummyConfig, cache: CacheInterface):
        self.config = config
        self.cache = cache
        self.sent: list = []

    async def send(self, to: str, subject: str) -> None:
        self.sent.append({"to": to, "subject": subject})


class DummyRepository:
    def __init__(self, db: DatabaseInterface):
        self.db = db

    async def find(self, id: int):
        return await self.db.query(f"SELECT * WHERE id={id}")


class DummyService:
    def __init__(self, repo: DummyRepository, cache: CacheInterface):
        self.repo = repo
        self.cache = cache


class SimpleClass:
    pass


class ClassWithDefault:
    def __init__(self, name: str = "default"):
        self.name = name


class ClassWithPrimitives:
    def __init__(self, name: str, age: int = 25):
        self.name = name
        self.age = age


@pytest_asyncio.fixture
async def container():
    c = Container()
    yield c
    await c.close()


@pytest_asyncio.fixture
async def app(tmp_path):
    a = Application(base_path=str(tmp_path))
    yield a
    if a.is_booted:
        await a.shutdown()
    else:
        await a.close()


@pytest.fixture
def platform_obj():
    return Platform()
