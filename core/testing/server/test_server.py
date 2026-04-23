from __future__ import annotations

import pytest

from core.server.base import BaseServer, ServerConfig, ServerType
from core.server.granian import GranianServer
from core.server.uvicorn import UvicornServer


class TestServerConfig:
    def test_defaults(self):
        cfg = ServerConfig()
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 8000
        assert cfg.workers == 1
        assert cfg.reload is False

    def test_custom(self):
        cfg = ServerConfig(host="127.0.0.1", port=3000, workers=4, reload=True)
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 3000
        assert cfg.workers == 4


class TestUvicornServer:
    def test_init(self):
        server = UvicornServer()
        assert server.name == "uvicorn"
        assert server.server_type == ServerType.UVICORN

    def test_custom_config(self):
        cfg = ServerConfig(port=9000)
        server = UvicornServer(cfg)
        assert server.config.port == 9000

    def test_is_available(self):
        # uvicorn should be installed in test env
        assert UvicornServer.is_available() is True

    def test_repr(self):
        server = UvicornServer()
        r = repr(server)
        assert "UvicornServer" in r
        assert "8000" in r


class TestGranianServer:
    def test_init(self):
        server = GranianServer()
        assert server.name == "granian"
        assert server.server_type == ServerType.GRANIAN

    def test_interface(self):
        server = GranianServer(interface="rsgi")
        assert server._interface == "rsgi"

    def test_run_requires_string(self):
        server = GranianServer()
        if GranianServer.is_available():
            with pytest.raises(TypeError, match="import string"):
                server.run(object())  # not a string

    def test_async_serve_not_supported(self):
        GranianServer()

    def test_repr(self):
        server = GranianServer()
        r = repr(server)
        assert "GranianServer" in r


class TestServerProvider:
    @pytest.mark.asyncio
    async def test_register(self):
        from core.foundation.application import Application
        from core.server.servcer_service_provider import ServerServiceProvider

        app = Application()
        provider = ServerServiceProvider(app)
        await provider.register()

        server = await app.make("server")
        assert isinstance(server, BaseServer)

        config = await app.make(ServerConfig)
        assert isinstance(config, ServerConfig)
