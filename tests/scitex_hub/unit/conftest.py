#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit test configuration - minimal setup without external dependencies.

Unit tests should be fast, isolated, and not require:
- Database connections
- Network access
- Django setup (unless testing Django-specific utilities)
"""

import pytest


@pytest.fixture
def sample_data():
    """Provide sample data for unit tests."""
    return {
        "numbers": [1, 2, 3, 4, 5],
        "text": "sample text for testing",
        "nested": {"key1": "value1", "key2": [1, 2, 3]},
    }


@pytest.fixture
def empty_data():
    """Provide empty data structures for edge case tests."""
    return {
        "empty_list": [],
        "empty_dict": {},
        "empty_string": "",
        "none": None,
    }
