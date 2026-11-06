"""Read the development installer's declarations without running its shell."""

import os
import posixpath
import re


def is_direct_service(document, service):
    entrypoint = service.get("entrypoint") or []
    if isinstance(entrypoint, str):
        entrypoint = [entrypoint]
    return document.get("name") == "scitex-hub-dev" and any(
        part == "/app/deployment/docker/docker_dev/entrypoint.sh" for part in entrypoint
    )


def requested_roots(installer):
    """Use the same extras and last declaration that the installer requests."""
    result = {}
    pattern = (
        r'^\s*try_editable_install\s+"([^"\n]+)"\s+"([^"\n]+)"(?:\s+"([^"\n]+)")?\s*$'
    )
    for target, distribution, extras in re.findall(pattern, installer, re.MULTILINE):
        if not re.fullmatch(r"/[A-Za-z0-9_-]+", target):
            raise ValueError("invalid installer source target")
        if extras and not re.fullmatch(r"\[[A-Za-z0-9_,.-]+\]", extras):
            raise ValueError("invalid installer extras")
        result[target] = {"distribution": distribution, "extras": extras}
    if not result or 'ECOSYSTEM_EDITABLE_EXTRAS["/app"]="[all]"' not in installer:
        raise ValueError("development installer declarations are not understood")
    if '"/scitex-python[all]"' not in installer:
        raise ValueError("umbrella install declaration is not understood")
    result["/app"] = {"distribution": "scitex-hub", "extras": "[all]"}
    result["/scitex-python"] = {"distribution": "scitex", "extras": "[all]"}
    return result


def source_roots(document, roles):
    """Only package-source binds enter the probe; user and service mounts do not."""
    maps = []
    for row in roles.values():
        mounts = row["service"].get("volumes", [])
        if not isinstance(mounts, list):
            raise ValueError("development volumes are not resolved")
        mapping = {}
        for mount in mounts:
            if not isinstance(mount, dict):
                raise ValueError("development volume is not resolved")
            target = mount.get("target")
            if not isinstance(target, str) or not target.startswith("/"):
                raise ValueError("development mount target is not resolved")
            target = posixpath.normpath(target)
            protected = (
                "/usr/local/lib",
                "/usr/local/bin",
                "/opt/scitex-image-contract",
                "/opt/scitex-frontend",
                "/entrypoint.sh",
                "/root-init.sh",
                "/image-runtime.sh",
            )
            if any(
                target == path
                or target.startswith(path + "/")
                or path.startswith(target.rstrip("/") + "/")
                for path in protected
            ):
                raise ValueError(
                    "development source profile cannot model runtime-code overlays"
                )
            allowed_state = (
                "/app/data",
                "/app/media",
                "/app/staticfiles",
                "/app/.cache",
                "/app/.jsbuild",
                "/app/logs",
                "/app/.scitex",
                "/app/singularity",
            )
            if target.startswith("/app/") and not any(
                target == path or target.startswith(path + "/")
                for path in allowed_state
            ):
                raise ValueError(
                    "development application code has a nested unmodelled overlay"
                )
            if target in mapping:
                raise ValueError("duplicate development mount target")
            mapping[target] = mount
        maps.append(mapping)
    app = maps[0].get("/app", {})
    root = app.get("source")
    if (
        app.get("type") != "bind"
        or not isinstance(root, str)
        or not os.path.isabs(root)
    ):
        raise ValueError("development requires its declared application source bind")
    path = os.path.join(root, "deployment/docker/docker_dev/install_ecosystem.sh")
    with open(path, encoding="utf-8") as stream:
        requested = requested_roots(stream.read())
    result = {}
    for target, specification in requested.items():
        values = [mapping.get(target) for mapping in maps]
        if all(value is None for value in values):
            continue
        if any(not isinstance(value, dict) for value in values):
            raise ValueError("development Python roles disagree on source mounts")
        sources = {value.get("source") for value in values}
        if len(sources) != 1 or any(value.get("type") != "bind" for value in values):
            raise ValueError("development Python source binds disagree")
        source = sources.pop()
        if (
            not isinstance(source, str)
            or not os.path.isabs(source)
            or any(c in source for c in ",:\x00")
        ):
            raise ValueError("development source is not a usable absolute path")
        # Exactly the validity boundary used by try_editable_install.
        if not any(
            os.path.isfile(os.path.join(source, name))
            for name in ("pyproject.toml", "setup.py")
        ):
            continue
        result[target] = dict(specification, source=source)
    if "/app" not in result:
        raise ValueError("application source is not a Python package")
    allowed_paths = {"/app", "/app/apps"} | {target + "/src" for target in result}
    for row in roles.values():
        value = row["service"]["environment"].get("PYTHONPATH")
        if value is not None and (
            not isinstance(value, str)
            or any(
                path and posixpath.normpath(path) not in allowed_paths
                for path in value.split(":")
            )
        ):
            raise ValueError("development PYTHONPATH contains an unmodelled source")
    return result
