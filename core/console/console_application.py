from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import TYPE_CHECKING, Any

from ..exceptions import (
    CommandLockException,
    CommandNotFoundException,
    CommandTimeoutException,
    CommandValidationException,
    EnvironmentGuardException,
)
from .command import Command
from .completion import CompletionGenerator
from .docs_generator import DocsGenerator
from .events import (
    CommandFailed,
    CommandFinished,
    CommandSkipped,
    CommandStarting,
    EventDispatcher,
)
from .input import ArgvInput, Verbosity
from .kernel import ConsoleKernel
from .lock import CommandLock
from .middleware import MiddlewarePipeline
from .output import ConsoleOutput
from .profiler import CommandProfiler
from .signals import SignalManager

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class ConsoleApplication:
    def __init__(
        self,
        name: str = "AioFast",
        version: str = "1.0.0",
        kernel: ConsoleKernel | None = None,
        container: Any = None,
        binary: str = "aiocraft",
        locks_dir: str = "storage/locks",
    ) -> None:
        self._name = name
        self._version = version
        self._kernel = kernel or ConsoleKernel()
        self._container = container
        self._binary = binary
        self._output = ConsoleOutput()
        self._lock_manager = CommandLock(locks_dir)
        self._signal_manager = SignalManager.get_instance()
        self._before_callbacks: list[Callable] = []
        self._after_callbacks: list[Callable] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def kernel(self) -> ConsoleKernel:
        return self._kernel

    @property
    def events(self) -> EventDispatcher:
        return self._kernel.events

    @property
    def container(self) -> Any:
        return self._container

    # ── Run ───────────────────────────────────────────────

    async def run(self, argv: list[str] | None = None) -> int:
        input_ = ArgvInput(argv)
        self._output.verbosity = input_.verbosity
        self._signal_manager.install()
        await self._kernel.bootstrap()
        cmd = input_.command

        if not cmd or cmd in ("--help", "-h"):
            return await self._show_list()
        if cmd in ("--version", "-V"):
            self._output.line(f"[bold]{self._name}[/bold] version [green]{self._version}[/green]")
            return 0
        if cmd == "completion":
            return await self._handle_completion(input_)
        if cmd == "help":
            return await self._handle_help(input_)

        return await self._run_command(cmd, input_)

    async def call(self, command_name: str, quiet: bool = False, **kwargs: Any) -> int:
        argv_parts = [command_name]
        for key, value in kwargs.items():
            flag = key.replace("_", "-")
            if isinstance(value, bool):
                if value:
                    argv_parts.append(f"--{flag}")
            else:
                argv_parts.append(f"--{flag}={value}")
        input_ = ArgvInput(argv_parts)
        output = ConsoleOutput(quiet=quiet)

        cmd_cls = self._kernel.find(command_name)
        if not cmd_cls:
            raise CommandNotFoundException(command_name)
        command = await self._resolve_command(cmd_cls)
        command.setup(input_, output, self)
        errors = command.validate()

        if errors:
            for err in errors:
                output.error(err)
            return Command.INVALID
        return await self._execute_lifecycle(command)

    # ── Internal Execution ────────────────────────────────

    async def _run_command(self, name: str, input_: ArgvInput) -> int:
        cmd_cls = self._kernel.find(name)
        if not cmd_cls:
            self._output.error(f"Command '{name}' not found")
            self._suggest_command(name)
            return Command.FAILURE

        try:
            # Environment guard
            allowed_envs = getattr(cmd_cls, "_allowed_environments", None)
            if allowed_envs:
                current_env = os.getenv("APP_ENV", "local")
                if current_env not in allowed_envs:
                    raise EnvironmentGuardException(name, current_env, allowed_envs)
            # Profile flag
            do_profile = input_.has_option("profile")
            profiler = None

            if do_profile:
                profiler = CommandProfiler()
                profiler.start(name)

            # Resolve
            if cmd_cls.isolated:
                command = cmd_cls()
            else:
                command = await self._resolve_command(cmd_cls)
            command.setup(input_, self._output, self)

            # Validate
            errors = command.validate()
            if errors:
                raise CommandValidationException(name, errors)

            # Production guard
            if command.production_guard and not command.confirm_production():
                self._output.comment("Command cancelled")
                await self._kernel.events.dispatch(CommandSkipped(name, "production guard"))
                return Command.FAILURE
            # Dspatch starting event
            await self._kernel.events.dispatch(CommandStarting(command, input_))

            for cb in self._before_callbacks:
                cb(command)
            # Execute with middleware → lifecycle
            exit_code = await self._execute_with_middleware(command)

            for cb in self._after_callbacks:
                cb(command, exit_code)
            # Dispatch finished event
            elapsed = time.perf_counter() - command._start_time if command._start_time else 0
            await self._kernel.events.dispatch(CommandFinished(command, exit_code, elapsed))

            # Profile output
            if profiler:
                result = profiler.stop()
                result.render(self._output)

            return exit_code

        except CommandValidationException as e:
            for err in e.errors:
                self._output.error(err)
            return Command.INVALID
        except EnvironmentGuardException as e:
            self._output.error(str(e))
            return Command.FAILURE
        except CommandLockException as e:
            self._output.error(str(e))
            return Command.FAILURE
        except KeyboardInterrupt:
            self._output.newline()
            self._output.comment("Interrupted")
            return 130
        except Exception as e:
            await self._kernel.events.dispatch(
                CommandFailed(command if "command" in dir() else Command.__new__(Command), e)
            )
            self._output.error(str(e))
            if self._output.verbosity.value >= Verbosity.VERBOSE.value:
                self._output.console.print_exception()
            return Command.FAILURE

    async def _resolve_command(self, cmd_cls: type[Command]) -> Command:
        if self._container is not None:
            try:
                return await self._container.make(cmd_cls)
            except Exception:
                pass
        return cmd_cls()

    async def _execute_with_middleware(self, command: Command) -> int:
        middlewares = list(self._kernel.global_middleware)

        for mw_ref in getattr(command, "middleware", []):
            if isinstance(mw_ref, type):
                if self._container:
                    try:
                        mw = await self._container.make(mw_ref)
                    except Exception:
                        mw = mw_ref()
                else:
                    mw = mw_ref()
                middlewares.append(mw)
            else:
                middlewares.append(mw_ref)

        if middlewares:
            pipeline = MiddlewarePipeline(middlewares)
            return await pipeline.run(command, self._execute_lifecycle)
        return await self._execute_lifecycle(command)

    async def _execute_lifecycle(self, command: Command) -> int:
        command._start_time = time.perf_counter()

        # Lock
        lock_acquired = False
        if command.lock:
            lock_key = self._resolve_lock_key(command)
            lock_timeout = getattr(command, "_lock_timeout", 0)
            lock_acquired = await self._lock_manager.acquire(lock_key, timeout=lock_timeout)
            if not lock_acquired:
                raise CommandLockException(command.name)

        try:
            # Before hook
            should_continue = await command.before()
            if not should_continue:
                command.comment("Command aborted by before() hook")
                return Command.FAILURE

            # Handle with DI + timeout + retry
            exit_code = await self._execute_handle(command)

            # Success / Failure hooks
            if exit_code == Command.SUCCESS:
                await command.on_success()
            else:
                await command.on_failure(exit_code)

            return exit_code

        except Exception as e:
            try:
                exit_code = await command.on_error(e)
                return exit_code if isinstance(exit_code, int) else Command.FAILURE
            except Exception:
                raise

        finally:
            # After hook — always runs
            elapsed = time.perf_counter() - command._start_time
            try:
                await command.after(exit_code if "exit_code" in dir() else Command.FAILURE)
            except Exception as after_err:
                logger.warning("after() hook error: %s", after_err)

            # Release lock
            if lock_acquired:
                await self._lock_manager.release(self._resolve_lock_key(command))

            # Log execution
            if getattr(command, "_log_execution", False):
                elapsed = time.perf_counter() - command._start_time
                logger.info(
                    "Command %s finished in %.3fs (exit=%d)",
                    command.name,
                    elapsed,
                    exit_code if "exit_code" in dir() else -1,
                )

    async def _execute_handle(self, command: Command) -> int:
        timeout_seconds = getattr(command, "_timeout_seconds", 0)
        retry_times = getattr(command, "_retry_times", 0)
        retry_delay = getattr(command, "_retry_delay", 1.0)
        retry_exceptions = getattr(command, "_retry_exceptions", (Exception,))

        async def _invoke() -> int:
            # DI into handle() — resolve parameters from container
            if self._container is not None:
                result = await self._container.call(command.handle)
            else:
                result = await command.handle()
            return result if isinstance(result, int) else Command.SUCCESS

        async def _invoke_with_timeout() -> int:
            if timeout_seconds > 0:
                try:
                    return await asyncio.wait_for(_invoke(), timeout=timeout_seconds)
                except asyncio.TimeoutError:
                    raise CommandTimeoutException(command.name, timeout_seconds)
            return await _invoke()

        if retry_times > 0:
            last_error = None
            for attempt in range(1, retry_times + 1):
                try:
                    return await _invoke_with_timeout()
                except retry_exceptions as e:
                    last_error = e
                    if attempt < retry_times:
                        command.warn(f"Attempt {attempt}/{retry_times} failed: {e}. Retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
            command.error(f"All {retry_times} attempts failed")
            raise last_error  # ty:ignore[invalid-raise]
        else:
            return await _invoke_with_timeout()

    def _resolve_lock_key(self, command: Command) -> str:
        key = getattr(command, "_lock_key", "") or command.name
        # Interpolate argument values: "import:{store}" → "import:redis"
        for name, value in command.all_arguments().items():
            key = key.replace(f"{{{name}}}", str(value or ""))
        for name, value in command.all_options().items():
            key = key.replace(f"{{{name}}}", str(value or ""))
        return key

    # ── List / Help / Completion / Docs ───────────────────

    async def _show_list(self) -> int:
        o = self._output
        o.newline()
        o.line(f"  [bold green]{self._name}[/bold green] [dim]{self._version}[/dim]")
        o.newline()
        o.line("[bold]Usage:[/bold]")
        o.line(f"  {self._binary} <command> [arguments] [options]")
        o.newline()
        o.line("[bold]Global Options:[/bold]")
        o.line("  [green]--help, -h[/green]              Show help")
        o.line("  [green]--version, -V[/green]           Show version")
        o.line("  [green]--quiet[/green]                 Suppress output")
        o.line("  [green]-v|-vv|-vvv[/green]             Verbosity level")
        o.line("  [green]--no-interaction[/green]        Disable prompts")
        o.line("  [green]--format=FORMAT[/green]         Output format (table|json|csv|plain|yaml|xml)")
        o.line("  [green]--profile[/green]               Show execution profile")
        o.newline()
        o.line("[bold]Available commands:[/bold]")
        grouped = self._kernel.grouped()

        if "" in grouped:
            for cmd_cls in grouped[""]:
                if not cmd_cls.hidden:
                    desc = cmd_cls.description or ""
                    o.line(f"  [green]{cmd_cls.name:<24}[/green] {desc}")

        for group_name in sorted(k for k in grouped if k):
            o.newline()
            o.line(f" [bold yellow]{group_name}[/bold yellow]")
            for cmd_cls in grouped[group_name]:
                if not cmd_cls.hidden:
                    desc = cmd_cls.description or ""
                    o.line(f"  [green]{cmd_cls.name:<24}[/green] {desc}")

        o.newline()
        return 0

    async def _handle_help(self, input_: ArgvInput) -> int:
        if not input_.arguments:
            return await self._show_list()
        cmd_name = input_.arguments[0]
        cmd_cls = self._kernel.find(cmd_name)
        if not cmd_cls:
            self._output.error(f"Command '{cmd_name}' not found")
            return Command.FAILURE
        cmd = await self._resolve_command(cmd_cls)
        cmd.setup(input_, self._output, self)
        self._output.newline()
        self._output.console.print(cmd.get_help())
        self._output.newline()
        return 0

    async def _handle_completion(self, input_: ArgvInput) -> int:
        shell = input_.arguments[0] if input_.arguments else "bash"
        gen = CompletionGenerator(self._kernel.all(), self._binary)
        try:
            self._output.line(gen.generate(shell))
            return 0
        except ValueError as e:
            self._output.error(str(e))
            return Command.FAILURE

    def generate_docs(self, fmt: str = "markdown") -> str:
        gen = DocsGenerator(self._kernel.all(), self._name, self._binary)
        return gen.generate(fmt)

    def _suggest_command(self, name: str) -> None:
        all_names = self._kernel.loader.names()
        suggestions = [n for n in all_names if name in n or n.startswith(name[:3])]
        if suggestions:
            self._output.newline()
            self._output.line("[dim]Did you mean?[/dim]")
            for s in suggestions[:5]:
                self._output.line(f"  [green]{s}[/green]")

    # ── Hooks ─────────────────────────────────────────────

    def before_command(self, callback: Callable) -> ConsoleApplication:
        self._before_callbacks.append(callback)
        return self

    def after_command(self, callback: Callable) -> ConsoleApplication:
        self._after_callbacks.append(callback)
        return self

    def on(self, event_type: type, callback: Callable) -> ConsoleApplication:
        self._kernel.events.listen(event_type, callback)
        return self

    def __repr__(self) -> str:
        return f"<ConsoleApplication {self._name} v{self._version}>"
