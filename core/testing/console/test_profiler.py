import time

from core.console.output import ConsoleOutput
from core.console.profiler import CommandProfiler, ProfileResult


class TestCommandProfiler:
    def test_start_stop(self):
        p = CommandProfiler()
        p.start("test:cmd")
        time.sleep(0.05)
        result = p.stop()
        assert result.elapsed >= 0.04
        assert result.command_name == "test:cmd"

    def test_elapsed_ms(self):
        result = ProfileResult(elapsed=1.5, command_name="test")
        assert result.elapsed_ms == 1500.0

    def test_memory_peak_mb(self):
        result = ProfileResult(memory_peak=10 * 1024 * 1024)
        assert abs(result.memory_peak_mb - 10.0) < 0.01

    def test_memory_diff_mb(self):
        result = ProfileResult(
            memory_start=5 * 1024 * 1024,
            memory_current=8 * 1024 * 1024,
        )
        assert abs(result.memory_diff_mb - 3.0) < 0.01

    def test_render_does_not_crash(self):
        result = ProfileResult(
            elapsed=0.5,
            memory_peak=1024 * 1024,
            memory_current=1024 * 1024,
            memory_start=512 * 1024,
            command_name="test",
        )
        out = ConsoleOutput(quiet=True)
        out.start_buffering()
        result.render(out)
        output = out.stop_buffering()
        assert "test" in output
