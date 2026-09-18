#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reviewed library blocker: the media route advertised no range support.

A player seeking into a video, or a resuming download manager, was answered with the
whole file and no way to ask for less. These are the bounds rules the route now applies,
pinned as functions so the arithmetic is testable without a request.
"""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "apps" / "infra" / "public_app" / "demo_library.py"


def load_module():
    spec = importlib.util.spec_from_file_location("demo_library", MODULE_PATH)
    assert spec is not None and spec.loader is not None, MODULE_PATH
    module = importlib.util.module_from_spec(spec)
    sys.modules["demo_library"] = module
    spec.loader.exec_module(module)
    return module


library = load_module()
SIZE = 1000


def test_a_plain_range_is_honoured_inclusively():
    # Arrange / Act / Assert
    assert library.range_bounds("bytes=0-99", SIZE) == (0, 99)
    assert library.range_bounds("bytes=100-199", SIZE) == (100, 199)


def test_an_open_ended_range_runs_to_the_last_byte():
    # Arrange / Act / Assert
    assert library.range_bounds("bytes=900-", SIZE) == (900, 999)


def test_a_suffix_range_counts_back_from_the_end():
    # Arrange / Act / Assert
    assert library.range_bounds("bytes=-50", SIZE) == (950, 999)
    assert library.range_bounds("bytes=-5000", SIZE) == (0, 999)


def test_an_end_past_the_file_is_clamped_not_refused():
    # Arrange / Act / Assert
    assert library.range_bounds("bytes=0-999999", SIZE) == (0, 999)


def test_no_range_header_means_serve_the_whole_file():
    # Arrange / Act / Assert
    assert library.range_bounds("", SIZE) is None
    assert library.range_bounds(None, SIZE) is None


def test_a_range_that_cannot_be_satisfied_is_reported_as_such():
    # Arrange: each of these used to be answered with the whole file, silently.
    cases = [
        "bytes=1000-",            # starts at the first byte past the end
        "bytes=5000-6000",
        "bytes=abc-def",          # not a range at all
        "bytes=-0",               # a suffix of nothing
        "bytes=",                 # no bounds
        "bytes=199-100",          # end before start
        "items=0-10",             # the wrong unit
        "bytes=0-9,20-29",        # multipart: not something this route honours
        "bytes=-",                # both bounds omitted
    ]
    # Act / Assert
    for value in cases:
        assert library.range_bounds(value, SIZE) == "unsatisfiable", value


def test_an_empty_or_unknown_file_size_cannot_satisfy_anything():
    # Arrange / Act / Assert
    assert library.range_bounds("bytes=0-10", 0) == "unsatisfiable"
    assert library.range_bounds("bytes=0-10", -5) == "unsatisfiable"


def test_the_range_never_exceeds_the_file():
    # Arrange / Act: every answer must be inside the file, whatever was asked.
    for value in (f"bytes={start}-{end}" for start in range(0, 1100, 37)
                  for end in range(0, 1100, 53)):
        bounds = library.range_bounds(value, SIZE)
        if isinstance(bounds, tuple):
            start, end = bounds
            assert 0 <= start <= end <= SIZE - 1, value
