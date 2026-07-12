#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SciTeX Hub Branding Constants - Single Source of Truth

All site-wide branding text should be defined here and referenced
via Django settings or context processors.

This module is deliberately PURE PYTHON (no Django import), so the tab-title
and favicon policy below can be lifted verbatim into a shared SciTeX package
(scitex-ui) once that package grows a branding surface -- see the module note
in ``favicon_for_env``.
"""

# Core branding
SITE_NAME = "SciTeX"
SITE_TAGLINE = "Research Automation for AI and Humans"
SITE_DESCRIPTION = (
    "Python toolkit + MCP server for literature search, "
    "statistics, visualization, and manuscript writing."
)

# Meta descriptions for SEO
META_DESCRIPTION_DEFAULT = f"{SITE_NAME} - {SITE_TAGLINE}"
META_DESCRIPTION_LONG = (
    f"{SITE_NAME}: {SITE_TAGLINE}. "
    "An integrated ecosystem of tools from hypothesis to publication."
)

# Social media / Open Graph
OG_TITLE = f"{SITE_NAME} - {SITE_TAGLINE}"
OG_DESCRIPTION = META_DESCRIPTION_LONG


# ---------------------------------------------------------------------------
# Deployment environments
# ---------------------------------------------------------------------------
ENV_DEVELOPMENT = "development"
ENV_STAGING = "staging"
ENV_PRODUCTION = "production"

KNOWN_ENVS = (ENV_DEVELOPMENT, ENV_STAGING, ENV_PRODUCTION)

_ENV_ALIASES = {
    "dev": ENV_DEVELOPMENT,
    "stag": ENV_STAGING,
    "prod": ENV_PRODUCTION,
}


def normalize_env(value):
    """Normalize an environment name to one of ``KNOWN_ENVS``.

    Raises ``ValueError`` on an unrecognized value. This is deliberate: a
    typo'd environment must fail loudly at boot rather than silently falling
    back to a default and serving the WRONG environment's favicon -- which
    would defeat the entire point of colour-coding the tab icon.
    """
    key = (value or "").strip().lower()
    key = _ENV_ALIASES.get(key, key)
    if key not in KNOWN_ENVS:
        raise ValueError(
            f"Unknown SciTeX environment {value!r}. "
            f"Expected one of {KNOWN_ENVS} "
            f"(aliases: {sorted(_ENV_ALIASES)})."
        )
    return key


# ---------------------------------------------------------------------------
# App mode: hub-embedded vs standalone
# ---------------------------------------------------------------------------
# The same SciTeX app (e.g. Writer) can run EMBEDDED in the hub or STANDALONE
# (e.g. `scitex-writer gui` on its own port). The tab must tell them apart.
MODE_HUB = "hub"
MODE_STANDALONE = "standalone"

KNOWN_MODES = (MODE_HUB, MODE_STANDALONE)


def normalize_mode(value):
    """Normalize an app mode to one of ``KNOWN_MODES``; raise on unknown."""
    key = (value or "").strip().lower()
    if key not in KNOWN_MODES:
        raise ValueError(
            f"Unknown SciTeX app mode {value!r}. Expected one of {KNOWN_MODES}."
        )
    return key


# ---------------------------------------------------------------------------
# Favicon: the tab ICON encodes the ENVIRONMENT
# ---------------------------------------------------------------------------
# All three are the SAME brand mark (the SciTeX snake) and differ ONLY in
# colour, so the tab icon alone tells you which deployment you are looking at:
#
#     production  -> white snake on NAVY        (the official product look)
#     staging     -> NAVY snake on WHITE        (heavy / high-contrast)
#     development -> white snake on GREEN
#
# These SVGs are produced by the existing brand-mark generator,
# ``scripts/utils/icons/generate_scitex_icons.py`` (which owns the snake path
# and the SciTeX palette), so the icons stay consistent with the rest of the
# ecosystem's iconography instead of being hand-drawn one-offs.
_ICON_DIR = "shared/images/scitex_logos/scitex-icons/generated"

FAVICON_BY_ENV = {
    ENV_PRODUCTION: f"{_ICON_DIR}/scitex-icon-white-bg-navy.svg",
    ENV_STAGING: f"{_ICON_DIR}/scitex-icon-navy-bg-white.svg",
    ENV_DEVELOPMENT: f"{_ICON_DIR}/scitex-icon-white-bg-green.svg",
}


def favicon_for_env(env):
    """Return the static-relative favicon path for ``env``.

    Raises ``ValueError`` on an unknown environment (see ``normalize_env``).
    """
    return FAVICON_BY_ENV[normalize_env(env)]


# ---------------------------------------------------------------------------
# Tab titles: the tab TEXT names the app, the brand, and the context
# ---------------------------------------------------------------------------
# One pattern, applied everywhere:
#
#     <Detail> · <App> — SciTeX            hub, production
#     <App> — SciTeX (dev)                 hub, development
#     <App> — SciTeX (staging)             hub, staging
#     <App> — SciTeX (standalone)          standalone app, any environment
#
# The product name is ALWAYS exactly "SciTeX"; app names are ALWAYS
# Capitalized. The version is deliberately NOT in the title -- it belongs in
# the UI chrome, not in every tab.
TITLE_SEPARATOR = " — "  # em dash, between the app and the brand
DETAIL_SEPARATOR = " · "  # middle dot, between the detail and the app

# URL prefix -> Capitalized app name. The single source of truth for how a
# SciTeX app is spelled in a tab. Capitalization here is the contract:
# "Todo", never "todo"; "FigRecipe", never "figrecipe".
APP_NAMES = {
    "/scholar/": "Scholar",
    "/writer/": "Writer",
    "/figrecipe/": "FigRecipe",
    "/console/": "Console",
    "/todo/": "Todo",
    "/clew/": "Clew",
    "/discovery/": "Discovery",
    "/store/": "Store",
    "/docs/": "Docs",
    "/tools/": "Tools",
}

# Hub sections that are not products, but still need a stable tab label.
SECTION_NAMES = {
    "/explore/": "Explore",
    "/social/explore/": "Explore",
    "/browse/": "Files",
    "/tree/": "Files",
}

# Everything that can name a tab. Apps win over sections on an exact tie;
# in practice their prefixes are disjoint.
PATH_LABELS = {**SECTION_NAMES, **APP_NAMES}

# Environment -> the parenthetical shown in the tab. Production is unmarked:
# the public site reads simply "<App> — SciTeX".
ENV_MARKERS = {
    ENV_PRODUCTION: None,
    ENV_STAGING: "staging",
    ENV_DEVELOPMENT: "dev",
}


def app_for_path(path):
    """Return the Capitalized app/section name owning ``path``, or ``None``.

    Longest prefix wins, so a nested path (``/social/explore/``) cannot be
    shadowed by a shorter one (``/explore/``).
    """
    path = path or ""
    match = None
    for prefix, name in PATH_LABELS.items():
        if path.startswith(prefix) and (match is None or len(prefix) > len(match[0])):
            match = (prefix, name)
    return match[1] if match else None


def title_marker(env, mode=MODE_HUB):
    """Return the tab's parenthetical marker, or ``None`` for none.

    A STANDALONE app is marked as such regardless of environment: "which app
    am I in" dominates "which deployment", and a standalone app is not part of
    a hub deployment in the first place.
    """
    if normalize_mode(mode) == MODE_STANDALONE:
        return MODE_STANDALONE
    return ENV_MARKERS[normalize_env(env)]


def page_title(app=None, detail=None, *, env, mode=MODE_HUB):
    """Build the browser tab title.

    Args:
        app: Capitalized app name (e.g. ``"Writer"``), or ``None`` outside an
            app (the landing page, settings, ...).
        detail: optional page-level detail (a project slug, a username).
        env: one of ``KNOWN_ENVS`` (required -- callers pass
            ``settings.SCITEX_ENV``; there is no implicit default, so a
            missing environment is a loud error, not a wrong-coloured tab).
        mode: one of ``KNOWN_MODES``; defaults to hub-embedded.

    Returns:
        e.g. ``"my-project · Writer — SciTeX (dev)"``.
    """
    marker = title_marker(env, mode)
    brand = f"{SITE_NAME} ({marker})" if marker else SITE_NAME

    lead = [part for part in (detail, app) if part]
    if not lead:
        return brand
    return DETAIL_SEPARATOR.join(lead) + TITLE_SEPARATOR + brand
