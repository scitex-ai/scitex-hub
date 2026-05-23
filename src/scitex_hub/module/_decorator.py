#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The @stx.module decorator for marking functions as SciTeX workspace modules."""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable

from . import INJECTED
from ._manifest import ModuleManifest
from ._output import ModuleOutputCollector


def module(
    func: Callable = None,
    *,
    label: str = "",
    icon: str = "fa-puzzle-piece",
    category: str = "other",
    description: str = "",
    version: str = "0.1.0",
    dependencies: list | None = None,
    min_scitex_version: str = "",
) -> Callable:
    """Decorator to mark a function as a SciTeX workspace module.

    The decorated function can declare parameters with default=INJECTED;
    the module runner will supply *project*, *plt*, and *logger* at
    execution time.
    """

    def decorator(fn: Callable) -> Callable:
        _label = label or fn.__name__.replace("_", " ").title()
        _description = description
        if not _description and fn.__doc__:
            _description = fn.__doc__.strip().split("\n")[0]

        manifest = ModuleManifest(
            name=fn.__name__,
            label=_label,
            icon=icon,
            category=category,
            description=_description,
            version=version,
            dependencies=dependencies or [],
            min_scitex_version=min_scitex_version,
        )

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            """Execute the module function, collecting outputs."""
            ModuleOutputCollector.clear()
            try:
                result = fn(*args, **kwargs)
            except Exception:
                ModuleOutputCollector.clear()
                raise
            outputs = ModuleOutputCollector.get_current()
            ModuleOutputCollector.clear()
            return result, outputs

        wrapper._is_stx_module = True
        wrapper._manifest = manifest
        wrapper._func = fn

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


def _inject_params(fn: Callable, provided: dict[str, Any]) -> dict[str, Any]:
    """Build kwargs for *fn*, injecting values where the default is INJECTED."""
    sig = inspect.signature(fn)
    kwargs: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        if param.default is not inspect.Parameter.empty and isinstance(
            param.default, type(INJECTED)
        ):
            if name in provided:
                kwargs[name] = provided[name]
    return kwargs


# EOF
