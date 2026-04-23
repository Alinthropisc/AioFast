from __future__ import annotations

import sys
import time
import tracemalloc
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .output import ConsoleOutput


@dataclass
class ProfileResult:
    elapsed: float = 0.0
    memory_start: int = 0
    memory_peak: int = 0
    memory_current: int = 0
    command_name: str = ""

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed * 1000

    @property
    def memory_peak_mb(self) -> float:
        return self.memory_peak / (1024 * 1024)

    @property
    def memory_diff_mb(self) -> float:
        return (self.memory_current - self.memory_start) / (1024 * 1024)

    def render(self, output: ConsoleOutput) -> None:
        output.newline()
        output.table(
            ["Metric", "Value"],
            [
                ["Command", self.command_name],
                ["Total time", f"{self.elapsed:.3f}s ({self.elapsed_ms:.1f}ms)"],
                ["Memory peak", f"{self.memory_peak_mb:.2f} MB"],
                ["Memory diff", f"{self.memory_diff_mb:+.2f} MB"],
                ["Python", sys.version.split()[0]],
            ],
            title="Command Profile",
        )


class CommandProfiler:
    def __init__(self) -> None:
        self._start_time: float = 0
        self._start_mem: int = 0
        self._tracking = False

    def start(self, command_name: str = "") -> None:
        self._command_name = command_name
        self._start_time = time.perf_counter()

        if not tracemalloc.is_tracing():
            tracemalloc.start()
            self._tracking = True
        snapshot = tracemalloc.take_snapshot()
        stats = snapshot.statistics("filename")
        self._start_mem = sum(s.size for s in stats)

    def stop(self) -> ProfileResult:
        elapsed = time.perf_counter() - self._start_time
        current, peak = tracemalloc.get_traced_memory()
        result = ProfileResult(
            elapsed=elapsed,
            memory_start=self._start_mem,
            memory_peak=peak,
            memory_current=current,
            command_name=self._command_name,
        )

        if self._tracking:
            tracemalloc.stop()
            self._tracking = False

        return result
