from typing import Protocol

import pytest
import pytest_asyncio

from core.foundation import Application, Platform, ServiceProvider


class Config:
    db_url: str = "sqlite+aiosqlite:///test.db"
    cache_url: str = "memory://"
    app_name: str = "TestApp"


class CacheProtocol(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str) -> None: ...


class DatabaseProtocol(Protocol):
    async def query(self, sql: str) -> list: ...
    async def close(self) -> None: ...


class MailerProtocol(Protocol):
    async def send(self, to: str, body: str) -> None: ...


class InMemoryCache:
    def __init__(self, config: Config):
        self._data = {}
        self.config = config

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def set(self, key: str, value: str) -> None:
        self._data[key] = value


class FakeDatabase:
    def __init__(self, config: Config):
        self.config = config
        self.connected = False
        self.closed = False
        self.queries: list[str] = []

    async def connect(self):
        self.connected = True

    async def query(self, sql: str) -> list:
        self.queries.append(sql)
        return [{"id": 1, "sql": sql}]

    async def close(self):
        self.closed = True


class LogMailer:
    def __init__(self, config: Config, cache: CacheProtocol):
        self.config = config
        self.cache = cache
        self.sent: list[dict] = []

    async def send(self, to: str, body: str) -> None:
        self.sent.append({"to": to, "body": body})
        await self.cache.set(f"mail:{to}", body)


class UserRepository:
    def __init__(self, db: DatabaseProtocol):
        self.db = db

    async def find(self, user_id: int):
        return await self.db.query(f"SELECT * FROM users WHERE id={user_id}")

    async def all(self):
        return await self.db.query("SELECT * FROM users")


class UserService:
    def __init__(self, repo: UserRepository, mailer: MailerProtocol, cache: CacheProtocol):
        self.repo = repo
        self.mailer = mailer
        self.cache = cache

    async def register(self, name: str, email: str) -> dict:
        await self.mailer.send(email, f"Welcome {name}!")
        await self.cache.set(f"user:{email}", name)
        return {"name": name, "email": email}

    async def get(self, user_id: int):
        return await self.repo.find(user_id)


class ConfigProvider(ServiceProvider):
    async def register(self) -> None:
        self.app.instance(Config, Config())


class DatabaseProvider(ServiceProvider):
    async def register(self) -> None:
        self.app.singleton(DatabaseProtocol, FakeDatabase)
        self.app.alias(DatabaseProtocol, "db")

    async def boot(self) -> None:
        db = await self.app.make(DatabaseProtocol)
        await db.connect()


class CacheProvider(ServiceProvider):
    async def register(self) -> None:
        self.app.singleton(CacheProtocol, InMemoryCache)
        self.app.alias(CacheProtocol, "cache")


class MailProvider(ServiceProvider):
    async def register(self) -> None:
        self.app.singleton(MailerProtocol, LogMailer)


class AppServiceProvider(ServiceProvider):
    async def register(self) -> None:
        self.app.bind(UserRepository)
        self.app.bind(UserService)
        self.app.tag([CacheProtocol, DatabaseProtocol, MailerProtocol], "core_services")


class DeferredAnalyticsProvider(ServiceProvider):
    @property
    def deferred(self) -> bool:
        return True

    def provides(self) -> list:
        return ["analytics"]

    async def register(self) -> None:
        self.app.instance("analytics", {"engine": "fake_analytics"})


class TestFullApplicationLifecycle:
    @pytest_asyncio.fixture
    async def booted_app(self, tmp_path):
        app = Application(base_path=str(tmp_path))
        app.register_providers(
            ConfigProvider, DatabaseProvider, CacheProvider, MailProvider, AppServiceProvider, DeferredAnalyticsProvider
        )
        await app.boot()
        yield app
        await app.shutdown()

    @pytest.mark.asyncio
    async def test_app_is_booted(self, booted_app):
        assert booted_app.is_booted

    @pytest.mark.asyncio
    async def test_providers_count(self, booted_app):
        assert len(booted_app.get_providers()) == 5

    @pytest.mark.asyncio
    async def test_config_resolved(self, booted_app):
        config = await booted_app.make(Config)
        assert config.app_name == "TestApp"

    @pytest.mark.asyncio
    async def test_database_connected_on_boot(self, booted_app):
        db = await booted_app.make(DatabaseProtocol)
        assert db.connected

    @pytest.mark.asyncio
    async def test_singleton_same_instance(self, booted_app):
        db1 = await booted_app.make(DatabaseProtocol)
        db2 = await booted_app.make(DatabaseProtocol)
        assert db1 is db2

    @pytest.mark.asyncio
    async def test_alias_resolution(self, booted_app):
        db_by_alias = await booted_app.make("db")
        db_by_type = await booted_app.make(DatabaseProtocol)
        assert db_by_alias is db_by_type

    @pytest.mark.asyncio
    async def test_deep_dependency_chain(self, booted_app):
        service = await booted_app.make(UserService)
        assert isinstance(service, UserService)
        assert isinstance(service.repo, UserRepository)
        assert isinstance(service.repo.db, FakeDatabase)
        assert isinstance(service.mailer, LogMailer)
        assert isinstance(service.cache, InMemoryCache)

    @pytest.mark.asyncio
    async def test_user_registration_flow(self, booted_app):
        service = await booted_app.make(UserService)
        result = await service.register("Alice", "alice@example.com")
        assert result == {"name": "Alice", "email": "alice@example.com"}

        mailer = await booted_app.make(MailerProtocol)
        assert len(mailer.sent) == 1
        assert mailer.sent[0]["to"] == "alice@example.com"

        cache = await booted_app.make(CacheProtocol)
        cached_name = await cache.get("user:alice@example.com")
        assert cached_name == "Alice"

    @pytest.mark.asyncio
    async def test_tagged_services(self, booted_app):
        services = await booted_app.tagged("core_services")
        assert len(services) == 3

    @pytest.mark.asyncio
    async def test_deferred_provider_lazy_load(self, booted_app):
        assert not booted_app.has("analytics")
        analytics = await booted_app.make("analytics")
        assert analytics == {"engine": "fake_analytics"}
        assert booted_app.has("analytics")

    @pytest.mark.asyncio
    async def test_swap_for_testing(self, booted_app):
        class MockMailer:
            sent = []

            async def send(self, to: str, body: str) -> None:
                self.sent.append(to)

        mock_mailer = MockMailer()
        booted_app.swap(MailerProtocol, mock_mailer)

        mailer = await booted_app.make(MailerProtocol)
        assert mailer is mock_mailer

        booted_app.forget_swap(MailerProtocol)

    @pytest.mark.asyncio
    async def test_scoped_container(self, booted_app):
        class RequestContext:
            def __init__(self):
                self.id = id(self)

        booted_app.scoped("request_ctx", RequestContext)

        async with booted_app.create_scope("req1") as s1:
            ctx1a = await s1.make("request_ctx")
            ctx1b = await s1.make("request_ctx")
            assert ctx1a is ctx1b

        async with booted_app.create_scope("req2") as s2:
            ctx2 = await s2.make("request_ctx")
            assert ctx2 is not ctx1a

    @pytest.mark.asyncio
    async def test_contextual_binding(self, booted_app):
        class Storage:
            name = "base"

        class S3Storage(Storage):
            name = "s3"

        class LocalStorage(Storage):
            name = "local"

        class PhotoUploader:
            def __init__(self, storage: Storage):
                self.storage = storage

        class VideoUploader:
            def __init__(self, storage: Storage):
                self.storage = storage

        booted_app.bind(Storage, LocalStorage)
        booted_app.when(PhotoUploader).needs(Storage).give(S3Storage)

        photo = await booted_app.make(PhotoUploader)
        video = await booted_app.make(VideoUploader)

        assert photo.storage.name == "s3"
        assert video.storage.name == "local"

    @pytest.mark.asyncio
    async def test_container_call(self, booted_app):
        async def get_app_name(config: Config) -> str:
            return config.app_name

        result = await booted_app.call(get_app_name)
        assert result == "TestApp"

    @pytest.mark.asyncio
    async def test_factory(self, booted_app):
        create_repo = await booted_app.factory(UserRepository)
        repo = await create_repo()
        assert isinstance(repo, UserRepository)

    @pytest.mark.asyncio
    async def test_has_and_contains(self, booted_app):
        assert booted_app.has(Config)
        assert Config in booted_app
        assert "db" in booted_app
        assert not booted_app.has("nonexistent_key_xyz")

    @pytest.mark.asyncio
    async def test_make_or_default(self, booted_app):
        result = await booted_app.make_or("nonexistent", "fallback")
        assert result == "fallback"

        config = await booted_app.make_or(Config, None)
        assert isinstance(config, Config)


class TestApplicationPlatformIntegration:
    @pytest.mark.asyncio
    async def test_platform_bound(self, app):
        """Test without full boot — just check instance binding."""
        platform = await app.make(Platform)
        assert isinstance(platform, Platform)

    @pytest.mark.asyncio
    async def test_platform_via_alias(self, app):
        platform = await app.make("platform")
        assert isinstance(platform, Platform)


class TestApplicationShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_closes_resources(self, tmp_path):
        app = Application(base_path=str(tmp_path))

        class Resource:
            closed = False

            async def close(self):
                self.closed = True

        resource = Resource()

        class ResourceProvider(ServiceProvider):
            async def register(self) -> None:
                self.app.instance("resource", resource)

        app.register_provider(ResourceProvider)
        await app.boot()
        await app.shutdown()

        assert resource.closed
        assert not app.is_booted
