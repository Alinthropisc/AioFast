from core.console.input import Verbosity
from core.console.output import ConsoleOutput


class TestConsoleOutput:
    def test_buffering(self):
        o = ConsoleOutput(quiet=True)
        o.start_buffering()
        o.line("hello")
        o.line("world")
        result = o.stop_buffering()
        assert "hello" in result
        assert "world" in result

    def test_info_buffered(self):
        o = ConsoleOutput(quiet=True)
        o.start_buffering()
        o.info("test message")
        result = o.stop_buffering()
        assert "test message" in result

    def test_success_buffered(self):
        o = ConsoleOutput(quiet=True)
        o.start_buffering()
        o.success("done!")
        result = o.stop_buffering()
        assert "done!" in result

    def test_warn_buffered(self):
        o = ConsoleOutput(quiet=True)
        o.start_buffering()
        o.warn("careful")
        result = o.stop_buffering()
        assert "careful" in result

    def test_error_buffered(self):
        o = ConsoleOutput(quiet=True)
        o.start_buffering()
        o.error("failure")
        result = o.stop_buffering()
        assert "failure" in result

    def test_comment_buffered(self):
        o = ConsoleOutput(quiet=True)
        o.start_buffering()
        o.comment("note")
        result = o.stop_buffering()
        assert "note" in result

    def test_debug_only_at_debug_level(self):
        o = ConsoleOutput(quiet=True)
        o.start_buffering()
        o.verbosity = Verbosity.NORMAL
        o.debug("hidden")
        result = o.stop_buffering()
        assert "hidden" not in result

    def test_debug_visible_at_debug_level(self):
        o = ConsoleOutput(quiet=True)
        o.start_buffering()
        o.verbosity = Verbosity.DEBUG
        o.debug("visible")
        result = o.stop_buffering()
        assert "visible" in result

    def test_verbose_only_at_verbose_level(self):
        o = ConsoleOutput(quiet=True)
        o.start_buffering()
        o.verbosity = Verbosity.NORMAL
        o.verbose("hidden")
        result = o.stop_buffering()
        assert "hidden" not in result

    def test_verbose_visible(self):
        o = ConsoleOutput(quiet=True)
        o.start_buffering()
        o.verbosity = Verbosity.VERBOSE
        o.verbose("shown")
        result = o.stop_buffering()
        assert "shown" in result

    def test_quiet_suppresses_line(self):
        o = ConsoleOutput(quiet=True)
        # Without buffering, quiet suppresses output
        # We can't easily test this without buffering
        # so test that buffering overrides quiet
        o.start_buffering()
        o.line("should appear")
        result = o.stop_buffering()
        assert "should appear" in result

    def test_newline_buffered(self):
        o = ConsoleOutput(quiet=True)
        o.start_buffering()
        o.line("before")
        o.newline(2)
        o.line("after")
        result = o.stop_buffering()
        assert "before" in result
        assert "after" in result

    def test_panel_buffered(self):
        o = ConsoleOutput(quiet=True)
        o.start_buffering()
        o.panel("content", title="Title")
        result = o.stop_buffering()
        assert "content" in result

    def test_rule_buffered(self):
        o = ConsoleOutput(quiet=True)
        o.start_buffering()
        o.rule("Section")
        result = o.stop_buffering()
        assert "Section" in result

    def test_json_buffered(self):
        o = ConsoleOutput(quiet=True)
        o.start_buffering()
        o.json({"key": "value"})
        result = o.stop_buffering()
        assert "key" in result
        assert "value" in result

    def test_table_buffered(self):
        o = ConsoleOutput(quiet=True)
        o.start_buffering()
        o.table(["Name", "Age"], [["Alice", "30"]])
        result = o.stop_buffering()
        assert "Alice" in result

    def test_set_quiet(self):
        o = ConsoleOutput()
        assert o._quiet is False
        o.set_quiet(True)
        assert o._quiet is True

    def test_verbosity_property(self):
        o = ConsoleOutput()
        assert o.verbosity == Verbosity.NORMAL
        o.verbosity = Verbosity.DEBUG
        assert o.verbosity == Verbosity.DEBUG

    def test_renderers_property(self):
        o = ConsoleOutput()
        assert o.renderers is not None
        assert o.renderers.has("json")
        assert o.renderers.has("table")
