"""E2E tests exercise behavior against the real environment.

These tests intentionally poke at Docker availability and reconnect
behavior. Skip them in the default hermetic run; enable with RUN_E2E=1.
"""

import os

import pytest

if os.getenv("RUN_E2E") != "1":
    pytest.skip("E2E tests manipulate the real Docker environment (set RUN_E2E=1)", allow_module_level=True)
