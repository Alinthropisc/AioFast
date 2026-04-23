from __future__ import annotations

from core.log import LogContext, context_patcher


class TestLogContextPush:
    def test_push_adds_data(self):
        LogContext.push(request_id="abc")
        ctx = LogContext.get()
        assert ctx["request_id"] == "abc"

    def test_push_merges(self):
        LogContext.push(a=1)
        LogContext.push(b=2)
        ctx = LogContext.get()
        assert ctx == {"a": 1, "b": 2}

    def test_push_overwrites(self):
        LogContext.push(a=1)
        LogContext.push(a=2)
        assert LogContext.get()["a"] == 2


class TestLogContextClear:
    def test_clear(self):
        LogContext.push(x=1, y=2)
        LogContext.clear()
        assert LogContext.get() == {}

    def test_forget_keys(self):
        LogContext.push(a=1, b=2, c=3)
        LogContext.forget("a", "c")
        ctx = LogContext.get()
        assert ctx == {"b": 2}

    def test_forget_nonexistent_key(self):
        LogContext.push(a=1)
        LogContext.forget("zzz")  # should not raise
        assert LogContext.get() == {"a": 1}


class TestLogContextManager:
    def test_context_manager_adds_data(self):
        with LogContext(user_id=42):
            ctx = LogContext.get()
            assert ctx["user_id"] == 42
        # After exit — restored
        assert "user_id" not in LogContext.get()

    def test_nested_context(self):
        with LogContext(a=1):
            assert LogContext.get() == {"a": 1}
            with LogContext(b=2):
                ctx = LogContext.get()
                assert ctx == {"a": 1, "b": 2}
            assert LogContext.get() == {"a": 1}
        assert LogContext.get() == {}

    def test_context_overwrite_restores(self):
        LogContext.push(x="original")
        with LogContext(x="override"):
            assert LogContext.get()["x"] == "override"
        assert LogContext.get()["x"] == "original"


class TestContextPatcher:
    def test_patcher_adds_context(self):
        LogContext.push(req="123")
        record = {"extra": {}}
        context_patcher(record)
        assert record["extra"]["context"] == {"req": "123"}
        assert "req='123'" in record["extra"]["context_str"]

    def test_patcher_empty_context(self):
        record = {"extra": {}}
        context_patcher(record)
        assert record["extra"]["context"] == {}
        assert record["extra"]["context_str"] == ""

    def test_patcher_multiple_keys(self):
        LogContext.push(a=1, b="two")
        record = {"extra": {}}
        context_patcher(record)
        assert record["extra"]["context"]["a"] == 1
        assert record["extra"]["context"]["b"] == "two"
        assert "a=1" in record["extra"]["context_str"]
        assert "b='two'" in record["extra"]["context_str"]
