# -*- coding: utf-8 -*-
# File: config/_env.py
"""
Environment-variable read helpers with legacy SCITEX_CLOUD_* alias support.

Background
----------
The project was renamed scitex-cloud -> scitex-hub at v0.18.0 (ADR-0001).
Commit d38d6894 renamed the operator-facing env-var prefix from
``SCITEX_CLOUD_*`` to ``SCITEX_HUB_*`` (Step D.1). Deployments and CI that
still export the old prefix would otherwise silently fall through to the
default value, which violates the project's "no silent fallback" rule.

This module exposes :func:`getenv_with_legacy_alias`, which reads
``SCITEX_HUB_<NAME>`` first and, if unset, falls back to
``SCITEX_CLOUD_<NAME>`` while emitting an explicit ``DeprecationWarning``.
The direction is strictly one-way:

    SCITEX_HUB_<NAME>   (canonical)   <- preferred
    SCITEX_CLOUD_<NAME> (legacy alias) -> read only if HUB is unset

The new prefix is what every component should set going forward; the
legacy prefix is recognized for backward compatibility and is logged.

See: docs/adr/0001-rename-scitex-cloud-to-scitex-hub.md
"""
from __future__ import annotations

import os
import warnings
from typing import Optional

# Canonical and legacy prefixes for the environment-variable rename.
_HUB_PREFIX = "SCITEX_HUB_"
_CLOUD_PREFIX = "SCITEX_CLOUD_"


def _legacy_name(hub_name: str) -> Optional[str]:
    """Return the SCITEX_CLOUD_* alias for a SCITEX_HUB_* name, else None."""
    if hub_name.startswith(_HUB_PREFIX):
        return _CLOUD_PREFIX + hub_name[len(_HUB_PREFIX) :]
    return None


def getenv_with_legacy_alias(
    name: str,
    default: Optional[str] = None,
) -> Optional[str]:
    """Read a ``SCITEX_HUB_*`` env var, falling back to ``SCITEX_CLOUD_*``.

    If ``SCITEX_HUB_<X>`` is set, its value is returned (canonical path).
    Otherwise, if ``SCITEX_CLOUD_<X>`` is set, its value is returned and a
    :class:`DeprecationWarning` is emitted to flag the legacy prefix.
    If neither is set, ``default`` is returned.

    The alias direction is one-way: ``SCITEX_HUB_*`` is canonical;
    ``SCITEX_CLOUD_*`` is the legacy alias kept for backward compatibility
    (ADR-0001). Callers should only pass ``SCITEX_HUB_*`` names — this
    function never falls back from CLOUD to HUB.

    Args:
        name: The canonical env-var name (must start with ``SCITEX_HUB_``
            to enable alias lookup; other names work but skip the alias).
        default: Value returned when neither the canonical nor the legacy
            name is set in the environment.

    Returns:
        The environment value, or ``default`` if unset.
    """
    value = os.environ.get(name)
    if value is not None:
        return value

    legacy = _legacy_name(name)
    if legacy is not None:
        legacy_value = os.environ.get(legacy)
        if legacy_value is not None:
            warnings.warn(
                (
                    f"Environment variable {legacy!r} is a deprecated alias "
                    f"of {name!r}. The scitex-cloud -> scitex-hub rename "
                    "(ADR-0001) deprecated the SCITEX_CLOUD_* prefix; set "
                    f"{name} instead. The legacy name will be removed in a "
                    "future major release."
                ),
                DeprecationWarning,
                stacklevel=2,
            )
            return legacy_value

    return default


def require_env_with_legacy_alias(name: str) -> str:
    """Like :func:`getenv_with_legacy_alias` but raises if both are unset.

    Mirrors the existing ``require_env`` helper in
    :mod:`config.settings.settings_shared`, but transparently honors the
    legacy ``SCITEX_CLOUD_*`` alias (with DeprecationWarning).
    """
    value = getenv_with_legacy_alias(name)
    if value is None:
        legacy = _legacy_name(name) or ""
        hint = f" (or its deprecated alias {legacy!r})" if legacy else ""
        raise EnvironmentError(
            f"Required environment variable {name!r}{hint} is not set. "
            "Check deployment/docker/envs/.env.{ENV} file."
        )
    return value


__all__ = [
    "getenv_with_legacy_alias",
    "require_env_with_legacy_alias",
]

# EOF
