#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refuse the recreate BEFORE the outage, not during it.

WHY THIS EXISTS
---------------
The same trap fired twice on production scitex.ai inside five days.

  2026-08-18  A module-scope import of a symbol added in scitex-writer 2.42.0 was
              deployed against an image holding 2.41.0. Django raised ImportError
              at startup, restart-looped, and the site served 503 for ~25 minutes.
  2026-08-22  scitex-sh and scitex-decorators were absent from the prod image, so
              ``import scitex.io`` failed and the PUBLIC /api/plot/ endpoint
              returned 500 to every well-formed request. (Control: malformed
              requests correctly returned 400 throughout, so the endpoint was
              reached and the 500 was the import, not the routing.)

Both were repaired by installing a package INTO THE RUNNING CONTAINER, and both
repairs live only in that container's writable layer -- ``docker diff`` reports
them as 'A'. The next ``up -d --force-recreate`` deletes them. The outage is one
recreate away.

The incident card names the root cause itself: "The root cause is not the import.
It is that nothing checks." Until this script, the check was "somebody remembers",
and the agent that remembered was down 2026-08-19..08-22 -- precisely when
remembering fails.

WHAT IT DOES
------------
  1. Derives every sibling package hub imports at MODULE SCOPE, by walking the
     repo with ``ast`` (not by keeping a list that rots).
  2. Asks THE TARGET DEPLOYMENT -- the image the next recreate will run, plus the
     boot overlay that image gets at container start -- what it actually has.
  3. Compares against the floors hub declares in pyproject.toml, including the
     optional-dependency groups the prod image installs.
  4. Executes those imports inside the target, because the 2026-08-22 packages
     are declared in no pyproject anywhere in the chain and a floor comparison is
     structurally blind to them.
  5. Refuses, naming package / wanted / found / remedy, before anything
     irreversible happens.

WHAT IT DELIBERATELY HAS NO ESCAPE HATCH FOR
--------------------------------------------
There is no ``--warn-only`` and no skip environment variable. A gate that can be
switched off at the moment it goes red is the gate that was already here:
``deployment/docker/common/lib/scitex.src:10`` runs ``python -c "import scitex"``
with stderr discarded, which is GREEN on the very image that raises ImportError on
``import scitex.io`` -- and it runs after the recreate, where it can only report
an outage it was too late to prevent.

Exit codes:  0 satisfied  |  1 REFUSED  |  2 target unreachable  |  3 bad usage
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import preflight_declarations as declarations  # noqa: E402
import preflight_targets as targets  # noqa: E402
import preflight_versions as versions  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PROBE = os.path.join(HERE, "preflight_probe.py")
DEFAULT_CONTRACT = os.path.join(HERE, "preflight_contract.json")

RED, GREEN, YELLOW, CYAN, BOLD, NC = (
    ("\033[0;31m", "\033[0;32m", "\033[0;33m", "\033[0;36m", "\033[1m", "\033[0m")
    if sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    else ("", "", "", "", "", "")
)

REMEDY_FLOOR = (
    "bump what the IMAGE installs so it satisfies the declared floor -- the pin block in\n"
    "                     deployment/docker/docker_prod/Dockerfile.prod runs AFTER `uv pip install \".[all]\"`\n"
    "                     and overrides it, so a stale pin silently wins. Then rebuild.\n"
    "                     If the floor itself is wrong, lower it in pyproject.toml -- but never lower a floor\n"
    "                     to quiet this gate: the floor is what hub's own code needs in order to import."
)
REMEDY_ABSENT = (
    "install the distribution into the IMAGE (Dockerfile.prod), not into the running container.\n"
    "                     Measured 2026-08-22: `docker diff` showed the container-level hotfix packages as 'A'\n"
    "                     in the writable layer only, so `up -d --force-recreate` deletes them and the outage\n"
    "                     returns. If nothing declares this package, add it to hub's pyproject.toml as well,\n"
    "                     so the next resolver run keeps it."
)
REMEDY_IMPORT = (
    "install what provides this module into the IMAGE and re-run the preflight.\n"
    "                     A `pip install` inside the running container does NOT fix this: it lives in the\n"
    "                     writable layer and the next recreate erases it. If the module comes from a\n"
    "                     boot-overlaid app (.scitex-apps.json), fix the clone on the apps volume instead."
)


class Finding(object):
    def __init__(self, severity, subject, lines, remedy):
        self.severity = severity  # "fail" | "unknown" | "advisory"
        self.subject = subject
        self.lines = lines
        self.remedy = remedy


def _load_contract(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _is_sibling_distribution(name, contract):
    if name in set(contract.get("ignore_distributions", [])):
        return False
    if name in set(contract.get("sibling_distributions", [])):
        return True
    return any(name.startswith(p) for p in contract.get("sibling_distribution_prefixes", []))


def _effective(name, report):
    """(version, source) for what the target will actually have, or an UNKNOWN.

    The boot overlay wins over the image because that is the measured precedence:
    install_apps.sh editable-installs the clone at every container start, on top
    of whatever wheel the image baked in.
    """
    overlay = report.get("overlay", {}).get(name)
    if overlay and "version" in overlay:
        return overlay["version"], "boot overlay clone {0}".format(overlay.get("clone", "?"))
    if overlay and "unknown" in overlay:
        return None, "UNKNOWN: {0}".format(overlay["unknown"])
    installed = report.get("installed", {}).get(name)
    if installed is None:
        return None, "UNKNOWN: the target was never asked about this distribution"
    if "version" in installed:
        return installed["version"], "installed in the target"
    if installed.get("absent"):
        return None, "ABSENT"
    return None, "UNKNOWN: {0}".format(installed.get("unknown", "unreadable"))


def _evaluate_floors(floors, report, contract):
    findings, passes = [], []
    for name in sorted(floors):
        if not _is_sibling_distribution(name, contract):
            continue
        floor = floors[name]
        version, source = _effective(name, report)
        if version is None and source == "ABSENT":
            findings.append(Finding("fail", name, [
                ("hub declares", "{0}  (pyproject.toml:{1}, [{2}])".format(
                    floor.declaration, floor.line_number, floor.group)),
                ("target has", "NOTHING -- no distribution metadata for {0}".format(name)),
            ], REMEDY_ABSENT))
            continue
        if version is None:
            findings.append(Finding("unknown", name, [
                ("hub declares", "{0}  (pyproject.toml:{1}, [{2}])".format(
                    floor.declaration, floor.line_number, floor.group)),
                ("target has", source),
            ], "make the target answerable, then re-run. An unread floor is not a satisfied floor."))
            continue
        try:
            ok = versions.satisfies(version, floor.specifier)
        except versions.Undecidable as exc:
            findings.append(Finding("unknown", name, [
                ("hub declares", floor.declaration),
                ("target has", "{0}  ({1})".format(version, source)),
                ("comparison", "UNDECIDABLE: {0}".format(exc)),
            ], "the version or the specifier is not PEP 440 comparable; fix whichever is malformed."))
            continue
        if ok:
            passes.append((name, floor.declaration, version, source))
        else:
            findings.append(Finding("fail", name, [
                ("hub declares", "{0}  (pyproject.toml:{1}, [{2}])".format(
                    floor.declaration, floor.line_number, floor.group)),
                ("target has", "{0}  ({1})".format(version, source)),
                ("verdict", "{0} does NOT satisfy {1}".format(version, floor.specifier)),
            ], REMEDY_FLOOR))
    return findings, passes


def _build_probes(imports, contract):
    """Derived module-scope imports first, then the contract's explicit extras."""
    probes, seen = [], set()
    for item in imports:
        key = (item.module, ())
        if key in seen:
            continue
        seen.add(key)
        probes.append({
            "module": item.module,
            "attrs": [],
            "required": not item.guarded,
            "origin": "{0} (module scope, {1})".format(
                item.where, "unguarded" if item.guarded is False else "guarded by try/except"),
        })
    for extra in contract.get("extra_import_probes", []):
        key = (extra["module"], tuple(extra.get("attrs", [])))
        if key in seen:
            continue
        seen.add(key)
        why = (extra.get("why", "") or "").split(". ")[0]
        probes.append({
            "module": extra["module"],
            "attrs": list(extra.get("attrs", [])),
            "required": True,
            "origin": "preflight_contract.json -- {0}".format(why),
        })
    return probes


def _evaluate_imports(probes, report):
    by_key = {}
    for result in report.get("imports", []):
        by_key[(result["module"], tuple(result.get("attrs", [])))] = result
    findings, ok_count, inconclusive = [], 0, []
    for probe in probes:
        result = by_key.get((probe["module"], tuple(probe["attrs"])))
        label = probe["module"] + ("".join(".{0}".format(a) for a in probe["attrs"]))
        if result is None:
            findings.append(Finding("unknown", label, [
                ("target", "never answered for this probe"),
            ], "the probe did not run; re-run the preflight."))
            continue
        status = result.get("status")
        if status == "ok":
            ok_count += 1
            continue
        detail = "{0}: {1}".format(result.get("error_type"), result.get("error"))
        if status == "inconclusive":
            inconclusive.append((label, detail))
            continue
        severity = "fail" if probe["required"] else "advisory"
        findings.append(Finding(severity, label, [
            ("imported at", probe["origin"]),
            ("target raises", detail),
        ], REMEDY_IMPORT if probe["required"] else
            "guarded by try/except, so hub degrades rather than crash-looping -- but it IS degrading."))
    return findings, ok_count, inconclusive


def _render_findings(title, findings, stream):
    if not findings:
        return
    stream.write("\n  {0}{1} ({2}){3}\n".format(BOLD, title, len(findings), NC))
    for finding in findings:
        stream.write("    {0}{1}{2}\n".format(BOLD, finding.subject, NC))
        for key, value in finding.lines:
            stream.write("      {0:<14}: {1}\n".format(key, value))
        stream.write("      {0:<14}: {1}\n".format("remedy", finding.remedy))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Refuse a container recreate whose target cannot satisfy hub's declared floors.",
    )
    parser.add_argument("--env", choices=["dev", "staging", "prod"],
                        help="derive the target names for this environment")
    parser.add_argument("--target", help="image:<ref> | container:<name> | local | cmd:<argv>")
    parser.add_argument("--apps-volume", help="docker volume holding the boot-overlay clones")
    parser.add_argument("--apps-manifest", default=os.path.join(REPO_ROOT, ".scitex-apps.json"))
    parser.add_argument("--pyproject", default=os.path.join(REPO_ROOT, "pyproject.toml"))
    parser.add_argument("--repo-root", default=REPO_ROOT)
    parser.add_argument("--contract", default=DEFAULT_CONTRACT)
    parser.add_argument("--extra", action="append", default=None,
                        help="pyproject optional-dependency group to include (default: the contract's)")
    parser.add_argument("--via-ssh", help="run the docker command on this host over ssh")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--verbose", action="store_true", help="also list every satisfied floor")
    parser.add_argument("--json", dest="as_json", action="store_true", help="emit the raw target report")
    args = parser.parse_args(argv)

    out = sys.stdout
    try:
        contract = _load_contract(args.contract)
    except Exception as exc:  # noqa: BLE001
        out.write("{0}preflight: cannot read contract {1}: {2}{3}\n".format(RED, args.contract, exc, NC))
        return 3

    target_spec, apps_volume = args.target, args.apps_volume
    if args.env and not target_spec:
        target_spec = "image:scitex-hub-{0}-django:latest".format(args.env)
        if apps_volume is None:
            apps_volume = "scitex-hub-{0}_apps_volume".format(args.env)
    if not target_spec:
        out.write("{0}preflight: one of --env or --target is required{1}\n".format(RED, NC))
        return 3

    extras = args.extra if args.extra is not None else contract.get("prod_image_extras", [])

    try:
        floors = declarations.declared_floors(args.pyproject, extras)
        imports, files_scanned = declarations.module_scope_sibling_imports(args.repo_root, contract)
    except declarations.DeclarationError as exc:
        out.write("{0}preflight: cannot read hub's declarations: {1}{2}\n".format(RED, exc, NC))
        return 3

    # Controls. An empty floor set and an empty import set are indistinguishable
    # from "everything is fine" unless the readers prove they read something.
    if not floors:
        out.write("{0}preflight: parsed ZERO floors from {1}; the comparison would be "
                  "vacuously green{2}\n".format(RED, args.pyproject, NC))
        return 3
    if not files_scanned:
        out.write("{0}preflight: the import scan read ZERO files under {1}; it would report "
                  "no imports whatever the code does{2}\n".format(RED, args.repo_root, NC))
        return 3

    probes = _build_probes(imports, contract)
    sibling_floors = {n: f for n, f in floors.items() if _is_sibling_distribution(n, contract)}

    try:
        target = targets.resolve(target_spec, apps_volume, args.apps_manifest, args.via_ssh)
        spec = {
            "distributions": sorted(sibling_floors),
            "overlay": target.overlay,
            "extra_syspath": target.extra_syspath,
            "import_probes": [{"module": p["module"], "attrs": p["attrs"]} for p in probes],
        }
        report = targets.interrogate(target, open(PROBE, encoding="utf-8").read(), spec, args.timeout)
    except targets.TargetUnreachable as exc:
        out.write("\n{0}{1}❌ DEPLOY REFUSED -- the target could not be interrogated.{2}\n".format(RED, BOLD, NC))
        out.write("   {0}\n".format(exc))
        out.write("\n   Unknown is not OK. This preflight exists because a package was once verified\n"
                  "   somewhere other than production and the result was stated about production.\n")
        return 2

    if args.as_json:
        out.write(json.dumps(report, indent=2, sort_keys=True) + "\n")

    floor_findings, floor_passes = _evaluate_floors(floors, report, contract)
    import_findings, import_ok, inconclusive = _evaluate_imports(probes, report)
    findings = floor_findings + import_findings
    fails = [f for f in findings if f.severity == "fail"]
    unknowns = [f for f in findings if f.severity == "unknown"]
    advisories = [f for f in findings if f.severity == "advisory"]

    out.write("\n{0}SIBLING FLOOR + IMPORT PREFLIGHT{1}\n".format(BOLD, NC))
    out.write("  target interrogated : {0}\n".format(target.description))
    out.write("  interrogated by     : {0}\n".format(target.command))
    out.write("  target python       : {0} at {1}\n".format(
        report.get("python_version", "?"), report.get("executable", "?")))
    out.write("  declared floors from: {0}  ([project.dependencies]{1})\n".format(
        args.pyproject, "".join(" + [{0}]".format(e) for e in extras)))
    out.write("  module-scope scan   : {0} sibling imports across {1} files under {2}\n".format(
        len(imports), files_scanned, ", ".join(contract.get("scan_dirs", []))))
    out.write("  checked             : {0} sibling floors, {1} import probes ({2} comparator)\n".format(
        len(sibling_floors), len(probes), versions.BACKEND))
    if report.get("syspath_prepended"):
        out.write("  boot overlay        : {0}\n".format(", ".join(report["syspath_prepended"])))

    if not target.is_target_check:
        out.write("\n{0}{1}  !! THIS IS NOT A TARGET CHECK !!{2}\n".format(YELLOW, BOLD, NC))
        out.write("{0}  --target local interrogates the shell this script is running in, which is\n"
                  "  the exact mistake that took scitex.ai down on 2026-08-18. Its result says\n"
                  "  NOTHING about what production will run. Do not gate a deploy on it.{1}\n".format(YELLOW, NC))

    if args.verbose and floor_passes:
        out.write("\n  {0}SATISFIED ({1}){2}\n".format(BOLD, len(floor_passes), NC))
        for name, declaration, version, source in floor_passes:
            out.write("    {0}{1:<22}{2} wants {3:<26} has {4:<12} ({5})\n".format(
                GREEN, name, NC, declaration, version, source))

    _render_findings("FLOOR UNSATISFIED", [f for f in fails if f in floor_findings], out)
    _render_findings("COULD NOT BE DETERMINED", unknowns, out)
    _render_findings("IMPORT FAILS INSIDE THE TARGET", [f for f in fails if f in import_findings], out)
    _render_findings("DEGRADED BUT GUARDED (not fatal)", advisories, out)

    if inconclusive:
        out.write("\n  {0}INCONCLUSIVE ({1}) -- module found, but raised a non-import error{2}\n".format(
            BOLD, len(inconclusive), NC))
        for label, detail in inconclusive:
            out.write("    {0:<44} {1}\n".format(label, detail))
        bootstrap = report.get("django_bootstrap") or {}
        out.write("    (django bootstrap in target: {0})\n".format(bootstrap.get("detail", "not attempted")))

    out.write("\n")
    if fails or unknowns:
        out.write("{0}{1}❌ DEPLOY REFUSED -- {2} unsatisfied, {3} undetermined.{4}\n".format(
            RED, BOLD, len(fails), len(unknowns), NC))
        out.write("{0}   Nothing has been recreated. Fix the target, not this gate: on 2026-08-18 and\n"
                  "   again on 2026-08-22 this exact condition reached production and the site went\n"
                  "   down, because nothing checked.{1}\n".format(RED, NC))
        return 1

    out.write("{0}✅ target satisfies every declared sibling floor ({1} checked) and imports "
              "cleanly ({2}/{3} probes).{4}\n".format(GREEN, len(sibling_floors), import_ok, len(probes), NC))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# EOF
