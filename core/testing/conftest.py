from __future__ import annotations

import pytest


@pytest.fixture
def app():
    """Fresh Application instance."""
    from core.foundation.application import Application

    return Application()


@pytest.fixture
def tmp_env(tmp_path):
    """Temporary directory for env/config files."""
    return tmp_path
