from core.registry import RouteCollector


async def dummy_handler():
    return "ok"


def test_route_registration_speed(benchmark):
    def register():
        c = RouteCollector()
        for i in range(500):
            c.get(f"/api/v1/resource/{i}", dummy_handler, name=f"route_{i}")

    benchmark(register)


def test_route_lookup_speed(benchmark):
    c = RouteCollector()
    for i in range(500):
        c.get(f"/api/v1/resource/{i}", dummy_handler, name=f"route_{i}")

    def lookup():
        for r in c.collect():
            _ = r.path

    benchmark(lookup)
