#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/infra/llm_app/relay_groups.py
"""Single source of truth for the eval-js / ui-action relay group name.

WHY THIS EXISTS AS A SHARED HELPER RATHER THAN AN f-STRING IN THREE PLACES.

The group name is computed by a CONSUMER (consumers.py, on connect) and by two
PRODUCERS (views/context.py `api_eval_js` and `api_ui_action`). All three must
agree exactly or delivery silently stops: `group_send` to a group nobody has
joined is NOT an error. Three copies of one f-string is three chances to drift
into a failure with no symptom.

WHAT WAS WRONG WITH THE OLD NAME.

It was `eval_js_{username}`, which is correct only if ONE USERNAME MEANS ONE
HUMAN. For the anonymous visitor pool it does not: `pool_manager.py:247` builds
the identity as ``f"{VISITOR_USER_PREFIX}{visitor_num:03d}"``, so ``visitor-007``
is a SEAT NUMBER recycled across people. A socket is discarded from its group
only on `disconnect` (consumers.py:39-41) and nothing in the slot-release path
closes one, while the channels default `group_expiry` is 86400s against a
30-minute idle release. So the previous occupant of a seat can still be joined
to the group named after it when a different person is handed that seat, and
that person's eval-js POST executes arbitrary JS in the previous occupant's
browser via `new Function()` (eval-js-relay.ts:24).

WHY THE LEASE AND NOT THE SESSION.

Keying on the Django session key looks equivalent and is not: the onsite MCP
producer authenticates through an HMAC header (`X-SciTeX-OnSite`) and has NO
session. A session-derived name would make it address a group no consumer has
joined -- and, again, that is silent. `VisitorAllocation.allocation_token`
(project_app/models/core.py:58) is per-LEASE, is reachable from a plain `User`
on both sides, and is simply ABSENT for non-visitor users, which is what keeps
their group name byte-identical to today.

    two sockets, DIFFERENT leases of one seat   ->  different groups (leak closed)
    two sockets, SAME lease (one human, tabs)   ->  same group      (feature kept)
    a user with NO lease (regular / onsite MCP) ->  unchanged        (onsite kept)

The middle line is not decoration. A "fix" that separated two sockets by
USERNAME would also stop delivering to a user's own second tab, and would look
correct while doing it.
"""

from __future__ import annotations

_PREFIX = "eval_js"


def _allocation_token_for(user) -> str | None:
    """Return the user's ACTIVE visitor lease token, or None if they have none.

    A pre-resolved ``user.allocation_token`` is honoured when present. That is
    the seam the relay tests drive, and it is also a legitimate fast path for a
    caller that already loaded the allocation -- the value is the same either
    way. A real Django ``User`` carries no such attribute, so production always
    falls through to the query below.

    Any lookup failure returns None rather than raising: this runs on the
    WebSocket connect path, and a database hiccup must not take the relay down.
    Returning None degrades to TODAY's group name, which is the pre-existing
    behaviour -- not a silent new failure mode.
    """
    pre_resolved = getattr(user, "allocation_token", None)
    if pre_resolved:
        return str(pre_resolved)

    username = getattr(user, "username", "") or ""
    # Only pool visitors have a lease; skip the query for everyone else.
    if not username.startswith("visitor-"):
        return None

    try:
        from apps.infra.project_app.models import VisitorAllocation

        number = int(username.rsplit("-", 1)[-1])
        row = VisitorAllocation.objects.filter(
            visitor_number=number, is_active=True
        ).only("allocation_token").first()
        return row.allocation_token if row else None
    except Exception:  # stx-allow: fallback (reason: connect-path lookup failure degrades to today's group name, never takes the relay down)
        return None


def relay_group_for(user) -> str:
    """The channel-layer group carrying eval_js / ui_action for ``user``.

    MUST be the only place this name is built. Producers and the consumer have
    to agree exactly, and a mismatch is silent.
    """
    username = getattr(user, "username", "") or ""
    token = _allocation_token_for(user)
    if not token:
        return f"{_PREFIX}_{username}"
    return f"{_PREFIX}_{username}_{token}"
