from __future__ import annotations

import logging

from loguru import logger as loguru_logger

from core.log import LoguruInterceptor


class TestInterceptor:
    def test_intercept_root(self, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")
        LoguruInterceptor.setup()
        stdlib_logger = logging.getLogger("test_module")
        stdlib_logger.info("from stdlib")
        assert any("from stdlib" in msg for msg in sink_capture["messages"])

    def test_intercept_specific_module(self, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{message}")
        LoguruInterceptor.setup(modules=["my_lib"])
        my_logger = logging.getLogger("my_lib")
        my_logger.warning("my lib warning")
        assert any("my lib warning" in msg for msg in sink_capture["messages"])

    def test_setup_common(self):
        # Should not raise
        LoguruInterceptor.setup_common()

    def test_level_mapping(self, capture_sink, sink_capture):
        loguru_logger.add(capture_sink, level="DEBUG", format="{level.name}: {message}")
        LoguruInterceptor.setup()
        stdlib_logger = logging.getLogger("level_test")
        stdlib_logger.error("error message")
        assert any("ERROR" in msg for msg in sink_capture["messages"])
