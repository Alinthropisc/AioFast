from __future__ import annotations

import time

from loguru import logger as loguru_logger

from core.log import BufferedChannel


class TestBufferedChannel:
    def test_collects_messages(self):
        flushed = []
        ch = BufferedChannel(
            "buf",
            {
                "level": "DEBUG",
                "buffer_size": 5,
                "flush_interval": 999,  # don't auto-flush
                "on_flush": lambda batch: flushed.extend(batch),
            },
        )
        ch.setup(loguru_logger)

        for i in range(3):
            loguru_logger.info(f"msg {i}")
        time.sleep(0.1)
        # Not flushed yet (under buffer_size)
        assert len(flushed) == 0

    # def test_auto_flush_on_size(self):
    #     flushed = []
    #     ch = BufferedChannel("buf", {
    #         "level": "DEBUG",
    #         "buffer_size": 3,
    #         "flush_interval": 999,
    #         "on_flush": lambda batch: flushed.extend(batch),
    #     })
    #     ch.setup(loguru_logger)

    #     for i in range(5):
    #         loguru_logger.info(f"msg {i}")
    #     time.sleep(0.1)
    #     assert len(flushed) >= 3

    def test_manual_flush(self):
        flushed = []

        ch = BufferedChannel(
            "buf",
            {
                "level": "DEBUG",
                "buffer_size": 100,
                "flush_interval": 999,
                "on_flush": lambda batch: flushed.extend(batch),
            },
        )
        ch.setup(loguru_logger)
        loguru_logger.info("manual flush test")
        time.sleep(0.1)
        ch.flush()
        assert len(flushed) > 0

    def test_teardown_flushes(self):
        flushed = []

        ch = BufferedChannel(
            "buf",
            {
                "level": "DEBUG",
                "buffer_size": 100,
                "flush_interval": 999,
                "on_flush": lambda batch: flushed.extend(batch),
            },
        )
        ch.setup(loguru_logger)
        loguru_logger.info("teardown msg")
        time.sleep(0.1)
        ch.teardown(loguru_logger)
        assert len(flushed) > 0

    def test_repr(self):
        ch = BufferedChannel(
            "buf",
            {
                "level": "DEBUG",
                "buffer_size": 50,
                "flush_interval": 5,
            },
        )
        assert "BufferedChannel" in repr(ch)
