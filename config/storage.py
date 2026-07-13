#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static-files storage backends.

Home of the content-hashing backend prod/staging opt into. WHY we hash at all
is documented in ``config/settings/settings_static.py``; this module is only
concerned with one wrinkle: source maps.
"""

from __future__ import annotations

from whitenoise.storage import CompressedManifestStaticFilesStorage


def _without_source_map_rules(patterns):
    """Django's reference-rewriting rules, minus the sourceMappingURL ones.

    Derived from Django's own defaults rather than copied, so a Django upgrade
    that adds or changes a rule is picked up automatically instead of being
    silently frozen at whatever was true the day this was written.
    """
    kept_groups = []
    for extension, rules in patterns:
        kept = tuple(
            rule
            for rule in rules
            if "sourceMappingURL"
            not in (rule[0] if isinstance(rule, (tuple, list)) else rule)
        )
        if kept:
            kept_groups.append((extension, kept))
    return tuple(kept_groups)


class HashedStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Content-hashing storage that does not manage SOURCE MAPS.

    Strictness is the whole point of the hashing backend: a dangling CSS
    ``url()``/``@import`` or ``{% static %}`` must still raise, because that is a
    real 404 in a user's browser. Those rules are untouched here.

    A ``//# sourceMappingURL=….js.map`` comment is a different animal. It is a
    DEV-ONLY pointer that a browser fetches only with devtools open, and vendored
    bundles routinely ship minified code *without* the maps: scitex-ui vendors
    Monaco's ``vs/`` tree but no ``min-maps/``, so its ``workerMain.js`` ends with
    a pointer to a ``.map`` that was deliberately never distributed. Django then
    treats that debug pointer as a hard dependency and fails ``collectstatic`` —
    i.e. an artefact that was never meant to ship blocks every deploy.

    ``manifest_strict = False`` would be the wrong cure: it silences REAL missing
    assets too, which is exactly the class of bug this backend exists to surface.
    So we make the narrow, explicit statement instead — *source maps are not
    managed assets* — and leave everything user-facing strict.

    Cost, stated plainly: a shipped ``.map`` keeps its unhashed URL, so devtools
    may 404 on it. That is a debugging nicety, not a user-facing asset.
    """

    patterns = _without_source_map_rules(CompressedManifestStaticFilesStorage.patterns)


# EOF
