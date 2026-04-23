from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .command import Command
from .input import ArgvInput
from .output import ConsoleOutput

if TYPE_CHECKING:
    from .console_application import ConsoleApplication


class CommandResult:
    def __init__(self, exit_code: int, output: str, command_name: str = "") -> None:
        self.exit_code = exit_code
        self.output = output
        self.command_name = command_name

    @property
    def was_successful(self) -> bool:
        return self.exit_code == Command.SUCCESS

    @property
    def was_failure(self) -> bool:
        return self.exit_code != Command.SUCCESS

    def assert_successful(self) -> CommandResult:
        assert self.exit_code == Command.SUCCESS, (
            f"Command '{self.command_name}' failed with code {self.exit_code}.\n Output: {self.output}"
        )
        return self

    def assert_failed(self) -> CommandResult:
        assert self.exit_code != Command.SUCCESS, (
            f"Command '{self.command_name}' was expected to fail but succeeded.\n Output: {self.output}"
        )
        return self

    def assert_exit_code(self, code: int) -> CommandResult:
        assert self.exit_code == code, f"Expected exit code {code}, got {self.exit_code}.\n Output: {self.output}"
        return self

    def assert_output_contains(self, text: str) -> CommandResult:
        assert text in self.output, f"Expected output to contain '{text}'.\n Actual: {self.output}"
        return self

    def assert_output_not_contains(self, text: str) -> CommandResult:
        assert text not in self.output, f"Expected output NOT to contain '{text}'.\n Actual: {self.output}"
        return self

    def assert_output_empty(self) -> CommandResult:
        stripped = self.output.strip()
        assert not stripped, f"Expected empty output, got: {stripped}"
        return self

    def __repr__(self) -> str:
        status = "OK" if self.was_successful else f"FAIL({self.exit_code})"
        return f"<CommandResult {self.command_name} {status}>"


class ConsoleTester:
    def __init__(self, app: ConsoleApplication | None = None, container: Any = None) -> None:
        self._app = app
        self._container = container

    async def call(
        self,
        command: str | type[Command],
        arguments: list[str] | None = None,
        options: dict[str, Any] | None = None,
        interactive: bool = False,
    ) -> CommandResult:
        argv = self._build_argv(command, arguments, options)
        input_ = ArgvInput(argv)
        output = ConsoleOutput(quiet=True)
        output.start_buffering()

        if self._app:
            name = input_.command
            cmd_cls = self._app.kernel.find(name)
            if not cmd_cls:
                return CommandResult(exit_code=Command.FAILURE, output=f"Command '{name}' not found", command_name=name)

            if self._container:
                try:
                    cmd_instance = await self._container.make(cmd_cls)
                except Exception:
                    cmd_instance = cmd_cls()
            else:
                cmd_instance = cmd_cls()
            cmd_instance.setup(input_, output, self._app)

            errors = cmd_instance.validate()
            if errors:
                return CommandResult(exit_code=Command.INVALID, output="\n".join(errors), command_name=name)

            try:
                exit_code = await cmd_instance.handle()
                exit_code = exit_code if isinstance(exit_code, int) else Command.SUCCESS
            except Exception as e:
                exit_code = Command.FAILURE
                output.error(str(e))
        else:
            if isinstance(command, type) and issubclass(command, Command):
                cmd_instance = command()
                cmd_instance.setup(input_, output, None)
                errors = cmd_instance.validate()

                if errors:
                    return CommandResult(exit_code=Command.INVALID, output="\n".join(errors), command_name=command.name)

                try:
                    exit_code = await cmd_instance.handle()
                    exit_code = exit_code if isinstance(exit_code, int) else Command.SUCCESS
                except Exception as e:
                    exit_code = Command.FAILURE
                    output.error(str(e))
            else:
                return CommandResult(
                    exit_code=Command.FAILURE, output="No app or command class provided", command_name=str(command)
                )
        buffered = output.stop_buffering()
        cmd_name = command if isinstance(command, str) else getattr(command, "name", str(command))
        return CommandResult(exit_code=exit_code, output=buffered, command_name=cmd_name)

    @staticmethod
    def _build_argv(
        command: str | type[Command], arguments: list[str] | None = None, options: dict[str, Any] | None = None
    ) -> list[str]:
        parts: list[str] = []

        if isinstance(command, str):
            parts.extend(command.split())
        elif hasattr(command, "name"):
            parts.append(command.name)

        if arguments:
            parts.extend(arguments)

        if options:
            for key, value in options.items():
                flag = key.lstrip("-")
                if isinstance(value, bool):
                    if value:
                        parts.append(f"--{flag}")
                else:
                    parts.append(f"--{flag}={value}")

        return parts
