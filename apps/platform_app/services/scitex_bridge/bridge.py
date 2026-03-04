#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/platform_app/services/scitex_bridge/bridge.py
"""
ScitexBridge: per-user, per-project gateway to the scitex Python package.

Each bridge instance is scoped to a single (user, project) pair.
It guards access to a fixed allowlist of public modules, sets up
working-directory isolation, and serializes results before returning them.
"""

from __future__ import annotations

import importlib
import logging
import os
from pathlib import Path
from typing import Any, Optional

from .serializer import serialize_result

logger = logging.getLogger(__name__)

# Modules that callers are allowed to reach through the bridge.
# Internal/private scitex sub-packages are intentionally excluded.
ALLOWED_MODULES = frozenset({"io", "plt", "stats", "writer", "scholar", "session"})


class ScitexBridgeError(Exception):
    """Raised when the bridge cannot fulfil a request."""


class ModuleProxy:
    """
    Thin proxy that binds a scitex module to a bridge instance.

    Allows attribute-style access:  proxy.describe(data)
    instead of:                     bridge.call("stats", "describe", data)
    """

    def __init__(self, bridge: "ScitexBridge", module_name: str) -> None:
        object.__setattr__(self, "_bridge", bridge)
        object.__setattr__(self, "_module_name", module_name)

    def __getattr__(self, function_name: str):
        bridge = object.__getattribute__(self, "_bridge")
        module_name = object.__getattribute__(self, "_module_name")

        def _caller(*args, **kwargs):
            return bridge.call(module_name, function_name, *args, **kwargs)

        return _caller


class ScitexBridge:
    """
    Gateway to public scitex APIs with per-user / per-project isolation.

    Parameters
    ----------
    project:
        Django Project instance (may be None for user-level operations).
    user:
        Django User instance. Must be authenticated.
    """

    def __init__(self, project=None, user=None) -> None:
        self._project = project
        self._user = user
        self._workdir: Optional[Path] = self._resolve_workdir()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def call(self, module: str, function: str, *args: Any, **kwargs: Any) -> Any:
        """
        Call ``scitex.<module>.<function>(*args, **kwargs)``.

        Parameters
        ----------
        module:
            One of the allowed module names (io, plt, stats, writer,
            scholar, session).
        function:
            Public function name within that module. Names starting with
            an underscore are rejected.

        Returns
        -------
        JSON-safe dict produced by ``serialize_result``.

        Raises
        ------
        ScitexBridgeError
            On access-policy violations or scitex-level errors.
        """
        self._validate_module(module)
        self._validate_function(function)

        scitex_module = self._import_module(module)
        func = self._resolve_function(scitex_module, module, function)

        old_cwd = os.getcwd()
        try:
            if self._workdir:
                os.chdir(self._workdir)
            raw = func(*args, **kwargs)
            return serialize_result(raw)
        except ScitexBridgeError:
            raise
        except Exception as exc:
            raise ScitexBridgeError(
                f"scitex.{module}.{function} raised {type(exc).__name__}: {exc}"
            ) from exc
        finally:
            os.chdir(old_cwd)

    def get_module(self, module_name: str) -> ModuleProxy:
        """
        Return a proxy object for the given scitex module.

        The proxy supports attribute-style calls:
            proxy = bridge.get_module("stats")
            result = proxy.describe(data)
        """
        self._validate_module(module_name)
        return ModuleProxy(self, module_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_workdir(self) -> Optional[Path]:
        """Derive per-project working directory from the project model."""
        if self._project is None:
            return None
        try:
            workdir = self._project.get_local_path()
            workdir.mkdir(parents=True, exist_ok=True)
            return workdir
        except Exception as exc:
            logger.warning(
                "ScitexBridge: could not resolve workdir for project %s: %s",
                getattr(self._project, "name", "?"),
                exc,
            )
            return None

    @staticmethod
    def _validate_module(module: str) -> None:
        if module not in ALLOWED_MODULES:
            raise ScitexBridgeError(
                f"Module '{module}' is not allowed. "
                f"Allowed modules: {sorted(ALLOWED_MODULES)}"
            )

    @staticmethod
    def _validate_function(function: str) -> None:
        if function.startswith("_"):
            raise ScitexBridgeError(
                f"Access to private/internal function '{function}' is not allowed."
            )

    @staticmethod
    def _import_module(module: str):
        try:
            return importlib.import_module(f"scitex.{module}")
        except ImportError as exc:
            raise ScitexBridgeError(
                f"scitex.{module} is not installed or not importable: {exc}"
            ) from exc

    @staticmethod
    def _resolve_function(scitex_module, module: str, function: str):
        func = getattr(scitex_module, function, None)
        if func is None or not callable(func):
            raise ScitexBridgeError(f"scitex.{module} has no callable '{function}'.")
        return func


# EOF
