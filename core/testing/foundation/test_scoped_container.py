import pytest

from core.foundation import Container
from core.testing.foundation.conftest import DummyConfig, SimpleClass


class TestScopedContainer:
    @pytest.mark.asyncio
    async def test_scoped_same_within_scope(self):
        container = Container()
        container.scoped("uow", SimpleClass)

        async with container.create_scope("request") as scope:
            a = await scope.make("uow")
            b = await scope.make("uow")
            assert a is b

        await container.close()

    @pytest.mark.asyncio
    async def test_scoped_different_across_scopes(self):
        container = Container()
        container.scoped("uow", SimpleClass)

        async with container.create_scope("req1") as s1:
            a = await s1.make("uow")

        async with container.create_scope("req2") as s2:
            b = await s2.make("uow")

        assert a is not b
        await container.close()

    @pytest.mark.asyncio
    async def test_scoped_delegates_non_scoped(self):
        container = Container()
        container.singleton("config", DummyConfig)
        container.scoped("uow", SimpleClass)

        async with container.create_scope("req") as scope:
            cfg = await scope.make("config")
            assert isinstance(cfg, DummyConfig)

        await container.close()

    @pytest.mark.asyncio
    async def test_scope_has(self):
        container = Container()
        container.scoped("uow", SimpleClass)
        container.bind("other", DummyConfig)

        async with container.create_scope("req") as scope:
            # Before resolve
            assert scope.has("uow")
            assert scope.has("other")
            assert not scope.has("nonexistent")

        await container.close()

    @pytest.mark.asyncio
    async def test_scope_close_calls_cleanup(self):
        container = Container()

        class ScopedResource:
            closed = False

            async def aclose(self):
                self.closed = True

        container.scoped("resource", ScopedResource)

        async with container.create_scope("req") as scope:
            resource = await scope.make("resource")

        assert resource.closed
        await container.close()

    @pytest.mark.asyncio
    async def test_scope_repr(self):
        container = Container()
        container.scoped("x", SimpleClass)
        scope = container.create_scope("test_scope")
        r = repr(scope)
        assert "ScopedContainer" in r
        assert "test_scope" in r
        await scope.close()
        await container.close()
