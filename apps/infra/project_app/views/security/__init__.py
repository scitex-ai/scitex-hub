"""
Security feature views
GitHub-style security features for SciTeX projects
"""

from .advisories import security_advisories, security_advisory_detail
from .alerts import (
    create_fix_pr,
    dismiss_alert,
    reopen_alert,
    security_alert_detail,
    security_alerts,
)
from .dependency import api_dependency_tree, security_dependency_graph
from .overview import security_overview
from .policy import security_policy
from .scan import security_scan_history, trigger_security_scan

# Aliases for backward compatibility with security_views.py names
security_policy_edit = security_policy
scan_history = security_scan_history
dependency_graph = security_dependency_graph

__all__ = [
    # Overview
    "security_overview",
    # Alerts
    "security_alerts",
    "security_alert_detail",
    "dismiss_alert",
    "reopen_alert",
    "create_fix_pr",
    # Scan
    "security_scan_history",
    "trigger_security_scan",
    "scan_history",  # alias
    # Advisories
    "security_advisories",
    "security_advisory_detail",
    # Dependency
    "security_dependency_graph",
    "api_dependency_tree",
    "dependency_graph",  # alias
    # Policy
    "security_policy",
    "security_policy_edit",  # alias
]
