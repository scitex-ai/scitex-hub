"""SciTeX App Tools — init, validate, develop, publish, and manage app plugins."""

from . import _ui as ui
from ._api import get_current, get_info, install_app, list_all, switch_to
from ._components import (
    SHARED_COMPONENTS,
    get_all_components,
    get_component,
    get_css_imports,
    get_ts_imports,
)
from ._deps import (
    build_container,
    check_deps,
    check_deps_from_manifest,
    format_missing_report,
    install_deps,
)
from ._launcher import dev_server
from ._prefs import delete_prefs, get_prefs, list_prefs, set_prefs

# Scaffold, validate, publish — canonical source is scitex-app.
# Import from scitex_app.appmaker, fall back to local copies.
try:
    from scitex_app.appmaker import init_app, validate
    from scitex_app.appmaker._publish import publish
    from scitex_app.appmaker._license import generate_license_text
    from scitex_app.appmaker._validate import (
        validate_css,
        validate_dependencies,
        validate_manifest,
        validate_security,
        validate_structure,
        validate_templates,
    )
except ImportError:
    from ._license import generate_license_text
    from ._publish import publish
    from ._scaffold import init_app
    from ._validate import (
        validate,
        validate_css,
        validate_dependencies,
        validate_manifest,
        validate_security,
        validate_structure,
        validate_templates,
    )

__all__ = [
    # init
    "init_app",
    # app management
    "get_current",
    "switch_to",
    "list_all",
    "get_info",
    "install_app",
    # dependencies
    "check_deps",
    "check_deps_from_manifest",
    "install_deps",
    "format_missing_report",
    "build_container",
    # preferences
    "get_prefs",
    "set_prefs",
    "delete_prefs",
    "list_prefs",
    # validate
    "validate",
    "validate_structure",
    "validate_security",
    "validate_manifest",
    "validate_templates",
    "validate_css",
    "validate_dependencies",
    # license
    "generate_license_text",
    # dev
    "dev_server",
    "publish",
    # UI automation
    "ui",
    # components catalog
    "SHARED_COMPONENTS",
    "get_component",
    "get_all_components",
    "get_css_imports",
    "get_ts_imports",
]

# EOF
