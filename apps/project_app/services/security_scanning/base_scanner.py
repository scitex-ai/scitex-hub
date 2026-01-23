"""
Base security scanner class
"""

from typing import Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BaseScanner:
    """
    Base security scanner class with core scanning orchestration
    """

    def __init__(self, project):
        self.project = project
        self.project_path = project.get_local_path()

    def run_full_scan(self, user=None) -> Dict:
        """
        Run a complete security scan on the project

        Returns:
            dict: Scan results with alerts and statistics
        """
        from apps.project_app.models.security import SecurityScanResult

        # Create scan result record
        scan = SecurityScanResult.objects.create(
            project=self.project, scan_type="full", status="running", triggered_by=user
        )

        start_time = datetime.now()
        results = {
            "alerts": [],
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "errors": [],
        }

        try:
            # Run dependency vulnerability scan
            dep_results = self.scan_dependencies()
            results["alerts"].extend(dep_results["alerts"])

            # Run secret scanning
            secret_results = self.scan_secrets()
            results["alerts"].extend(secret_results["alerts"])

            # Run code analysis
            code_results = self.scan_code()
            results["alerts"].extend(code_results["alerts"])

            # Count alerts by severity
            for alert in results["alerts"]:
                severity = alert.get("severity", "low")
                if severity == "critical":
                    results["critical"] += 1
                elif severity == "high":
                    results["high"] += 1
                elif severity == "medium":
                    results["medium"] += 1
                elif severity == "low":
                    results["low"] += 1

            # Save alerts to database
            alerts_created = self._save_alerts(results["alerts"])

            # Complete scan
            duration = (datetime.now() - start_time).total_seconds()
            scan.alerts_created = alerts_created
            scan.critical_count = results["critical"]
            scan.high_count = results["high"]
            scan.medium_count = results["medium"]
            scan.low_count = results["low"]
            scan.complete(duration=duration)

            results["scan_id"] = scan.id
            results["duration"] = duration

        except Exception as e:
            logger.error(f"Security scan failed: {e}")
            scan.fail(str(e))
            results["errors"].append(str(e))

        return results

    def _save_alerts(self, alerts: List[Dict]) -> int:
        """Save alerts to database"""
        from apps.project_app.models.security import SecurityAlert

        count = 0
        for alert_data in alerts:
            # Check if alert already exists
            existing = SecurityAlert.objects.filter(
                project=self.project,
                title=alert_data["title"],
                affected_package=alert_data.get("affected_package", ""),
                status="open",
            ).first()

            if not existing:
                SecurityAlert.objects.create(project=self.project, **alert_data)
                count += 1

        return count

    # Methods to be implemented by mixins
    def scan_dependencies(self) -> Dict:
        raise NotImplementedError

    def scan_secrets(self) -> Dict:
        raise NotImplementedError

    def scan_code(self) -> Dict:
        raise NotImplementedError


# EOF
