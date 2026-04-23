import pytest

from core.exceptions import (
    BindingNotFoundException,
    BindingResolutionException,
    CircularDependencyException,
    StrictContainerException,
)
from core.foundation import (
    Container,
)
from core.testing.foundation.conftest import (
    CacheInterface,
    ClassWithDefault,
    DatabaseInterface,
    DummyCache,
    DummyConfig,
    DummyDatabase,
    DummyRepository,
    DummyService,
    SimpleClass,
)


class TestContainerBind:
    @pytest.mark.asyncio
    async def test_bind_and_make(self, container):
        container.bind("key", SimpleClass)
        obj = await container.make("key")
        assert isinstance(obj, SimpleClass)

    @pytest.mark.asyncio
    async def test_bind_transient_creates_new_instances(self, container):
        container.bind("key", SimpleClass)
        a = await container.make("key")
        b = await container.make("key")
        assert a is not b

    @pytest.mark.asyncio
    async def test_bind_self(self, container):
        container.bind(SimpleClass)
        obj = await container.make(SimpleClass)
        assert isinstance(obj, SimpleClass)

    @pytest.mark.asyncio
    async def test_bind_module_raises(self, container):
        import os

        with pytest.raises(StrictContainerException, match="module"):
            container.bind("os", os)

    @pytest.mark.asyncio
    async def test_bind_if_does_not_override(self, container):
        container.bind("key", SimpleClass)
        container.bind_if("key", DummyConfig)
        obj = await container.make("key")
        assert isinstance(obj, SimpleClass)

    @pytest.mark.asyncio
    async def test_bind_if_binds_when_missing(self, container):
        container.bind_if("key", SimpleClass)
        obj = await container.make("key")
        assert isinstance(obj, SimpleClass)


class TestContainerSingleton:
    @pytest.mark.asyncio
    async def test_singleton_returns_same_instance(self, container):
        container.singleton("key", SimpleClass)
        a = await container.make("key")
        b = await container.make("key")
        assert a is b

    @pytest.mark.asyncio
    async def test_singleton_if_does_not_override(self, container):
        container.singleton("key", SimpleClass)
        first = await container.make("key")
        container.singleton_if("key", DummyConfig)
        second = await container.make("key")
        assert first is second


class TestContainerInstance:
    @pytest.mark.asyncio
    async def test_instance_returns_exact_object(self, container):
        cfg = DummyConfig()
        container.instance("config", cfg)
        result = await container.make("config")
        assert result is cfg

    @pytest.mark.asyncio
    async def test_instance_with_class_key(self, container):
        cfg = DummyConfig()
        container.instance(DummyConfig, cfg)
        result = await container.make(DummyConfig)
        assert result is cfg


class TestContainerAlias:
    @pytest.mark.asyncio
    async def test_alias_resolves(self, container):
        container.singleton("database", SimpleClass)
        container.alias("database", "db")
        obj = await container.make("db")
        assert isinstance(obj, SimpleClass)

    @pytest.mark.asyncio
    async def test_chained_alias(self, container):
        container.singleton("database", SimpleClass)
        container.alias("database", "db")
        container.alias("db", "d")
        obj = await container.make("d")
        assert isinstance(obj, SimpleClass)

    @pytest.mark.asyncio
    async def test_circular_alias_raises(self, container):
        """Circular alias: a → b → a should raise."""
        # Нужно чтобы оба были в _aliases
        container._aliases["a"] = "b"
        container._aliases["b"] = "a"
        with pytest.raises(BindingResolutionException, match="Circular alias"):
            await container.make("a")


class TestContainerAutoResolve:
    @pytest.mark.asyncio
    async def test_auto_resolve_no_deps(self, container):
        obj = await container.make(SimpleClass)
        assert isinstance(obj, SimpleClass)

    @pytest.mark.asyncio
    async def test_auto_resolve_with_default(self, container):
        obj = await container.make(ClassWithDefault)
        assert isinstance(obj, ClassWithDefault)
        assert obj.name == "default"

    @pytest.mark.asyncio
    async def test_resolve_chain(self, container):
        cfg = DummyConfig()
        container.instance(DummyConfig, cfg)
        container.singleton(DatabaseInterface, DummyDatabase)
        container.singleton(CacheInterface, DummyCache)
        container.bind(DummyRepository)
        container.bind(DummyService)

        service = await container.make(DummyService)
        assert isinstance(service, DummyService)
        assert isinstance(service.repo, DummyRepository)
        assert isinstance(service.repo.db, DummyDatabase)
        assert isinstance(service.cache, DummyCache)


class TestContainerCallable:
    @pytest.mark.asyncio
    async def test_bind_factory_lambda(self, container):
        container.bind("greeting", lambda c: "hello world")
        result = await container.make("greeting")
        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_bind_async_factory(self, container):
        async def factory(c):
            return "async hello"

        container.bind("greeting", factory)
        result = await container.make("greeting")
        assert result == "async hello"


class TestContainerCall:
    @pytest.mark.asyncio
    async def test_call_function(self, container):
        cfg = DummyConfig()
        container.instance(DummyConfig, cfg)

        async def my_func(config: DummyConfig):
            return config.db_url

        result = await container.call(my_func)
        assert result == cfg.db_url

    @pytest.mark.asyncio
    async def test_call_with_extra_kwargs(self, container):
        async def my_func(name: str, age: int = 30):
            return f"{name}:{age}"

        result = await container.call(my_func, "Alice", age=25)
        assert result == "Alice:25"


class TestContainerTags:
    @pytest.mark.asyncio
    async def test_tagged_resolution(self, container):
        container.bind("a", SimpleClass)
        container.bind("b", DummyConfig)
        container.tag(["a", "b"], "services")

        results = await container.tagged("services")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_tagged_empty(self, container):
        results = await container.tagged("nonexistent")
        assert results == []


class TestContainerSwap:
    @pytest.mark.asyncio
    async def test_swap_overrides(self, container):
        container.singleton("cache", SimpleClass)
        container.swap("cache", DummyConfig())

        result = await container.make("cache")
        assert isinstance(result, DummyConfig)

    @pytest.mark.asyncio
    async def test_swap_callable(self, container):
        container.singleton("val", SimpleClass)
        container.swap("val", lambda c: "swapped")

        result = await container.make("val")
        assert result == "swapped"

    @pytest.mark.asyncio
    async def test_forget_swap(self, container):
        container.singleton("cache", SimpleClass)
        container.swap("cache", DummyConfig())
        container.forget_swap("cache")

        result = await container.make("cache")
        assert isinstance(result, SimpleClass)


class TestContainerCollect:
    def test_collect_by_pattern(self, container):
        container.bind("UserHook", SimpleClass)
        container.bind("AdminHook", SimpleClass)
        container.bind("Logger", DummyConfig)

        result = container.collect("*Hook")
        assert len(result) == 2
        assert "UserHook" in result
        assert "AdminHook" in result

    def test_collect_prefix(self, container):
        container.bind("Sentry_client", SimpleClass)
        container.bind("Sentry_dsn", DummyConfig)
        container.bind("Redis", SimpleClass)

        result = container.collect("Sentry*")
        assert len(result) == 2

    def test_collect_by_class(self, container):
        class Base:
            pass

        class Child(Base):
            pass

        container.bind("child", Child)
        container.bind("other", SimpleClass)

        result = container.collect(Base)
        assert len(result) == 1


class TestContainerHooks:
    def test_on_bind_fires(self, container):
        fired = []
        container.on_bind("key", lambda obj, c: fired.append(obj))
        container.bind("key", SimpleClass)
        assert len(fired) == 1
        assert fired[0] is SimpleClass

    @pytest.mark.asyncio
    async def test_on_make_fires(self, container):
        fired = []
        container.on_make("key", lambda obj, c: fired.append(True))
        container.bind("key", SimpleClass)
        await container.make("key")
        assert len(fired) == 1

    @pytest.mark.asyncio
    async def test_global_resolving_callback(self, container):
        resolved = []
        container.resolving(lambda obj, c: resolved.append(obj))
        container.bind("key", SimpleClass)
        await container.make("key")
        assert SimpleClass in resolved


class TestContainerHas:
    def test_has_string_key(self, container):
        container.bind("key", SimpleClass)
        assert container.has("key")
        assert "key" in container

    def test_has_class_key(self, container):
        container.bind(SimpleClass)
        assert container.has(SimpleClass)

    def test_has_missing(self, container):
        assert not container.has("nonexistent")


class TestContainerUnbind:
    def test_unbind_existing(self, container):
        container.bind("key", SimpleClass)
        assert container.unbind("key") is True
        assert not container.has("key")

    def test_unbind_missing(self, container):
        assert container.unbind("nonexistent") is False


class TestContainerMakeOrDefault:
    @pytest.mark.asyncio
    async def test_make_or_returns_value(self, container):
        container.bind("key", lambda c: "value")
        result = await container.make_or("key", "default")
        assert result == "value"

    @pytest.mark.asyncio
    async def test_make_or_returns_default(self, container):
        result = await container.make_or("missing", "fallback")
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_make_or_callable_default(self, container):
        result = await container.make_or("missing", lambda: "computed")
        assert result == "computed"


class TestContainerFactory:
    @pytest.mark.asyncio
    async def test_factory_creates(self, container):
        container.bind("key", SimpleClass)
        factory_fn = await container.factory("key")
        obj = await factory_fn()
        assert isinstance(obj, SimpleClass)


class TestContainerStrict:
    @pytest.mark.asyncio
    async def test_strict_raises_on_override(self):
        c = Container(strict=True)
        c.bind("key", SimpleClass)
        with pytest.raises(StrictContainerException):
            c.bind("key", DummyConfig)
        await c.close()


class TestCircularDependency:
    @pytest.mark.asyncio
    async def test_circular_raises(self, container):
        """Test circular dependency: A needs B, B needs A."""

        class B:
            pass

        class A:
            def __init__(self, b: B):
                pass

        # Now redefine B to need A (after A is defined)
        class B_real:
            def __init__(self, a: A):
                pass

        container.bind(A)
        container.bind(B, B_real)

        with pytest.raises((CircularDependencyException, BindingResolutionException)):
            await container.make(A)


class TestContainerNotFound:
    @pytest.mark.asyncio
    async def test_missing_binding_raises(self, container):
        with pytest.raises(BindingNotFoundException):
            await container.make("nonexistent_key")


class TestContainerFlush:
    @pytest.mark.asyncio
    async def test_flush_clears_everything(self, container):
        container.bind("a", SimpleClass)
        container.singleton("b", DummyConfig)
        container.alias("b", "bb")
        container.tag(["a"], "group")

        container.flush()
        assert not container.has("a")
        assert not container.has("b")
        assert len(container.get_bindings()) == 0

    @pytest.mark.asyncio
    async def test_forget_instances(self, container):
        container.singleton("key", SimpleClass)
        a = await container.make("key")
        container.forget_instances()
        b = await container.make("key")
        assert a is not b


class TestContainerClose:
    @pytest.mark.asyncio
    async def test_close_calls_aclose(self, container):
        class Closeable:
            closed = False

            async def aclose(self):
                self.closed = True

        obj = Closeable()
        container.instance("resource", obj)
        await container.close()
        assert obj.closed

    @pytest.mark.asyncio
    async def test_close_calls_sync_close(self, container):
        class SyncCloseable:
            closed = False

            def close(self):
                self.closed = True

        obj = SyncCloseable()
        container.instance("resource", obj)
        await container.close()
        assert obj.closed


class TestContainerRepr:
    def test_repr(self, container):
        container.bind("a", SimpleClass)
        r = repr(container)
        assert "Container" in r
        assert "bindings=1" in r
