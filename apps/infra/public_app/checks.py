"""Boot-time guard for the ``VITE_USE_BUILD`` declaration.

``SCITEX_HUB_VITE_USE_BUILD=true`` is a promise: "ignore the Vite dev server,
serve the platform's TypeScript from the built manifest instead." Nothing has
ever checked that the build the promise refers to exists.

When it does not, the failure is silent in the worst possible way. The reader
(``vite.manifest_path`` -> ``get_manifest``) catches the missing-file
``OSError`` and returns ``{}``, so *every* platform entry misses. Under
``DEBUG`` the template tag then raises ``TemplateSyntaxError`` on the FIRST
page a visitor opens -- which, on a public preview host, renders Django's
technical 500: the settings table, and the locals of every frame.

Measured on compute-03 2026-09-06: the public dev preview answered every
route with a 254,257-byte debug page for four days, because this flag was set
on a stack whose entrypoint starts a Vite *dev server* and never runs
``vite build``. The settings module that accepts the flag already carries a
comment saying "Run `npm run build` first." Prose is not a gate. This is.

The constitution's rule is the one that applies: a declaration that cannot be
honoured must FAIL, not evaporate. Refusing at boot with the path that is
missing is strictly better than serving a debug page to the internet.
"""

from django.conf import settings
from django.core.checks import Error, register


@register("staticfiles")
def check_vite_build_exists_when_declared(app_configs, **kwargs):
    """``VITE_USE_BUILD`` must not be set without a build behind it."""
    if not getattr(settings, "VITE_USE_BUILD", False):
        # The dev server serves the TypeScript; no manifest is expected.
        return []

    # Imported here, not at module scope: this module is imported from
    # AppConfig.ready(), and the templatetag pulls in django.template, which
    # is not safe to touch before the app registry is populated.
    from apps.infra.public_app.templatetags.vite import manifest_path

    path = manifest_path()
    if path.is_file():
        return []

    return [
        Error(
            "VITE_USE_BUILD is on, but the Vite manifest it names does not "
            f"exist: {path}",
            hint=(
                "Nothing will serve the platform's JavaScript, and under "
                "DEBUG every page raises TemplateSyntaxError on its first "
                "{% vite_script %} tag -- which renders Django's technical "
                "500, settings table included. Either run `npm run build` "
                "(it writes build.outDir='staticfiles/vite' from "
                "vite.config.ts), or unset SCITEX_HUB_VITE_USE_BUILD so the "
                "Vite dev server on VITE_HOST_PORT serves the entries "
                "instead. Note the dev server emits script tags pointing at "
                "window.location.hostname, so it cannot serve a REMOTE "
                "visitor unless that port is published -- a reachable "
                "preview wants the build, not the dev server."
            ),
            obj="config/settings/settings_dev.py",
            id="public_app.E001",
        )
    ]
