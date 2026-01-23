"""
Main security scanner class combining all scanning functionality
"""

from .base_scanner import BaseScanner
from .dependency_scanner import DependencyScannerMixin
from .secret_scanner import SecretScannerMixin
from .code_scanner import CodeScannerMixin
from .tool_utils import ToolUtilsMixin


class SecurityScanner(
    BaseScanner,
    DependencyScannerMixin,
    SecretScannerMixin,
    CodeScannerMixin,
    ToolUtilsMixin,
):
    """
    Main security scanner class
    Orchestrates various security checks using mixin composition
    """

    pass


# EOF
