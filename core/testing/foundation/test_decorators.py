import pytest

from core.foundation import Container, inject, injectable, service


class TestInjectableDecorator:
    def test_marks_class(self):
        @injectable
        class MyClass:
            pass

        assert hasattr(MyClass, "__injectable__")
        assert MyClass.__injectable__ is True

    def test_preserves_class(self):
        @injectable
        class MyClass:
            def hello(self):
                return "world"

        obj = MyClass()
        assert obj.hello() == "world"


class TestServiceDecorator:
    def test_default_meta(self):
        @service()
        class MyService:
            pass

        assert hasattr(MyService, "__service_meta__")
        meta = MyService.__service_meta__
        assert meta["name"] == "MyService"
        assert meta["singleton"] is False
        assert meta["tags"] == []

    def test_custom_meta(self):
        @service(name="my_svc", singleton=True, tags=["api", "core"])
        class MyService:
            pass

        meta = MyService.__service_meta__  # ty:ignore[unresolved-attribute]
        assert meta["name"] == "my_svc"
        assert meta["singleton"] is True
        assert "api" in meta["tags"]


class TestInjectDecorator:
    @pytest.mark.asyncio
    async def test_inject_with_container(self):
        """Test @inject on an instance method with container access."""
        container = Container()
        container.instance("greeting", "hello")

        class Controller:
            def __init__(self):
                self.container = container

            @inject
            async def index(self):
                return "action result"

        ctrl = Controller()
        # Call as bound method — self is automatically passed
        result = await ctrl.index()
        assert result == "action result"

        await container.close()

    @pytest.mark.asyncio
    async def test_inject_without_container(self):
        @inject
        async def standalone():
            return 42

        result = await standalone()
        assert result == 42

    @pytest.mark.asyncio
    async def test_inject_plain_function(self):
        """Test that @inject works on regular async functions."""

        @inject
        async def compute(x: int = 10):
            return x * 2

        result = await compute()
        assert result == 20
