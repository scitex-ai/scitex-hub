#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/__init__.py

"""Deprecation shim: ``scitex_cloud`` was renamed to ``scitex_hub``.

``scitex-cloud`` is the OLD distribution / module name of ``scitex-hub``
(see ``docs/adr/0001-rename-scitex-cloud-to-scitex-hub.md``). This module is
kept only as a transitional compatibility shim: importing it (or any of its
submodules) re-exports the corresponding object from :mod:`scitex_hub` and
emits a :class:`DeprecationWarning`.

    >>> import scitex_cloud            # works, warns
    >>> scitex_cloud.CloudClient is scitex_hub.CloudClient
    True
    >>> from scitex_cloud.sdk import *  # forwards to scitex_hub.sdk

Update your imports ``scitex_cloud`` -> ``scitex_hub``; this shim will be
removed in a future release.
"""

from __future__ import annotations

import importlib
import sys
import warnings

warnings.warn(
    "The 'scitex_cloud' package has been renamed to 'scitex_hub'. "
    "Importing 'scitex_cloud' is deprecated and the shim will be removed in "
    "a future release; update your imports to 'scitex_hub'. "
    "See docs/adr/0001-rename-scitex-cloud-to-scitex-hub.md.",
    DeprecationWarning,
    stacklevel=2,
)

_hub = importlib.import_module("scitex_hub")

# Mirror the renamed package's identity so attribute access, ``__version__``,
# ``__all__`` and any direct ``scitex_cloud.<name>`` lookups resolve to the
# live ``scitex_hub`` objects.
__version__ = getattr(_hub, "__version__", "unknown")
__author__ = getattr(_hub, "__author__", "SciTeX Team")
__all__ = list(getattr(_hub, "__all__", []))

# Make ``scitex_cloud`` resolve attributes from ``scitex_hub`` transparently.
__path__ = list(getattr(_hub, "__path__", []))


def __getattr__(name: str):
    """Forward attribute access to :mod:`scitex_hub` (PEP 562)."""
    try:
        return getattr(_hub, name)
    except AttributeError:
        # Fall back to importing it as a submodule (handled by the finder).
        try:
            return importlib.import_module(f"scitex_cloud.{name}")
        except ImportError as exc:  # pragma: no cover - defensive
            raise AttributeError(
                f"module 'scitex_cloud' has no attribute '{name}'"
            ) from exc


def __dir__():
    return sorted(set(dir(_hub)) | set(globals()))


# --- Submodule forwarding -------------------------------------------------
# Any ``import scitex_cloud.<sub>`` (or ``from scitex_cloud.<sub> import x``)
# is routed to the matching ``scitex_hub.<sub>`` module via a meta path
# finder + loader, so the shim never duplicates the package layout and the
# aliased module is the *same object* as ``scitex_hub.<sub>`` (identity holds).
import importlib.abc
import importlib.machinery

_PREFIX = "scitex_cloud."


class _ScitexCloudLoader(importlib.abc.Loader):
    """Loader that returns the real ``scitex_hub.<sub>`` module object."""

    def __init__(self, target: str) -> None:
        self._target = target

    def create_module(self, spec):
        return importlib.import_module(self._target)

    def exec_module(self, module):  # already executed by import_module
        return None


class _ScitexCloudMetaFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if not fullname.startswith(_PREFIX):
            return None
        real_target = "scitex_hub." + fullname[len(_PREFIX) :]
        loader = _ScitexCloudLoader(real_target)
        return importlib.machinery.ModuleSpec(fullname, loader)


sys.meta_path.insert(0, _ScitexCloudMetaFinder())

# EOF
