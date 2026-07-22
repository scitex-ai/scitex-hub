#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Security regression tests.

Every module here reproduces a CONFIRMED security finding as an executable
exploit and asserts the exploit is now BLOCKED. Tests carry
``@pytest.mark.security`` so the suite is greppable and can be run alone::

    pytest tests/security -m security

A gate that cannot fail is not a gate: each test in this package must FAIL
when the corresponding fix is reverted.
"""

# EOF
