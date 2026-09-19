#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/infra/llm_app/relay_groups.py
"""Single source of truth for the eval-js / ui-action relay group name.

WHY THIS EXISTS AS A SHARED HELPER RATHER THAN AN f-STRING IN THREE PLACES.

The group name is computed by a consumer and by two producers. All three must
agree exactly or delivery silently stops. Authenticated usernames are unique,
stable identities; anonymous sessions never join a relay group.
"""

from __future__ import annotations

_PREFIX = "eval_js"


def relay_group_for(user) -> str:
    """The channel-layer group carrying eval_js / ui_action for ``user``.

    MUST be the only place this name is built. Producers and the consumer have
    to agree exactly, and a mismatch is silent.
    """
    username = getattr(user, "username", "") or ""
    return f"{_PREFIX}_{username}"
