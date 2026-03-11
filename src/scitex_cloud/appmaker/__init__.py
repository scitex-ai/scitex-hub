"""SciTeX App Tools — scaffold, validate, develop, and publish app plugins."""

from ._components import (
    SHARED_COMPONENTS,
    get_all_components,
    get_component,
    get_css_imports,
    get_ts_imports,
)
from ._launcher import dev_server
from ._license import generate_license_text
from ._publish import publish
from ._scaffold import scaffold
from ._validate import (
    validate,
    validate_css,
    validate_manifest,
    validate_security,
    validate_structure,
    validate_templates,
)

__all__ = [
    # scaffold
    "scaffold",
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
