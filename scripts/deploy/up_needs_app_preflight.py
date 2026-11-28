#!/usr/bin/env python3
"""Does this ``compose up`` start anything built from the hub application image?

``compose.sh`` runs the sibling floor + import preflight before every ``up``.
That preflight interrogates the hub APPLICATION image (Django and the Celery
workers). Recreating a service that does not run that image -- gitea, an nginx
sidecar -- cannot be broken by a stale floor in that image, yet the gate used to
refuse it all the same. Measured 2026-11-27: ``up --no-deps gitea gitea_front``
was refused for 11 floors of the Django image while gitea was under a crawler
load the change was meant to stop.

This answers one question, and answers it conservatively. It prints ``skip``
ONLY when it can prove that every service the ``up`` would start or recreate
uses a literal third-party image with no ``build:`` -- something the hub never
builds. Every other case prints ``run``:

* a bare ``up`` (no service list means every service, the app ones included);
* any service named that uses an interpolated image (``${...}``, which is how the
  app image is wired) or has a ``build:`` section or an ``extends:``;
* any dependency of a named service reaching such a service, unless
  ``--no-deps`` is given (``depends_on``, ``links``, ``network_mode: service:``
  and ``volumes_from`` all start the other service);
* any option this script does not know, any positional that is not a service,
  and any compose file it cannot read or parse.

Usage: up_needs_app_preflight.py <docker_dir> "<compose_cmd>" up [up args...]
Exit status is 0 whenever an answer was printed; the caller acts on the word.
"""

import os
import shlex
import sys

# ``up`` flags that take no value and do not widen the set of services started.
_FLAGS = {
    "-d",
    "--detach",
    "--no-deps",
    "--no-build",
    "--build",
    "--force-recreate",
    "--no-recreate",
    "--always-recreate-deps",
    "--remove-orphans",
    "--renew-anon-volumes",
    "-V",
    "--wait",
    "--quiet-pull",
    "--no-color",
    "--no-log-prefix",
}

# Compose's default file names when no ``-f`` is given (override files merge in).
_DEFAULT_FILES = (
    "compose.yaml",
    "compose.yml",
    "docker-compose.yml",
    "docker-compose.yaml",
)
_OVERRIDE_FILES = (
    "compose.override.yaml",
    "compose.override.yml",
    "docker-compose.override.yml",
    "docker-compose.override.yaml",
)


class Undecidable(Exception):
    """Anything that prevents a proof; the answer is then ``run``."""


def compose_files(docker_dir, compose_cmd):
    argv = shlex.split(compose_cmd)
    named = [argv[i + 1] for i, tok in enumerate(argv[:-1]) if tok in ("-f", "--file")]
    if any(tok.startswith(("-f=", "--file=")) for tok in argv):
        raise Undecidable("compose file given in a form this script does not parse")
    if named:
        return [os.path.join(docker_dir, f) for f in named]
    base = [f for f in _DEFAULT_FILES if os.path.isfile(os.path.join(docker_dir, f))]
    if not base:
        raise Undecidable(f"no compose file in {docker_dir}")
    overrides = [
        f for f in _OVERRIDE_FILES if os.path.isfile(os.path.join(docker_dir, f))
    ]
    return [os.path.join(docker_dir, f) for f in base[:1] + overrides]


def load_services(paths):
    """``{name: [service dict from each file that defines it]}``."""
    try:
        import yaml
    except ImportError:
        raise Undecidable("PyYAML is not importable")
    services = {}
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                doc = yaml.safe_load(handle)
        except (OSError, yaml.YAMLError) as exc:
            raise Undecidable(f"cannot read {path}: {exc}")
        for name, svc in ((doc or {}).get("services") or {}).items():
            if not isinstance(svc, dict):
                raise Undecidable(f"service {name} is not a mapping")
            services.setdefault(name, []).append(svc)
    if not services:
        raise Undecidable("no services found")
    return services


def is_third_party(layers):
    """True only for a literal image the hub does not build, in every layer."""
    images = [layer.get("image") for layer in layers if "image" in layer]
    if any("build" in layer or "extends" in layer for layer in layers):
        return False
    if not images:
        return False
    return all(isinstance(img, str) and img and "$" not in img for img in images)


def dependencies(layers):
    deps = set()
    for layer in layers:
        dep = layer.get("depends_on") or []
        deps.update(dep.keys() if isinstance(dep, dict) else dep)
        for link in layer.get("links") or []:
            deps.add(str(link).split(":", 1)[0])
        mode = layer.get("network_mode") or ""
        if isinstance(mode, str) and mode.startswith("service:"):
            deps.add(mode[len("service:") :])
        for source in layer.get("volumes_from") or []:
            source = str(source)
            if source.startswith("container:"):
                continue
            deps.add(source.split(":", 1)[0])
    return deps


def parse_up_args(args):
    if not args or args[0] != "up":
        raise Undecidable("not an up invocation")
    names, no_deps = [], False
    for tok in args[1:]:
        if tok.startswith("-"):
            if tok not in _FLAGS:
                raise Undecidable(f"option {tok} is not modelled")
            no_deps = no_deps or tok == "--no-deps"
        else:
            names.append(tok)
    if not names:
        raise Undecidable("no service list: up starts every service")
    return names, no_deps


def decide(docker_dir, compose_cmd, up_args):
    names, no_deps = parse_up_args(up_args)
    services = load_services(compose_files(docker_dir, compose_cmd))
    started, todo = set(), list(names)
    while todo:
        name = todo.pop()
        if name in started:
            continue
        if name not in services:
            raise Undecidable(f"{name} is not a service in the compose files")
        started.add(name)
        if not no_deps:
            todo.extend(dependencies(services[name]))
    app = sorted(name for name in started if not is_third_party(services[name]))
    if app:
        return "run", "starts {0}".format(", ".join(app))
    return "skip", "only third-party images: {0}".format(", ".join(sorted(started)))


def main(argv):
    if len(argv) < 3:
        print("run")
        print(
            "usage: up_needs_app_preflight.py <docker_dir> <compose_cmd> up [args...]",
            file=sys.stderr,
        )
        return 0
    try:
        verdict, reason = decide(argv[0], argv[1], argv[2:])
    except Undecidable as exc:
        verdict, reason = "run", str(exc)
    print(verdict)
    print(f"[compose.sh] preflight {verdict}: {reason}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
