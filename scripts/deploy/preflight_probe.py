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

import ast
import hashlib
import importlib
import importlib.metadata
import importlib.util
import io
import json
import os
import re
import stat
import subprocess
import sys
import traceback
from pathlib import Path

#: The driver scans stdout for these. The target's own start-up chatter (uv
#: notices, deprecation warnings, an entrypoint banner) shares this stream, so
#: the report is delimited rather than assumed to be the whole of stdout.
REPORT_BEGIN = "@@SCITEX_HUB_PREFLIGHT_REPORT_BEGIN@@"
REPORT_END = "@@SCITEX_HUB_PREFLIGHT_REPORT_END@@"

#: ``version = "1.2.3"`` inside a clone's ``[project]`` table.
_PYPROJECT_VERSION = re.compile(r'^\s*version\s*=\s*"([^"]+)"', re.MULTILINE)

#: ``__version__ = "1.2.3"`` inside a clone's package ``__init__``.
_DUNDER_VERSION = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)

APP_DISTRIBUTIONS = frozenset({
    "scitex-ui", "figrecipe", "scitex-writer", "scitex-cards",
    "scitex-storage", "scitex-agent-container",
})


def _read_manifest(path):
    """Read a bounded regular pin without following any ancestor symlink."""
    path = Path(path)
    if not path.is_absolute() or str(path) != os.path.normpath(path):
        raise ValueError("noncanonical manifest path")
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
        file_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                          dir_fd=descriptor)
        try:
            before = os.fstat(file_fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > 64 * 1_024**2:
                raise ValueError("regular bounded manifest required")
            with os.fdopen(file_fd, "rb", closefd=False) as handle:
                data = handle.read(64 * 1_024**2 + 1)
            after = os.fstat(file_fd)
            fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
            if (tuple(getattr(before, f) for f in fields) !=
                    tuple(getattr(after, f) for f in fields) or len(data) != before.st_size):
                raise ValueError("manifest changed during read")
            return data
        finally:
            os.close(file_fd)
    finally:
        os.close(descriptor)


def _boot_snapshot(project_root=Path("/app")):
    """Use the Apps-owned verifier and reread the exact target-side pin.

    ``project_root`` is an internal fixture seam, never a driver/spec override.
    The normal path is the existing target /app, not a manifest-supplied root.
    """
    mode = os.environ.get("SCITEX_APPS_BOOT_MODE") or "legacy"
    if mode == "legacy":
        return {"mode": mode}, None
    if mode != "immutable":
        return {"mode": mode, "verified": False, "error": "unknown boot mode"}, None
    path = os.environ.get("SCITEX_APPS_BOOT_MANIFEST", "")
    digest = os.environ.get("SCITEX_APPS_BOOT_MANIFEST_SHA256", "")
    profile = os.environ.get("SCITEX_APPS_BOOT_PROFILE", "")
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B",
             str(project_root / "scripts/apps/verify_immutable_boot.py"),
             "--manifest", path, "--sha256", digest, "--profile", profile,
             "--project-root", str(project_root)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300,
        )
        if result.returncode != 0:
            raise ValueError("Apps snapshot verifier refused")
        data = _read_manifest(path)
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("manifest changed after verification")
        manifest = json.loads(data)
        if (manifest["schema"] != "scitex.apps.immutable-boot/v1" or
                manifest["profile"] != profile):
            raise ValueError("manifest profile changed after verification")
        rows = manifest["distributions"]
        if (len(rows) != len(APP_DISTRIBUTIONS) or
                {row["name"] for row in rows} != APP_DISTRIBUTIONS):
            raise ValueError("all six incumbent distributions required")
        if any(row["mode"] != ("wheel" if row["name"] == "scitex-storage" else "editable")
               for row in rows):
            raise ValueError("five editables and Storage wheel required")
    except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as exc:
        return {"mode": mode, "verified": False, "error": type(exc).__name__}, None
    return {"mode": mode, "verified": True, "profile": profile,
            "manifest_sha256": digest}, manifest


def _normalized_name(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def _console_binding(path, entry, package):
    """Measure the installed Python wrapper without executing a CLI command."""
    text = path.read_text(encoding="utf-8")
    first = text.splitlines()[0]
    if not first.startswith("#!") or os.path.realpath(first[2:]) != os.path.realpath(sys.executable):
        raise ValueError("console interpreter differs from target")
    tree = ast.parse(text, filename=str(path))
    module, separator, attribute = entry.value.partition(":")
    if not separator or not attribute.isidentifier():
        raise ValueError("unsupported console entry point")
    aliases = {
        alias.asname or alias.name
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module == module
        for alias in node.names if alias.name == attribute
    }
    if not aliases or not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                              and node.func.id in aliases for node in ast.walk(tree)):
        raise ValueError("console wrapper does not call its declared entry point")
    # Resolve its module through the same active target path. Do not invoke its
    # function, load a model, initialize an account, or perform a scientific job.
    spec = importlib.util.find_spec(module)
    if spec is None or spec.origin is None or not Path(spec.origin).is_relative_to(package):
        raise ValueError("console module belongs to another producer")
    if not callable(entry.load()):
        raise ValueError("console entry point is not callable")
    loaded = sys.modules[module]
    if (getattr(loaded, "__file__", None) != spec.origin or
            getattr(getattr(loaded, "__spec__", None), "origin", None) != spec.origin):
        raise ValueError("loaded console module differs from resolved producer")


def _active_bindings(manifest):
    """Compare actual imports, metadata and wrappers with the verified producer."""
    roots = {row["id"]: Path(row["path"]) for row in manifest["roots"]}
    distributions = list(importlib.metadata.distributions())
    bindings = {}
    for row in manifest["distributions"]:
        name = row["name"]
        answer = {"mode": row["mode"], "version": row["version"]}
        try:
            candidates = [dist for dist in distributions
                          if _normalized_name(dist.metadata.get("Name", "")) == name]
            metadata = roots[row["metadata"]["root"]] / row["metadata"]["path"]
            identities = {}
            for dist in candidates:
                # RECORD claims cannot establish metadata origin: a duplicate
                # dist-info can copy another RECORD verbatim. Only the actual
                # stdlib filesystem metadata reader location is supported here.
                location = getattr(dist, "_path", None)
                if not isinstance(dist, importlib.metadata.PathDistribution) or not isinstance(location, Path):
                    raise ValueError("distribution metadata location unknown")
                identities[location.absolute()] = dist
            if set(identities) != {metadata}:
                raise ValueError("missing, duplicate or foreign distribution metadata")
            dist = next(iter(identities.values()))
            if dist.version != row["version"]:
                raise ValueError("active distribution version differs")
            package = roots[row["package"]["root"]] / row["package"]["path"]
            module = importlib.import_module(name.replace("-", "_"))
            expected = str(package / "__init__.py")
            if (getattr(module, "__file__", None) != expected or
                    getattr(getattr(module, "__spec__", None), "origin", None) != expected or
                    list(getattr(module, "__path__", [])) != [str(package)]):
                raise ValueError("active package belongs to another producer")
            entries = [entry for entry in dist.entry_points if entry.group == "console_scripts"]
            scripts = {entry.name: entry for entry in entries}
            declared = {pointer["path"] for pointer in row["console_scripts"]}
            if (len(scripts) != len(entries) or len(declared) != len(row["console_scripts"]) or
                    set(scripts) != declared):
                raise ValueError("missing or undeclared console entry point")
            for pointer in row["console_scripts"]:
                path = roots[pointer["root"]] / pointer["path"]
                owners = {id(owner) for owner in distributions
                          if any(Path(os.path.abspath(owner.locate_file(file))) == path
                                 for file in (owner.files or []))}
                if owners != {id(dist)}:
                    raise ValueError("console wrapper has foreign or duplicate ownership")
                _console_binding(path, scripts[path.name], package)
            answer.update(verified=True, module_origin=expected,
                          metadata_origin=str(metadata), console_scripts=sorted(scripts))
        except Exception as exc:  # noqa: BLE001 - imports are classified, never accepted on error
            answer.update(verified=False, error=type(exc).__name__)
        bindings[name] = answer
    return bindings


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
    boot, snapshot = _boot_snapshot()
    isolated_site = bool(sys.flags.no_site)
    site_after_guard = False
    if boot["mode"] == "legacy" or snapshot is not None:
        # Built-in targets start with -S so no executable .pth can precede the
        # immutable verifier. Only then activate the genuine target site. A
        # custom runner that already initialized site cannot earn this boundary.
        if snapshot is not None:
            sys.dont_write_bytecode = True
        if isolated_site:
            import site

            site.main()
            site_after_guard = True
    prepended = []
    for path in spec.get("extra_syspath", []) if boot["mode"] == "legacy" else []:
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
        "boot": boot,
        "bindings": {},
        "site_initialized_after_guard": site_after_guard,
    }

    if snapshot is not None:
        report["bindings"] = _active_bindings(snapshot)
        boot["verified"] = all(row["verified"] for row in report["bindings"].values())
    if boot["mode"] != "legacy" and not boot.get("verified"):
        _print_report(report)
        return

    for distribution in spec.get("distributions", []):
        report["installed"][distribution] = _installed_version(distribution)

    for distribution, clone_dir in sorted(spec.get("overlay", {}).items()) if boot["mode"] == "legacy" else []:
        answer = _clone_version(clone_dir)
        answer["clone"] = clone_dir
        report["overlay"][distribution] = answer

    probes = spec.get("import_probes", [])
    if probes:
        report["django_bootstrap"] = _bootstrap_django()
        for probe in probes:
            report["imports"].append(_probe_import(probe["module"], probe.get("attrs", [])))

    _print_report(report)


def _print_report(report):
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
