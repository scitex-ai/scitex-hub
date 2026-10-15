#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub-side fallback for the SDK UI JavaScript catalog (fix-forward #1065).

WHY THIS EXISTS. The SDK App Creator wizard (``scitex_sdk.creator``,
mounted at /apps/new/) renders through ``scitex_sdk/app/app_shell.html``,
which extends ``scitex_sdk/ui/standalone_shell.html``. That shell embeds
``{% scitex_js_catalog "scitex_sdk.ui" %}``, whose ``js_catalog()`` calls
Django's ``JavaScriptCatalog.get_paths()`` — which only accepts
``app_config.name`` values from ``INSTALLED_APPS``.

The hub deliberately keeps ``scitex_sdk.ui`` OUT of ``INSTALLED_APPS``:
it claims label ``scitex_ui``, identical to the REQUIRED retired
``scitex-ui`` entry (still installed — required by scitex, scitex-cards,
scitex-writer), and Django 6 raises on duplicate labels AND duplicate
names, so neither the real entry nor a relabelled shim can be registered
(see config/settings/_optional_apps.py). The result is
``ValueError: Invalid package(s) provided to JavaScriptCatalog:
scitex_sdk.ui`` on every GET of the wizard.

WHY A FALLBACK, NOT THE OTHER OPTIONS. A hub template override would
vendor the whole 400-line SDK shell to neutralize one tag (drift on every
SDK bump). Registering the app is impossible per above. So: keep the
``libraries`` mapping on the SDK tag module (tests/config/
test_sdk_shell_bridge.py pins it) and make the tag's ``js_catalog``
lookup succeed by serving the package's own ``locale/`` dir directly —
the same ``<pkg>/locale`` path ``get_paths()`` would have returned had
the app been installed. Behaviour is byte-identical when every package
IS installed (the SDK implementation runs untouched); genuinely unknown
packages still raise the original ``ValueError``.

REMOVAL. Delete this (and the ready() hook) once the retired scitex-ui
requirement is dropped and ``scitex_sdk.ui`` registers normally, or once
the SDK stops cataloguing a non-installed package from its shell.
"""

from __future__ import annotations

#: The SDK's own ``js_catalog``, captured by :func:`install` BEFORE patching
#: (the patch replaces the module attribute, so a call-time import would
#: resolve to this module's wrapper and recurse forever).
_original_sdk_js_catalog = None


def safe_js_catalog(packages, language=None):
    """``scitex_sdk.ui.i18n.js_catalog`` with an uninstalled-package fallback.

    Falls back only on the ``ValueError`` ``get_paths()`` raises for
    packages outside ``INSTALLED_APPS``; every other error propagates.
    """
    from scitex_sdk.ui.i18n import JS_CATALOG_DOMAIN

    original = _original_sdk_js_catalog
    if original is None:
        # install() never ran, so nothing patched the SDK module: a fresh
        # import is the true original.
        from scitex_sdk.ui.i18n import js_catalog as original

    try:
        return original(packages, language=language)
    except ValueError:
        pass
    return _locale_dir_catalog(packages, language=language, domain=JS_CATALOG_DOMAIN)


def _locale_dir_catalog(packages, language=None, domain="djangojs"):
    """Build the ``{language, plural, catalog}`` payload without app registry.

    Installed packages resolve exactly as ``JavaScriptCatalog.get_paths()``
    would (``<app.path>/locale``); importable-but-uninstalled packages
    resolve to ``<package dir>/locale`` via importlib. Anything else keeps
    the original ``ValueError`` contract (same message shape).
    """
    from importlib import import_module
    from pathlib import Path

    from django.apps import apps
    from django.utils.translation import get_language
    from django.utils.translation.trans_real import DjangoTranslation
    from django.views.i18n import JavaScriptCatalog

    package_list = [packages] if isinstance(packages, str) else list(packages)
    resolved_language = language or get_language() or "en"
    installed = {cfg.name: cfg for cfg in apps.get_app_configs()}

    localedirs = []
    unresolvable = []
    for package in package_list:
        config = installed.get(package)
        if config is not None:
            localedirs.append(str(Path(config.path) / "locale"))
            continue
        try:
            module = import_module(package)
        except ImportError:
            unresolvable.append(package)
            continue
        module_file = getattr(module, "__file__", None)
        if not module_file:
            unresolvable.append(package)
            continue
        localedirs.append(str(Path(module_file).resolve().parent / "locale"))

    if unresolvable:
        raise ValueError(
            "Invalid package(s) provided to JavaScriptCatalog: %s"
            % ",".join(unresolvable)
        )

    catalog_view = JavaScriptCatalog(domain=domain, packages=[])
    catalog_view.translation = DjangoTranslation(
        resolved_language,
        domain=domain,
        localedirs=localedirs,
    )
    return {
        "language": resolved_language,
        "plural": catalog_view.get_plural(),
        "catalog": catalog_view.get_catalog(),
    }


_installed = False


def install():
    """Point the SDK tag module's ``js_catalog`` at :func:`safe_js_catalog`.

    The tag nodes look ``js_catalog`` up in their module globals at RENDER
    time, so patching the module attribute covers both the plain
    ``{% scitex_js_catalog %}`` function path and the dedup node path.
    No-op when the SDK is absent (the creator mount is ``[]`` then too).
    Idempotent per process.
    """
    global _installed, _original_sdk_js_catalog
    if _installed:
        return
    try:
        import scitex_sdk.ui.i18n as sdk_i18n
        import scitex_sdk.ui.templatetags.scitex_i18n as sdk_tags
    except ImportError:
        return
    if sdk_i18n.js_catalog is safe_js_catalog:
        _installed = True
        return
    _original_sdk_js_catalog = sdk_i18n.js_catalog
    sdk_tags.js_catalog = safe_js_catalog
    sdk_i18n.js_catalog = safe_js_catalog
    _installed = True


# EOF
