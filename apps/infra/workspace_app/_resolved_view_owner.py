"""Identify an already-resolved view through installed documentation ownership."""

import sys
from importlib import metadata
from pathlib import Path
from types import FunctionType


def resolved_view_owner(request):
    """Return one proven distribution, without importing or executing leaf code.

    Explicit mounts need not be launcher entries. Their callable must belong to
    an already-loaded module and an installed distribution's recorded file; a
    unique Docs declaration must cover that module. Ambiguity fails closed.
    """
    callback = getattr(getattr(request, "resolver_match", None), "func", None)
    seen = set()
    for _ in range(16):
        if not isinstance(callback, FunctionType) or id(callback) in seen:
            return None
        seen.add(id(callback))
        wrapped = getattr(callback, "__wrapped__", None)
        if wrapped is None:
            break
        callback = wrapped
    else:
        return None
    module = sys.modules.get(callback.__module__)
    if module is None or callback.__globals__ is not vars(module):
        return None
    origin = getattr(getattr(module, "__spec__", None), "origin", None)
    if not origin or origin != getattr(module, "__file__", None):
        return None
    try:
        actual = Path(origin).resolve(strict=True)
        if Path(callback.__code__.co_filename).resolve(strict=True) != actual:
            return None
    except (OSError, ValueError):
        return None

    try:
        from scitex_dev import list_doc_providers, normalize_distribution_name

        rows = list_doc_providers()
    except (ImportError, AttributeError, OSError, ValueError):
        return None
    owners = set()
    for row in rows:
        declared = row.target.partition(":")[0]
        if not declared or not all(part.isidentifier() for part in declared.split(".")):
            continue
        if not (
            module.__name__ == declared or module.__name__.startswith(declared + ".")
        ):
            continue
        if sum(other.name == row.name for other in rows) != 1:
            return None
        try:
            owner = normalize_distribution_name(row.distribution)
            distributions = [
                dist
                for dist in metadata.distributions(name=owner)
                if normalize_distribution_name(dist.metadata["Name"]) == owner
            ]
            if len(distributions) != 1:
                return None
            dist = distributions[0]
            relative = module.__name__.replace(".", "/")
            recorded = {str(path) for path in dist.files or ()}
            candidates = (relative + ".py", relative + "/__init__.py")
            if any(
                path in recorded
                and Path(dist.locate_file(path)).resolve(strict=True) == actual
                for path in candidates
            ):
                owners.add(owner)
        except (OSError, TypeError, ValueError):
            return None
    return next(iter(owners)) if len(owners) == 1 else None
