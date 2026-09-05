#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/infra/project_app/services/visitor_pool/landing.py

"""Which project a provisioned visitor slot OPENS on.

A visitor workspace holds two projects: the seeded demo (figures, data, a
manuscript) and the ``dotfiles`` home project (bashrc, gitconfig, screenrc).
Only one of them is a defensible first screen for a stranger.

WHY THIS IS NOT DONE BY THE PROFILE SIGNAL
------------------------------------------
Provisioning creates the USER first, so ``accounts_app.signals`` runs while
``dotfiles`` is the only project that exists and points the profile at it. The
demo row is created seconds later, and nothing revisits the choice:
``_adopt_landing_project`` deliberately refuses to overwrite an existing
pointer, because for a signed-in human that pointer is a CHOICE — pinned by
``tests/apps/accounts_app/test_signals_landing_project.py::
test_an_existing_choice_is_not_overwritten``.

PROVISIONING IS NOT A CHOICE. Both visitor creation sites — pool
initialisation and slot reset — end by deciding what the NEXT visitor opens
on, and there is no preference of theirs to protect. So the decision belongs
here, at those two call sites, and the signal's contract stays intact.

WHY IT EXISTS AT ALL
--------------------
Migration ``accounts_app.0014_visitors_land_on_the_demo_project`` repaired the
sixteen rows that existed on 2026-08-16 — but a data migration cannot repair
rows written after it runs. Measured on the develop preview 2026-09-05, minutes
after four fresh slots were provisioned: a new visitor's page title was
``dotfiles — SciTeX (dev)`` and the header's first word was ``dotfiles``.
Operator the same day: 「入ってきたユーザが今だと意味不明なので戻っちゃう」 — an
arriving user finds it meaningless and leaves. This module makes that
migration's intent the mechanism.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

__all__ = ["land_visitor_on"]


def land_visitor_on(visitor_user, project) -> bool:
    """Point ``visitor_user``'s profile at ``project``. Returns whether it moved.

    Best-effort by design: a slot whose profile row is missing must still be
    servable, so this reports rather than raises — the caller is in the middle
    of provisioning and a failure here is cosmetic, not structural.
    """
    profile = getattr(visitor_user, "profile", None)
    if profile is None:
        logger.warning(
            "[VisitorPool] %s has no profile; cannot set its landing project",
            getattr(visitor_user, "username", "<unknown>"),
        )
        return False
    if profile.last_active_repository_id == project.pk:
        return False
    profile.last_active_repository = project
    profile.save(update_fields=["last_active_repository"])
    logger.info(
        "[VisitorPool] %s opens on %s (%s)",
        visitor_user.username,
        project.name,
        project.slug,
    )
    return True


# EOF
