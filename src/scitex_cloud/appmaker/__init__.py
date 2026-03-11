"""SciTeX App Tools — init, validate, develop, publish, and manage app plugins."""

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
from ._license import generate_license_text
from ._prefs import delete_prefs, get_prefs, list_prefs, set_prefs
from ._publish import publish
from ._scaffold import init_app
from ._validate import (
    validate,
    validate_css,
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
    # license
    "generate_license_text",
    # dev
    "dev_server",
    "publish",
    # components catalog
    "SHARED_COMPONENTS",
    "get_component",
    "get_all_components",
    "get_css_imports",
    "get_ts_imports",
]

# EOF
