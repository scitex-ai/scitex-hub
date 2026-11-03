"""Public documentation projection of Dev/SDK provider metadata, never leaf code."""

from collections import Counter
from urllib.parse import quote, urlencode

from packaging.utils import canonicalize_name


def _distribution_name(value):
    # New Dev owns normalization; older installed Dev keeps metadata-only pages
    # readable while reporting the missing provider-discovery capability.
    import scitex_dev

    normalize = getattr(scitex_dev, "normalize_distribution_name", None)
    return (
        normalize(value)
        if callable(normalize)
        else canonicalize_name(value, validate=True)
    )


def api_docs_url(package):
    """Normalize an explicit registered distribution into the host docs route."""
    name = _distribution_name(package)
    return "/docs/web-api/?" + urlencode({"package": name})


def documentation_providers():
    try:
        import scitex_dev
    except ImportError:
        return (), "unavailable"

    discover = getattr(scitex_dev, "list_doc_providers", None)
    if not callable(discover):
        return (), "unavailable"
    try:
        return discover(), "available"
    except (ValueError, OSError):
        return (), "invalid"


def _api_providers():
    try:
        from scitex_sdk.app.api_plugin import (
            ApiPluginContractError,
            discover_api_plugins,
        )
    except ImportError:
        return (), "unavailable"

    try:
        return discover_api_plugins(), "available"
    except (ApiPluginContractError, ValueError, OSError):
        return (), "invalid"


def build_interface_catalog(
    package=None, *, docs=None, apis=None, descriptor_reader=None
):
    """Compose installed declarations without enabling routes or loading EPs.

    Explicit finite provider inputs also support owned metadata-fixture tests.
    Missing discovery support is unknown, never a fabricated empty catalog.
    """
    from scitex_sdk.app.api_mount import AdmissionDenied, read_inert_descriptor

    selected = _distribution_name(package) if package else ""
    docs, docs_state = (
        documentation_providers() if docs is None else (docs, "available")
    )
    apis, api_state = _api_providers() if apis is None else (apis, "available")
    read_descriptor = descriptor_reader or read_inert_descriptor
    duplicates = Counter(row.name for row in docs)
    packages = {}

    def owner(name):
        canonical = _distribution_name(name)
        return packages.setdefault(
            canonical,
            {
                "distribution": canonical,
                "version": None,
                "summary": "",
                "docs": [],
                "web_apis": [],
                "api_docs_url": api_docs_url(canonical),
                "skills_command": f"scitex-dev dev skills list --package {canonical} --json",
                "mcp_setup": "not_inspected",
            },
        )

    for row in docs:
        if not row.distribution:
            docs_state = "invalid"
            continue
        try:
            item = owner(row.distribution)
        except (ValueError, TypeError):
            docs_state = "invalid"
            continue
        item.update(version=row.version, summary=row.summary or "")
        ambiguous = duplicates[row.name] > 1
        # Provider names are URL path components, not filesystem inputs.
        try:
            canonicalize_name(row.name, validate=True)
            valid_name = True
        except ValueError:
            valid_name = False
        link = (
            ""
            if ambiguous or not valid_name
            else "/apps/docs/sphinx/" + quote(row.name, safe="") + "/index.html"
        )
        item["docs"].append(
            {
                "name": row.name,
                "target": row.target,
                "state": "ambiguous" if ambiguous or not valid_name else "registered",
                "url": link,
            }
        )

    for ref in apis:
        if not ref.distribution:
            api_state = "invalid"
            continue
        try:
            item = owner(ref.distribution)
        except (ValueError, TypeError):
            api_state = "invalid"
            continue
        declaration = {
            "name": ref.name,
            "target": ref.target,
            "state": "declaration_only",
            "operations": [],
        }
        try:
            descriptor = read_descriptor(ref.distribution)
            if descriptor is not None:
                if descriptor.id != ref.name:
                    raise ValueError("descriptor identity mismatch")
                fragment = descriptor.openapi_fragment()
                declaration["operations"] = [
                    {
                        "method": method.upper(),
                        "path": path,
                        "operation_id": operation["operationId"],
                    }
                    for path, methods in fragment["paths"].items()
                    for method, operation in methods.items()
                ]
                declaration["state"] = "inert_descriptor"
        except (AdmissionDenied, ValueError, OSError, TypeError):
            declaration["state"] = "invalid_descriptor"
        item["web_apis"].append(declaration)

    rows = [
        packages[name] for name in sorted(packages) if not selected or name == selected
    ]
    return {
        "schema_version": 1,
        "selected_package": selected,
        "docs_discovery": docs_state,
        "api_discovery": api_state,
        "packages": rows,
        "selected_not_registered": bool(
            selected and not rows and docs_state == api_state == "available"
        ),
        "host_admission": "not_observed",
        "live_availability": "not_probed",
    }
