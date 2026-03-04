"""
Platform app manifest package.

Public API:
    ManifestParser   — parse a manifest.yaml file
    ManifestError    — raised on invalid manifest structure or content
    validate_manifest — deep-validate a parsed manifest dict
    load_app_from_manifest — parse, validate, and register an app
"""

from apps.platform_app.manifest.loader import load_app_from_manifest
from apps.platform_app.manifest.parser import ManifestError, ManifestParser
from apps.platform_app.manifest.validator import validate_manifest

__all__ = [
    "ManifestError",
    "ManifestParser",
    "load_app_from_manifest",
    "validate_manifest",
]
