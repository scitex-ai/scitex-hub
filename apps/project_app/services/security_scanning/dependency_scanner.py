"""
Dependency vulnerability scanning
"""

import subprocess
import json
import re
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class DependencyScannerMixin:
    """Dependency vulnerability scanning functionality"""

    def scan_dependencies(self) -> Dict:
        """
        Scan Python dependencies for known vulnerabilities
        Uses pip-audit or safety

        Returns:
            dict: Vulnerability results
        """
        results = {"alerts": [], "errors": []}

        # Check if requirements.txt or pyproject.toml exists
        requirements_file = self.project_path / "requirements.txt"
        pyproject_file = self.project_path / "pyproject.toml"

        if not requirements_file.exists() and not pyproject_file.exists():
            logger.info(f"No dependency files found for {self.project.name}")
            return results

        # Try using pip-audit (preferred)
        if self._has_pip_audit():
            results = self._scan_with_pip_audit()
        # Fallback to safety
        elif self._has_safety():
            results = self._scan_with_safety()
        else:
            logger.warning("No security scanning tools available (pip-audit or safety)")
            results["errors"].append("Security scanning tools not installed")

        # Update dependency graph
        self._update_dependency_graph()

        return results

    def _scan_with_pip_audit(self) -> Dict:
        """Scan using pip-audit"""
        results = {"alerts": [], "errors": []}

        try:
            cmd = [
                "pip-audit",
                "--format",
                "json",
                "--requirement",
                str(self.project_path / "requirements.txt"),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_path),
                timeout=300,
            )

            if result.returncode == 0:
                # No vulnerabilities found
                return results

            # Parse JSON output
            try:
                data = json.loads(result.stdout)
                for vuln in data.get("vulnerabilities", []):
                    alert = {
                        "alert_type": "dependency",
                        "severity": self._map_severity(vuln.get("severity", "medium")),
                        "title": vuln.get("description", "Vulnerability detected"),
                        "description": vuln.get(
                            "fix_versions", "No description available"
                        ),
                        "affected_package": vuln.get("name", ""),
                        "affected_version": vuln.get("version", ""),
                        "fixed_version": ", ".join(vuln.get("fix_versions", [])),
                        "cve_id": vuln.get("id", ""),
                        "advisory_url": vuln.get("aliases", [{}])[0].get("url", "")
                        if vuln.get("aliases")
                        else "",
                        "fix_available": bool(vuln.get("fix_versions")),
                    }
                    results["alerts"].append(alert)
            except json.JSONDecodeError:
                logger.error("Failed to parse pip-audit output")
                results["errors"].append("Failed to parse pip-audit output")

        except subprocess.TimeoutExpired:
            logger.error("pip-audit timed out")
            results["errors"].append("Dependency scan timed out")
        except Exception as e:
            logger.error(f"pip-audit failed: {e}")
            results["errors"].append(str(e))

        return results

    def _scan_with_safety(self) -> Dict:
        """Scan using safety"""
        results = {"alerts": [], "errors": []}

        try:
            cmd = [
                "safety",
                "check",
                "--json",
                "--file",
                str(self.project_path / "requirements.txt"),
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
                for vuln in data:
                    alert = {
                        "alert_type": "dependency",
                        "severity": self._map_severity(
                            "high"
                        ),  # safety doesn't provide severity
                        "title": vuln[0],  # Package name
                        "description": vuln[3],  # Vulnerability description
                        "affected_package": vuln[0],
                        "affected_version": vuln[2],
                        "fixed_version": "",  # Not provided by safety
                        "cve_id": vuln[4] if len(vuln) > 4 else "",
                        "fix_available": False,
                    }
                    results["alerts"].append(alert)
            except (json.JSONDecodeError, IndexError, KeyError):
                logger.error("Failed to parse safety output")
                results["errors"].append("Failed to parse safety output")

        except subprocess.TimeoutExpired:
            logger.error("safety check timed out")
            results["errors"].append("Dependency scan timed out")
        except Exception as e:
            logger.error(f"safety check failed: {e}")
            results["errors"].append(str(e))

        return results

    def check_outdated_dependencies(self) -> Dict:
        """
        Check for outdated dependencies

        Returns:
            dict: Outdated dependency results
        """
        results = {"alerts": [], "errors": []}

        try:
            cmd = ["pip", "list", "--outdated", "--format", "json"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_path),
                timeout=60,
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                for package in data:
                    alert = {
                        "alert_type": "outdated",
                        "severity": "low",
                        "title": f"Outdated dependency: {package['name']}",
                        "description": f"Package {package['name']} is outdated. Current: {package['version']}, Latest: {package['latest_version']}",
                        "affected_package": package["name"],
                        "affected_version": package["version"],
                        "fixed_version": package["latest_version"],
                        "fix_available": True,
                    }
                    results["alerts"].append(alert)

        except Exception as e:
            logger.error(f"Outdated check failed: {e}")
            results["errors"].append(str(e))

        return results

    def _update_dependency_graph(self):
        """Update dependency graph from project dependencies"""
        from apps.project_app.models.security import DependencyGraph

        requirements_file = self.project_path / "requirements.txt"
        if not requirements_file.exists():
            return

        try:
            # Parse requirements.txt
            with open(requirements_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    # Parse package==version
                    match = re.match(r"([a-zA-Z0-9_-]+)==([0-9.]+)", line)
                    if match:
                        package_name, version = match.groups()

                        # Create or update dependency
                        dep, created = DependencyGraph.objects.update_or_create(
                            project=self.project,
                            package_name=package_name,
                            version=version,
                            defaults={
                                "is_direct": True,
                                "package_type": "python",
                            },
                        )

        except Exception as e:
            logger.error(f"Failed to update dependency graph: {e}")


# EOF
