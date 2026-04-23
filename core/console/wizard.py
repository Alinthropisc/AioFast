from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from .output import ConsoleOutput


class WizardStep:
    def __init__(self, name: str, callback: Callable) -> None:
        self.name = name
        self.callback = callback


class WizardContext:
    def __init__(self, output: ConsoleOutput) -> None:
        self._output = output

    def ask(self, question: str, default: str = "") -> str:
        return self._output.ask(question, default)

    def secret(self, question: str) -> str:
        return self._output.secret(question)

    def confirm(self, question: str, default: bool = False) -> bool:
        return self._output.confirm(question, default)

    def choice(self, question: str, choices: list[str], default: str = "") -> str:
        return self._output.choice(question, choices, default)

    def info(self, message: str) -> None:
        self._output.info(message)

    def success(self, message: str) -> None:
        self._output.success(message)


class Wizard:
    def __init__(self, title: str, output: ConsoleOutput) -> None:
        self._title = title
        self._output = output
        self._steps: list[WizardStep] = []
        self._results: dict[str, Any] = {}

    def step(self, name: str, callback: Callable) -> Wizard:
        self._steps.append(WizardStep(name, callback))
        return self

    async def run(self) -> dict[str, Any]:
        self._output.panel(self._title, title="Wizard", style="blue")
        self._output.newline()
        ctx = WizardContext(self._output)

        for i, step in enumerate(self._steps, 1):
            self._output.line(f"[bold cyan]Step {i}/{len(self._steps)}:[/bold cyan] [bold]{step.name}[/bold]")
            self._output.rule()
            result = step.callback(ctx)

            if inspect.isawaitable(result):
                result = await result
            self._results[step.name] = result
            self._output.success(f"Step '{step.name}' completed")
            self._output.newline()
        self._output.success("Wizard completed!")
        return dict(self._results)

    @property
    def results(self) -> dict[str, Any]:
        return dict(self._results)
