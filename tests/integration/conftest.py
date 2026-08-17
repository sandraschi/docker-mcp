"""Integration tests require a live Docker daemon + monitoring stack.

Skip the whole directory unless explicitly enabled, so the default `pytest`
run is hermetic (unit tests only). Enable with: RUN_INTEGRATION=1
"""

import os

import pytest

if os.getenv("RUN_INTEGRATION") != "1":
    pytest.skip("Integration tests need a live Docker + monitoring stack (set RUN_INTEGRATION=1)", allow_module_level=True)
