import asyncio

from core.foundation.container import Container


class DummyService:
    pass


class DummyRepo:
    def __init__(self, service: DummyService):
        self.service = service


def test_bind_speed(benchmark):
    def bind_many():
        c = Container()
        for i in range(1000):
            c.bind(f"service.{i}", DummyService)

    benchmark(bind_many)


def test_make_speed(benchmark):
    c = Container()
    c.bind(DummyService, DummyService)

    def make():
        asyncio.get_event_loop().run_until_complete(c.make(DummyService))

    benchmark(make)


def test_singleton_speed(benchmark):
    c = Container()
    c.singleton(DummyService, DummyService)

    def make_singleton():
        asyncio.get_event_loop().run_until_complete(c.make(DummyService))

    benchmark(make_singleton)


def test_resolve_with_deps(benchmark):
    c = Container()
    c.bind(DummyService, DummyService)
    c.bind(DummyRepo, DummyRepo)

    def resolve():
        asyncio.get_event_loop().run_until_complete(c.make(DummyRepo))

    benchmark(resolve)
