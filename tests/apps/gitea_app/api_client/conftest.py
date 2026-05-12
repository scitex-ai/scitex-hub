"""Skip the gitea_app/api_client/ tests when ``requests`` is missing.

Each ``test_*.py`` under this directory does ``import requests`` at the
module top — without an importorskip hoist, collection aborts on
minimal envs (PA-303).
"""

import pytest

pytest.importorskip(
    "requests",
    reason="requests not installed — gitea_app/api_client tests skipped",
)
