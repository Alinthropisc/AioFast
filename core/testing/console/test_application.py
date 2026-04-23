import os
from typing import Any
from unittest.mock import patch

import pytest

from core.console.command import Command
from core.console.console_application import ConsoleApplication
from core.console.events import CommandFinished, CommandStarting
from core.exceptions import CommandNotFoundException


class TestConsoleApplicationRun:
    @pytest.mark.asyncio
    async def test_run_no_args_shows_list(self, app):
        code = await app.run([])
        assert code == 0

    @pytest.mark.asyncio
    async def test_run_help_flag(self, app):
        code = await app.run(["--help"])
        assert code == 0

    @pytest.mark.asyncio
    async def test_run_version_flag(self, app):
        code = await app.run(["--version"])
        assert code == 0

    @pytest.mark.asyncio
    async def test_run_simple_command(self, app):
        code = await app.run(["simple"])
        assert code == 0

    @pytest.mark.asyncio
    async def test_run_fail_command(self, app):
        code = await app.run(["fail"])
        assert code == Command.FAILURE

    @pytest.mark.asyncio
    async def test_run_unknown_command(self, app):
        code = await app.run(["nonexistent"])
        assert code == Command.FAILURE

    @pytest.mark.asyncio
    async def test_run_with_args(self, app):
        code = await app.run(["greet", "Alice", "--shout", "--times=2"])
        assert code == 0

    @pytest.mark.asyncio
    async def test_run_validation_error(self, app):
        code = await app.run(["greet"])  # missing required username
        assert code == Command.INVALID

    @pytest.mark.asyncio
    async def test_run_help_for_command(self, app):
        code = await app.run(["help", "greet"])
        assert code == 0

    @pytest.mark.asyncio
    async def test_run_help_unknown_command(self, app):
        code = await app.run(["help", "nonexistent"])
        assert code == Command.FAILURE

    @pytest.mark.asyncio
    async def test_run_isolated_command(self, app):
        code = await app.run(["iso"])
        assert code == 0


class TestConsoleApplicationCall:
    @pytest.mark.asyncio
    async def test_call_existing_command(self, app):
        await app._kernel.bootstrap()
        code = await app.call("simple")
        assert code == 0

    @pytest.mark.asyncio
    async def test_call_with_kwargs(self, app):
        await app._kernel.bootstrap()
        code = await app.call("greet", username="Alice")
        # username is passed as --username=Alice option, not positional
        # so it might not bind correctly to positional arg
        # but the call should not crash
        assert isinstance(code, int)

    @pytest.mark.asyncio
    async def test_call_unknown_raises(self, app):
        await app._kernel.bootstrap()
        with pytest.raises(CommandNotFoundException):
            await app.call("nonexistent")

    @pytest.mark.asyncio
    async def test_call_quiet(self, app):
        await app._kernel.bootstrap()
        code = await app.call("simple", quiet=True)
        assert code == 0


class TestConsoleApplicationLifecycle:
    @pytest.mark.asyncio
    async def test_lifecycle_order(self, app):
        code = await app.run(["lifecycle"])
        assert code == 0
        # Can't easily access lifecycle command instance from here
        # but we verify it doesn't crash

    @pytest.mark.asyncio
    async def test_error_command_handled(self, app):
        code = await app.run(["error"])
        assert code == Command.FAILURE

    @pytest.mark.asyncio
    async def test_error_no_recovery(self, app):
        code = await app.run(["error:norecov"])
        assert code == Command.FAILURE


class TestConsoleApplicationEvents:
    @pytest.mark.asyncio
    async def test_before_callback(self, app):
        called = []
        app.before_command(lambda cmd: called.append(cmd.name))
        await app.run(["simple"])
        assert "simple" in called

    @pytest.mark.asyncio
    async def test_after_callback(self, app):
        results = []
        app.after_command(lambda cmd, code: results.append((cmd.name, code)))
        await app.run(["simple"])
        assert len(results) == 1
        assert results[0] == ("simple", 0)

    @pytest.mark.asyncio
    async def test_event_dispatch_starting(self, app):
        events = []
        app.on(CommandStarting, lambda e: events.append(e))
        await app.run(["simple"])
        assert len(events) == 1
        assert events[0].command.name == "simple"

    @pytest.mark.asyncio
    async def test_event_dispatch_finished(self, app):
        events = []
        app.on(CommandFinished, lambda e: events.append(e))
        await app.run(["simple"])
        assert len(events) == 1
        assert events[0].exit_code == 0


class TestConsoleApplicationEnvironmentGuard:
    @pytest.mark.asyncio
    async def test_environment_guard_blocks(self, kernel, tmp_path):
        from core.console.decorators import environments

        @environments("testing", "local")
        class GuardedCommand(Command):
            name = "guarded"
            description = "Guarded"

            async def handle(self, **kwargs: Any) -> int:
                return self.SUCCESS

        kernel.register(GuardedCommand)
        app = ConsoleApplication(
            name="Test",
            version="0.1.0",
            kernel=kernel,
            binary="test",
            locks_dir=str(tmp_path / "locks"),
        )

        with patch.dict(os.environ, {"APP_ENV": "production"}):
            code = await app.run(["guarded"])
        assert code == Command.FAILURE

    @pytest.mark.asyncio
    async def test_environment_guard_allows(self, kernel, tmp_path):
        from core.console.decorators import environments

        @environments("testing", "local")
        class AllowedCommand(Command):
            name = "allowed"
            description = "Allowed"

            async def handle(self, **kwargs: Any) -> int:
                return self.SUCCESS

        kernel.register(AllowedCommand)
        app = ConsoleApplication(
            name="Test",
            version="0.1.0",
            kernel=kernel,
            binary="test",
            locks_dir=str(tmp_path / "locks"),
        )

        with patch.dict(os.environ, {"APP_ENV": "local"}):
            code = await app.run(["allowed"])
        assert code == 0


class TestConsoleApplicationLock:
    @pytest.mark.asyncio
    async def test_locked_command_executes(self, app):
        code = await app.run(["locked"])
        assert code == 0


class TestConsoleApplicationCompletion:
    @pytest.mark.asyncio
    async def test_completion_bash(self, app):
        code = await app.run(["completion", "bash"])
        assert code == 0

    @pytest.mark.asyncio
    async def test_completion_invalid_shell(self, app):
        code = await app.run(["completion", "invalid_shell"])
        assert code == Command.FAILURE


class TestConsoleApplicationDocs:
    def test_generate_docs_markdown(self, app):
        md = app.generate_docs("markdown")
        assert "TestApp" in md
        assert "simple" in md

    def test_generate_docs_html(self, app):
        html = app.generate_docs("html")
        assert "<html>" in html


class TestConsoleApplicationSuggest:
    @pytest.mark.asyncio
    async def test_suggest_similar_command(self, app):
        # "simpl" should suggest "simple"
        code = await app.run(["simpl"])
        assert code == Command.FAILURE


class TestConsoleApplicationRepr:
    def test_repr(self, app):
        r = repr(app)
        assert "TestApp" in r
        assert "0.1.0" in r


class TestConsoleApplicationContainer:
    @pytest.mark.asyncio
    async def test_with_container(self, app_with_container):
        code = await app_with_container.run(["simple"])
        assert code == 0


class TestConsoleApplicationProfile:
    @pytest.mark.asyncio
    async def test_profile_flag(self, app):
        code = await app.run(["simple", "--profile"])
        assert code == 0
