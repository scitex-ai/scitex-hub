"""Project installed application owners into the documentation dispatcher.

The SDK owns installed GUI declarations; Dev owns leaf docs/skills discovery.
This host adapter reads metadata only, never loading an app entry point.
"""

from importlib.metadata import PackageNotFoundError, distribution
from threading import RLock
import re

from packaging.utils import canonicalize_name


_REGISTRATION_LOCK = RLock()


def register_installed_app_docs(pages, by_slug, *, modules=None, plugins=None):
    """Keep every installed application owner reachable, even without docs.

    Host-authored pages retain their existing slugs. Built-in host panes use
    their existing guides; this projection adds installed leaf applications.
    Multiple mounted views of one package can share its declared capabilities.
    """
    if modules is None:
        from apps.infra.workspace_app.registry import get_all_modules

        modules = get_all_modules()
    if plugins is None:
        from scitex_sdk.app.plugins import discover_plugin_apps

        plugins = discover_plugin_apps()
    modules, plugins = list(modules), list(plugins)
    candidates = []
    mounted_owners = set()
    for mod in modules:
        owner = getattr(mod, "pip_package", "")
        if not owner:
            continue
        owner = canonicalize_name(owner, validate=True)
        mounted_owners.add(owner)
        if owner == "scitex-hub" or (mod.docs_slug and mod.docs_slug in by_slug):
            continue
        candidates.append((mod.name, mod.label, owner))
    for plugin in plugins:
        owner = plugin.distribution
        if not owner:
            continue
        owner = canonicalize_name(owner, validate=True)
        if owner not in mounted_owners:
            candidates.append((plugin.name, plugin.name, owner))
    for name, label, owner in candidates:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            continue
        slug = "app-" + name
        if slug in by_slug:
            continue
        try:
            distribution(owner)
        except PackageNotFoundError:
            # A stale host manifest is not an installed app declaration.
            continue
        with _REGISTRATION_LOCK:
            if slug in by_slug:
                continue
            page = {
                "slug": slug,
                "label": label,
                "icon": "fas fa-puzzle-piece",
                "template": "docs_app/docs_installed_app.html",
                "badges": ["app"],
                "section": "apps",
                "distribution": owner,
            }
            pages.append(page)
            by_slug[slug] = page


def installed_app_context(page):
    """Read the owning Dev/SDK catalog; missing/ambiguous remains explicit."""
    from apps.infra.public_app.services.interface_catalog import build_interface_catalog

    owner = page["distribution"]
    return {
        "app_doc_label": page["label"],
        "app_doc_distribution": owner,
        "interface_catalog": build_interface_catalog(package=owner),
    }
