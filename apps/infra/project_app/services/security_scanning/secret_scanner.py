"""
Secret detection in code
"""

import subprocess
import json
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class SecretScannerMixin:
    """Secret detection functionality"""

    def scan_secrets(self) -> Dict:
        """
        Scan for secrets in code (API keys, passwords, tokens)
        Uses detect-secrets or similar

        Returns:
            dict: Secret detection results
        """
        results = {"alerts": [], "errors": []}

        if not self._has_detect_secrets():
            logger.info("detect-secrets not available")
            return results

        try:
            # Initialize baseline if not exists
            baseline_file = self.project_path / ".secrets.baseline"

            # Scan for secrets
            cmd = [
                "detect-secrets",
                "scan",
                "--baseline",
                str(baseline_file),
                str(self.project_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_path),
                timeout=300,
            )

            # Parse results
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    for file_path, secrets in data.get("results", {}).items():
                        for secret in secrets:
                            alert = {
                                "alert_type": "secret",
                                "severity": "critical",  # Secrets are always critical
                                "title": f"Potential secret detected: {secret.get('type', 'unknown')}",
                                "description": f"Potential {secret.get('type', 'secret')} found in {file_path}",
                                "file_path": file_path,
                                "line_number": secret.get("line_number", 0),
                                "fix_available": False,
                            }
                            results["alerts"].append(alert)
                except json.JSONDecodeError:
                    logger.error("Failed to parse detect-secrets output")

        except subprocess.TimeoutExpired:
            results["errors"].append("Secret scan timed out")
        except Exception as e:
            logger.error(f"Secret scan failed: {e}")
            results["errors"].append(str(e))

        return results


# EOF
