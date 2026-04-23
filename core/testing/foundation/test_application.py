import pytest

from core.foundation import Application, Container, Platform, ServiceProvider
from core.testing.foundation.conftest import DummyConfig, SimpleClass


class TestApplicationInit:
    @pytest.mark.asyncio
    async def test_self_bindings(self, app):
        resolved_app = await app.make("app")
        assert resolved_app is app

        resolved_app2 = await app.make(Application)
        assert resolved_app2 is app

        resolved_container = await app.make(Container)
        assert resolved_container is app

        resolved_platform = await app.make(Platform)
        assert isinstance(resolved_platform, Platform)

    @pytest.mark.asyncio
    async def test_default_state(self, app):
        assert not app.is_booted
        assert app.app_env in ("testing", "local")

    def test_repr(self, app):
        r = repr(app)
        assert "Application" in r
        assert "not booted" in r


class TestApplicationPaths:
    def test_base_path(self, app, tmp_path):
        assert app.base_path == tmp_path

    def test_path_join(self, app, tmp_path):
        p = app.path("app", "models")
        assert p == tmp_path / "app" / "models"

    def test_storage_path(self, app, tmp_path):
        app.use_storage_path(str(tmp_path / "storage"))
        assert app.storage_path == tmp_path / "storage"
        log_path = app.storage("logs", "app.log")
        assert log_path == tmp_path / "storage" / "logs" / "app.log"

    def test_storage_default(self, app, tmp_path):
        p = app.storage("logs")
        assert p == tmp_path / "storage" / "logs"

    def test_config_path(self, app, tmp_path):
        app.use_config_path(str(tmp_path / "config"))
        p = app.config("database.py")
        assert p == tmp_path / "config" / "database.py"

    def test_database_path(self, app, tmp_path):
        app.use_database_path(str(tmp_path / "db"))
        p = app.database("migrations")
        assert p == tmp_path / "db" / "migrations"

    def test_resource_path(self, app, tmp_path):
        p = app.resource("views", "index.html")
        assert p == tmp_path / "resources" / "views" / "index.html"

    def test_public_path(self, app, tmp_path):
        p = app.public("assets", "app.js")
        assert p == tmp_path / "public" / "assets" / "app.js"

    def test_path_without_base_raises(self):
        a = Application()
        with pytest.raises(RuntimeError, match="base_path"):
            a.path("something")


class TestApplicationEnvironment:
    def test_is_testing(self, app):
        assert app.is_testing is True

    def test_app_env_testing(self, app):
        assert app.app_env == "testing"

    def test_is_debug_default_true(self, app):
        # Default APP_DEBUG is "true"
        assert app.is_debug is True

    def test_is_debug_false(self, app, monkeypatch):
        monkeypatch.setenv("APP_DEBUG", "false")
        assert app.is_debug is False

    def test_is_production(self, app, monkeypatch):
        # In testing mode, is_testing takes precedence for app_env
        monkeypatch.setenv("APP_ENV", "production")
        # Still testing because pytest is in sys.modules
        assert app.app_env == "testing"

    def test_is_console(self, app):
        # pytest running → typically sys.argv[1] != 'serve'
        assert isinstance(app.is_console, bool)


class TestApplicationPlatform:
    def test_platform_property(self, app):
        assert isinstance(app.platform, Platform)

    def test_os_properties(self, app):
        # At least one should be True
        assert isinstance(app.is_windows, bool)
        assert isinstance(app.is_linux, bool)
        assert isinstance(app.is_macos, bool)
        assert isinstance(app.is_unix, bool)

    def test_platform_info(self, app):
        info = app.platform_info
        assert info.os_name  # Should not be empty
        assert info.python_version


class TestApplicationLifecycle:
    @pytest.mark.asyncio
    async def test_boot(self, app):
        assert not app.is_booted
        await app.boot()
        assert app.is_booted

    @pytest.mark.asyncio
    async def test_double_boot_warning(self, app, caplog):
        await app.boot()
        import logging

        with caplog.at_level(logging.WARNING):
            await app.boot()
        assert "already booted" in caplog.text

    @pytest.mark.asyncio
    async def test_shutdown(self, app):
        await app.boot()
        await app.shutdown()
        assert not app.is_booted

    @pytest.mark.asyncio
    async def test_boot_and_resolve(self, app):
        class TestProvider(ServiceProvider):
            async def register(self) -> None:
                self.app.bind("greeting", lambda c: "hello")

        app.register_provider(TestProvider)
        await app.boot()

        result = await app.make("greeting")
        assert result == "hello"


class TestApplicationResponseHandler:
    def test_set_and_get_handler(self, app):
        def handler(*a, **k):
            return None

        app.set_response_handler(handler)
        assert app.get_response_handler() is handler

    def test_call_without_handler_raises(self, app):
        with pytest.raises(RuntimeError, match="No response handler"):
            app("arg1", "arg2")

    def test_call_with_handler(self, app):
        results = []
        app.set_response_handler(lambda *a, **k: results.append(a))
        app("hello", "world")
        assert results == [("hello", "world")]


class TestApplicationBindingShortcuts:
    @pytest.mark.asyncio
    async def test_bind(self, app):
        app.bind("key", SimpleClass)
        obj = await app.make("key")
        assert isinstance(obj, SimpleClass)

    @pytest.mark.asyncio
    async def test_singleton(self, app):
        app.singleton("key", SimpleClass)
        a = await app.make("key")
        b = await app.make("key")
        assert a is b

    @pytest.mark.asyncio
    async def test_instance(self, app):
        cfg = DummyConfig()
        app.instance("config", cfg)
        result = await app.make("config")
        assert result is cfg

    @pytest.mark.asyncio
    async def test_scoped(self, app):
        app.scoped("uow", SimpleClass)
        async with app.create_scope("req") as scope:
            a = await scope.make("uow")
            b = await scope.make("uow")
            assert a is b

    @pytest.mark.asyncio
    async def test_alias(self, app):
        app.singleton("database", SimpleClass)
        app.alias("database", "db")
        obj = await app.make("db")
        assert isinstance(obj, SimpleClass)

    @pytest.mark.asyncio
    async def test_tag(self, app):
        app.bind("a", SimpleClass)
        app.bind("b", DummyConfig)
        app.tag(["a", "b"], "group")
        results = await app.tagged("group")
        assert len(results) == 2

    def test_has(self, app):
        app.bind("key", SimpleClass)
        assert app.has("key")
        assert "key" in app

    def test_when(self, app):
        class Base:
            pass

        class ImplA(Base):
            pass

        class NeedsBase:
            def __init__(self, dep: Base):
                self.dep = dep

        app.bind(Base, ImplA)
        builder = app.when(NeedsBase)
        assert builder is not None
