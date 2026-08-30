#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interrogates the DEPLOYMENT TARGET. This file is executed INSIDE the target.

It is never imported by the deploy host. ``preflight_sibling_floors.py`` reads
this source, appends a one-line ``_main(<spec json>)`` call, and pipes the whole
thing into whatever command runs code inside the target:

    docker run --rm --network none --entrypoint python <image> -   < this
    docker exec -i <container> python3 -                          < this

WHY IT IS SHIPPED IN AND NOT IMPORTED
-------------------------------------
The 2026-08-18 outage happened because a package was verified in the agent's own
container and the result was stated about production. Anything this file learns,
it learns by running where the code will actually run. It therefore imports
NOTHING outside the standard library and assumes nothing about the target beyond
"there is a Python here" -- a bare image with no repo checkout, no env file and
no network still answers.

WHAT IT REPORTS, AND THE THREE VALUES IT USES
---------------------------------------------
Every answer is one of PRESENT (a version string), ABSENT (the distribution has
no metadata here) or UNKNOWN (something went wrong reading it). UNKNOWN is never
folded into either of the other two -- the driver treats it as a refusal, because
an unread floor and a satisfied floor look identical if you let them.

THE BOOT OVERLAY
----------------
Prod's image is not the last word on what runs. ``entrypoint-prod.sh`` runs
``scripts/apps/install_apps.sh`` at EVERY container start, which editable-installs
the apps listed in ``.scitex-apps.json`` from git clones on a persistent volume,
overriding the image's PyPI wheels. Measured 2026-08-22: the image ships
scitex-writer 2.26.1 and the running container serves 2.42.0 from
``/app/.apps/scitex-writer``. So a check that reads only the image reports a floor
violation that boot repairs, and a gate that cries wolf on every deploy gets
switched off. When the driver mounts that volume, it passes the clone paths here
and this probe reads each clone's declared version -- which is exactly the version
the editable install will publish -- and reports it as the overlay answer.

IMPORT PROBES AND THE ERROR-CLASS RULE
--------------------------------------
A floor check is structurally blind to the 2026-08-22 outage: scitex-sh and
scitex-decorators are declared in NO pyproject anywhere in the chain (not hub's,
not scitex's, not scitex-io's), so no floor comparison can compare them. They are
reached only by executing the import. Hence the second half.

Imports are classified, not merely caught:

  * ``ModuleNotFoundError`` / ``ImportError`` -> FATAL. This is the shape of both
    incidents: the package or the symbol is not there.
  * any OTHER exception -> INCONCLUSIVE, reported, not fatal. A Django
    ``ImproperlyConfigured`` or ``AppRegistryNotReady`` proves the module was
    found and executed far enough to reach Django's configuration, i.e. the
    artifact HAS the package -- which is the question being asked. Treating it as
    fatal would make the gate red on every deploy for a reason that is not the
    defect, and a gate that is always red is a gate that gets removed.

    This is a stated rule with a stated blind spot, not a silent fallback: a
    genuine missing symbol that is masked by a Django configuration error raised
    earlier in the same module will read as INCONCLUSIVE. The driver prints every
    inconclusive probe with its exception, so it is visible rather than swallowed.

To shrink that blind spot the probe first tries a minimal ``django.setup()``
(``settings.configure()`` with no apps and no database -- nothing is connected to,
nothing is migrated). Most Django-touching sibling modules import cleanly after
it, which converts would-be INCONCLUSIVE results into real answers.
"""

import importlib
import importlib.metadata
import io
import json
import os
import re
import sys
import traceback

#: The driver scans stdout for these. The target's own start-up chatter (uv
#: notices, deprecation warnings, an entrypoint banner) shares this stream, so
#: the report is delimited rather than assumed to be the whole of stdout.
REPORT_BEGIN = "@@SCITEX_HUB_PREFLIGHT_REPORT_BEGIN@@"
REPORT_END = "@@SCITEX_HUB_PREFLIGHT_REPORT_END@@"

#: ``version = "1.2.3"`` inside a clone's ``[project]`` table.
_PYPROJECT_VERSION = re.compile(r'^\s*version\s*=\s*"([^"]+)"', re.MULTILINE)

#: ``__version__ = "1.2.3"`` inside a clone's package ``__init__``.
_DUNDER_VERSION = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def _installed_version(distribution):
    """What THIS environment reports for ``distribution``.

    Returns one of ``{"version": str}``, ``{"absent": True}`` or
    ``{"unknown": reason}``. ``importlib.metadata`` is the authority here rather
    than an import: a distribution can be installed under a name that shares no
    spelling with any module it provides, and hub declares floors by
    distribution name.
    """
    try:
        return {"version": importlib.metadata.version(distribution)}
    except importlib.metadata.PackageNotFoundError:
        return {"absent": True}
    except Exception as exc:  # noqa: BLE001 - reported, never swallowed
        return {"unknown": "{}: {}".format(type(exc).__name__, exc)}


def _clone_version(clone_dir):
    """The version an editable install of ``clone_dir`` would publish.

    ``importlib.metadata`` cannot answer this before the install has happened,
    and on 2026-08-22 it could not answer it AFTER either: all five
    boot-overlaid apps are editable installs whose module names have no
    dist-info reverse mapping. So the clone is read directly, in the same
    precedence pip uses -- the ``[project] version`` it will be built from
    first, the package ``__version__`` second.
    """
    if not os.path.isdir(clone_dir):
        return {"absent": True}

    pyproject = os.path.join(clone_dir, "pyproject.toml")
    if os.path.isfile(pyproject):
        try:
            with io.open(pyproject, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except Exception as exc:  # noqa: BLE001
            return {"unknown": "unreadable {}: {}".format(pyproject, exc)}
        match = _PYPROJECT_VERSION.search(text)
        if match:
            return {"version": match.group(1), "source": pyproject}

    src = os.path.join(clone_dir, "src")
    if os.path.isdir(src):
        try:
            entries = sorted(os.listdir(src))
        except Exception as exc:  # noqa: BLE001
            return {"unknown": "unreadable {}: {}".format(src, exc)}
        for entry in entries:
            init = os.path.join(src, entry, "__init__.py")
            if not os.path.isfile(init):
                continue
            try:
                with io.open(init, encoding="utf-8", errors="replace") as handle:
                    match = _DUNDER_VERSION.search(handle.read())
            except Exception:  # noqa: BLE001 - try the next candidate package
                continue
            if match:
                return {"version": match.group(1), "source": init}

    # Deliberately NOT "absent": the clone is here, we simply could not read a
    # version out of it. Calling that ABSENT would let the driver fall back to
    # the image version and report a floor as satisfied by a package the boot
    # overlay is about to replace with something unmeasured.
    return {"unknown": "clone present at {} but no version found in pyproject.toml or src/*/__init__.py".format(clone_dir)}


def _bootstrap_django():
    """Minimal ``django.setup()`` so Django-touching modules import cleanly.

    No apps, no database, no migrations -- ``settings.configure()`` with an empty
    ``INSTALLED_APPS`` and an empty ``DATABASES`` connects to nothing. Its only
    job is to stop ``django.conf.settings`` raising ``ImproperlyConfigured`` the
    moment a sibling's views module is imported, so that the import probe gets to
    ask its real question.
    """
    try:
        import django
        from django.conf import settings
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": "django not importable: {}: {}".format(type(exc).__name__, exc)}

    try:
        if not settings.configured:
            settings.configure(
                DEBUG=False,
                SECRET_KEY="scitex-hub-preflight-probe-not-a-real-key",
                INSTALLED_APPS=[],
                DATABASES={},
                USE_TZ=True,
            )
        django.setup()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": "{}: {}".format(type(exc).__name__, exc)}
    return {"ok": True, "detail": "settings.configure() + django.setup(), no apps, no database"}


def _probe_import(module, attrs):
    """Execute one import inside the target and classify what happens.

    ``attrs`` are attribute touches performed after the import. They exist for
    the umbrella's lazy layer: ``import scitex`` succeeds on an environment where
    ``scitex.plt`` resolution raises, because ``scitex/__init__.py`` defers to
    ``_LazyModule`` and only ``__getattr__`` reaches the real distribution. One
    such touch pulled six distributions on 2026-08-22 that no import scanner and
    no dependency resolver can see.
    """
    result = {"module": module, "attrs": list(attrs)}
    try:
        obj = importlib.import_module(module)
        for attr in attrs:
            getattr(obj, attr)
    except (ImportError, ModuleNotFoundError) as exc:
        result["status"] = "fatal"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()
        return result
    except Exception as exc:  # noqa: BLE001 - see the error-class rule in the module docstring
        result["status"] = "inconclusive"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()
        return result
    result["status"] = "ok"
    return result


def _run(spec):
    """Answer everything ``spec`` asks and print the delimited JSON report."""
    prepended = []
    for path in spec.get("extra_syspath", []):
        if os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)
            prepended.append(path)

    report = {
        "probe_protocol": 1,
        "python_version": sys.version.split()[0],
        "executable": sys.executable,
        "prefix": sys.prefix,
        "syspath_prepended": prepended,
        "syspath_requested": list(spec.get("extra_syspath", [])),
        "installed": {},
        "overlay": {},
        "imports": [],
        "django_bootstrap": None,
    }

    for distribution in spec.get("distributions", []):
        report["installed"][distribution] = _installed_version(distribution)

    for distribution, clone_dir in sorted(spec.get("overlay", {}).items()):
        answer = _clone_version(clone_dir)
        answer["clone"] = clone_dir
        report["overlay"][distribution] = answer

    probes = spec.get("import_probes", [])
    if probes:
        report["django_bootstrap"] = _bootstrap_django()
        for probe in probes:
            report["imports"].append(_probe_import(probe["module"], probe.get("attrs", [])))

    sys.stdout.write("\n" + REPORT_BEGIN + "\n")
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True))
    sys.stdout.write("\n" + REPORT_END + "\n")
    sys.stdout.flush()


# The driver ships this file into the target on stdin and APPENDS its own
# `_run(json.loads(...))` call, so `__name__` is "__main__" there too. Requiring
# an argv spec keeps this block from firing first and emitting a second, empty
# report that the driver would read instead of the real one.
if __name__ == "__main__" and len(sys.argv) > 1:
    _run(json.loads(sys.argv[1]))

# EOF
