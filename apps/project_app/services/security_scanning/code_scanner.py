"""
Static code analysis for security issues
"""

import subprocess
import json
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class CodeScannerMixin:
    """Static code analysis functionality"""

    def scan_code(self) -> Dict:
        """
        Static code analysis for security issues
        Uses bandit for Python

        Returns:
            dict: Code analysis results
        """
        results = {"alerts": [], "errors": []}

        if not self._has_bandit():
            logger.info("bandit not available")
            return results

        try:
            cmd = [
                "bandit",
                "-r",
                str(self.project_path),
                "-f",
                "json",
                "-ll",  # Only report low severity and above
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_path),
                timeout=300,
            )

            # Parse JSON output
            try:
                data = json.loads(result.stdout)
                for issue in data.get("results", []):
                    alert = {
                        "alert_type": "code",
                        "severity": self._map_bandit_severity(
                            issue.get("issue_severity", "LOW")
                        ),
                        "title": issue.get("issue_text", "Security issue detected"),
                        "description": f"{issue.get('issue_text', '')} - {issue.get('issue_cwe', {}).get('link', '')}",
                        "file_path": issue.get("filename", ""),
                        "line_number": issue.get("line_number", 0),
                        "fix_available": False,
                    }
                    results["alerts"].append(alert)
            except json.JSONDecodeError:
                logger.error("Failed to parse bandit output")

        except subprocess.TimeoutExpired:
            results["errors"].append("Code scan timed out")
        except Exception as e:
            logger.error(f"Code scan failed: {e}")
            results["errors"].append(str(e))

        return results


# EOF
