"""
Security scanning tool utilities
"""

import subprocess


class ToolUtilsMixin:
    """Tool availability checks and severity mapping"""

    def _has_pip_audit(self) -> bool:
        """Check if pip-audit is installed"""
        try:
            subprocess.run(["pip-audit", "--version"], capture_output=True, timeout=5)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _has_safety(self) -> bool:
        """Check if safety is installed"""
        try:
            subprocess.run(["safety", "--version"], capture_output=True, timeout=5)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _has_detect_secrets(self) -> bool:
        """Check if detect-secrets is installed"""
        try:
            subprocess.run(
                ["detect-secrets", "--version"], capture_output=True, timeout=5
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _has_bandit(self) -> bool:
        """Check if bandit is installed"""
        try:
            subprocess.run(["bandit", "--version"], capture_output=True, timeout=5)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    @staticmethod
    def _map_severity(severity: str) -> str:
        """Map external severity levels to our severity levels"""
        severity = severity.lower()
        if severity in ["critical", "high", "medium", "low"]:
            return severity
        if severity in ["error", "severe"]:
            return "critical"
        if severity in ["warning", "moderate"]:
            return "medium"
        if severity in ["info", "minor"]:
            return "low"
        return "medium"

    @staticmethod
    def _map_bandit_severity(severity: str) -> str:
        """Map bandit severity to our severity levels"""
        severity = severity.upper()
        mapping = {
            "HIGH": "high",
            "MEDIUM": "medium",
            "LOW": "low",
        }
        return mapping.get(severity, "medium")


# EOF
