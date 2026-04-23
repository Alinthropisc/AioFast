from core.console.loader import CommandLoader, LazyCommand
from core.testing.console.conftest import ArgCommand, HiddenTestCommand, SimpleCommand


class TestCommandLoader:
    def test_register(self):
        loader = CommandLoader()
        loader.register(SimpleCommand)
        assert loader.has("simple")
        assert len(loader) == 1

    def test_register_with_aliases(self):
        loader = CommandLoader()
        loader.register(ArgCommand)
        assert loader.has("greet")
        assert loader.has("hello")
        assert loader.has("hi")

    def test_get_by_name(self):
        loader = CommandLoader()
        loader.register(SimpleCommand)
        assert loader.get("simple") is SimpleCommand

    def test_get_by_alias(self):
        loader = CommandLoader()
        loader.register(ArgCommand)
        assert loader.get("hello") is ArgCommand

    def test_get_missing_returns_none(self):
        loader = CommandLoader()
        assert loader.get("nonexistent") is None

    def test_all(self):
        loader = CommandLoader()
        loader.register(SimpleCommand)
        loader.register(ArgCommand)
        all_cmds = loader.all()
        assert "simple" in all_cmds
        assert "greet" in all_cmds

    def test_names(self):
        loader = CommandLoader()
        loader.register(SimpleCommand)
        loader.register(ArgCommand)
        names = loader.names()
        assert "simple" in names
        assert "greet" in names

    def test_has_false(self):
        loader = CommandLoader()
        assert loader.has("nope") is False

    def test_grouped(self):
        loader = CommandLoader()
        loader.register(SimpleCommand)
        loader.register(HiddenTestCommand)
        groups = loader.grouped()
        assert "" in groups
        assert "debug" in groups

    def test_len(self):
        loader = CommandLoader()
        assert len(loader) == 0
        loader.register(SimpleCommand)
        assert len(loader) == 1


class TestLazyCommand:
    def test_lazy_register_and_resolve(self):
        loader = CommandLoader()
        lazy = LazyCommand(
            name="simple",
            module_path="core.testing.console.conftest",
            class_name="SimpleCommand",
        )
        loader.register_lazy(lazy)
        assert loader.has("simple")

        cls = loader.get("simple")
        assert cls is not None
        assert cls.name == "simple"

    def test_lazy_with_aliases(self):
        loader = CommandLoader()
        lazy = LazyCommand(
            name="greet",
            module_path="core.testing.console.conftest",
            class_name="ArgCommand",
            aliases=["hello"],
        )
        loader.register_lazy(lazy)
        assert loader.has("hello")


class TestCommandLoaderDiscover:
    def test_discover_from_path(self, tmp_path):
        cmd_dir = tmp_path / "commands"
        cmd_dir.mkdir()

        (cmd_dir / "__init__.py").write_text("")
        (cmd_dir / "test_cmd.py").write_text(
            "from core.console.command import Command\n"
            "from typing import Any\n\n"
            "class PingCommand(Command):\n"
            "    name = 'ping'\n"
            "    description = 'Ping test'\n"
            "    async def handle(self, **kwargs: Any) -> int:\n"
            "        return self.SUCCESS\n"
        )

        import sys

        sys.path.insert(0, str(tmp_path))

        loader = CommandLoader()
        loader.discover(str(cmd_dir), "commands")

        assert loader.has("ping")
        sys.path.remove(str(tmp_path))

    def test_discover_skips_underscore(self, tmp_path):
        cmd_dir = tmp_path / "cmds"
        cmd_dir.mkdir()
        (cmd_dir / "_private.py").write_text("x = 1")

        loader = CommandLoader()
        loader.discover(str(cmd_dir))
        assert len(loader) == 0

    def test_discover_nonexistent_path(self):
        loader = CommandLoader()
        loader.discover("/nonexistent/path")
        assert len(loader) == 0
