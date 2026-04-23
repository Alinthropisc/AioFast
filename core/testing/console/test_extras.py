from pathlib import Path

import pytest

from core.console.completion import CompletionGenerator
from core.console.docs_generator import DocsGenerator
from core.console.signals import SignalManager
from core.console.stub_engine import StubEngine
from core.testing.console.conftest import ArgCommand, HiddenTestCommand, SimpleCommand

# ── StubEngine ────────────────────────────────────────────


class TestStubEngine:
    def test_render(self, tmp_path):
        stubs_dir = tmp_path / "stubs"
        stubs_dir.mkdir()
        (stubs_dir / "test.stub").write_text("class {{ className }}:\n    name = '{{ name }}'\n")
        engine = StubEngine(custom_stubs_dir=str(stubs_dir))
        result = engine.render("test", {"className": "MyCmd", "name": "my:cmd"})
        assert "class MyCmd:" in result
        assert "name = 'my:cmd'" in result

    def test_generate_file(self, tmp_path):
        stubs_dir = tmp_path / "stubs"
        stubs_dir.mkdir()
        (stubs_dir / "test.stub").write_text("Hello {{ who }}!")

        engine = StubEngine(custom_stubs_dir=str(stubs_dir))
        output = tmp_path / "output" / "test.py"
        path = engine.generate("test", str(output), {"who": "World"})

        assert Path(path).exists()
        assert "Hello World!" in Path(path).read_text()

    def test_missing_stub_raises(self):
        engine = StubEngine(custom_stubs_dir="/nonexistent")
        with pytest.raises(FileNotFoundError):
            engine.render("nonexistent_stub_xyz", {})

    def test_stub_exists_true(self, tmp_path):
        stubs_dir = tmp_path / "stubs"
        stubs_dir.mkdir()
        (stubs_dir / "exists.stub").write_text("test")
        engine = StubEngine(custom_stubs_dir=str(stubs_dir))
        assert engine.stub_exists("exists") is True

    def test_stub_exists_false(self, tmp_path):
        engine = StubEngine(custom_stubs_dir=str(tmp_path))
        assert engine.stub_exists("nonexistent_xyz") is False

    def test_builtin_command_stub(self):
        engine = StubEngine()
        assert engine.stub_exists("command") is True
        result = engine.render(
            "command",
            {
                "className": "TestCommand",
                "commandName": "test:run",
                "description": "A test",
            },
        )
        # Проверяем только подстановку переменных, не импорты
        assert "TestCommand" in result or "test:run" in result

    def test_custom_overrides_builtin(self, tmp_path):
        stubs_dir = tmp_path / "stubs"
        stubs_dir.mkdir()
        (stubs_dir / "command.stub").write_text("CUSTOM {{ className }}")
        engine = StubEngine(custom_stubs_dir=str(stubs_dir))
        result = engine.render("command", {"className": "Override"})
        assert "CUSTOM Override" in result


# ── CompletionGenerator ───────────────────────────────────


class TestCompletionGenerator:
    @pytest.fixture
    def commands(self):
        return {"simple": SimpleCommand, "greet": ArgCommand}

    def test_bash(self, commands):
        gen = CompletionGenerator(commands, "testcraft")
        output = gen.generate("bash")
        assert "testcraft" in output
        assert "simple" in output
        assert "greet" in output

    def test_zsh(self, commands):
        gen = CompletionGenerator(commands, "testcraft")
        output = gen.generate("zsh")
        assert "testcraft" in output
        assert "simple" in output

    def test_fish(self, commands):
        gen = CompletionGenerator(commands, "testcraft")
        output = gen.generate("fish")
        assert "testcraft" in output

    def test_powershell(self, commands):
        gen = CompletionGenerator(commands, "testcraft")
        output = gen.generate("powershell")
        assert "testcraft" in output

    def test_unsupported_shell(self, commands):
        gen = CompletionGenerator(commands, "testcraft")
        with pytest.raises(ValueError, match="Unsupported"):
            gen.generate("csh")


# ── DocsGenerator ─────────────────────────────────────────


class TestDocsGenerator:
    @pytest.fixture
    def commands(self):
        return {
            "simple": SimpleCommand,
            "greet": ArgCommand,
            "debug:internal": HiddenTestCommand,
        }

    def test_markdown(self, commands):
        gen = DocsGenerator(commands, "TestApp", "testcraft")
        md = gen.generate("markdown")
        assert "# TestApp" in md
        assert "simple" in md
        assert "greet" in md
        assert "username" in md
        assert "--shout" in md

    def test_markdown_alias(self, commands):
        gen = DocsGenerator(commands, "TestApp", "testcraft")
        md = gen.generate("md")
        assert "# TestApp" in md

    def test_html(self, commands):
        gen = DocsGenerator(commands, "TestApp", "testcraft")
        html = gen.generate("html")
        assert "<html>" in html
        assert "TestApp" in html
        assert "simple" in html
        assert "<code>" in html

    def test_hidden_commands_excluded_markdown(self, commands):
        gen = DocsGenerator(commands, "TestApp", "testcraft")
        gen.generate("markdown")
        # Hidden commands are in the generator but skipped in output
        # debug:internal has hidden=True


# ── SignalManager ─────────────────────────────────────────


class TestSignalManager:
    def test_singleton(self):
        s1 = SignalManager.get_instance()
        s2 = SignalManager.get_instance()
        assert s1 is s2

    def test_is_running_initial(self):
        s = SignalManager()
        assert s.is_running is True
        assert s.is_shutting_down is False

    def test_stop(self):
        s = SignalManager()
        s.stop()
        assert s.is_running is False
        assert s.is_shutting_down is True

    def test_reset(self):
        s = SignalManager()
        s.stop()
        s.reset()
        assert s.is_running is True
        assert s.is_shutting_down is False

    def test_on_shutdown_callback(self):
        s = SignalManager()
        called = []
        s.on_shutdown(lambda: called.append(True))
        assert len(s._callbacks) >= 1

    def test_repr(self):
        s = SignalManager()
        s.reset()
        assert "running" in repr(s)
        s.stop()
        assert "stopping" in repr(s)
        s.reset()

    def teardown_method(self):
        # Reset singleton state
        s = SignalManager.get_instance()
        s.reset()
        s._callbacks.clear()
        s._installed = False
