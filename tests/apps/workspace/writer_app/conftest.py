#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Writer cutover fixtures (CCT 2763/2764 + CCT 2806).

Re-exports the shared dev-gate helper so tests in this directory can take
``writer_old_direct`` as a fixture argument. The helper itself lives in
``_old_direct_gate.py`` (underscore-prefixed, so pytest never collects it)
because Django ``TestCase`` modules import the ``writer_old_direct_urls``
context manager from the same definition — one gate, documented once.
"""

from __future__ import annotations

from ._old_direct_gate import (
    WRITER_OLD_DIRECT_FLAG,
    writer_old_direct,
    writer_old_direct_urls,
)

__all__ = [
    "WRITER_OLD_DIRECT_FLAG",
    "writer_old_direct",
    "writer_old_direct_urls",
]


# EOF
