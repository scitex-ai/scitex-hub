"""
CVE and vulnerability database lookup
"""

from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class CVELookup:
    """
    Lookup CVE information from external databases
    """

    @staticmethod
    def lookup_cve(cve_id: str) -> Optional[Dict]:
        """
        Look up CVE information from NVD database

        Args:
            cve_id: CVE identifier (e.g., CVE-2024-1234)

        Returns:
            dict: CVE information or None
        """
        try:
            import requests

            url = f"https://services.nvd.nist.gov/rest/json/cve/1.0/{cve_id}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # Extract relevant information
                return {
                    "id": cve_id,
                    "description": data.get("description", ""),
                    "severity": data.get("severity", "unknown"),
                    "published_date": data.get("publishedDate", ""),
                    "references": data.get("references", []),
                }

        except Exception as e:
            logger.error(f"CVE lookup failed for {cve_id}: {e}")

        return None

    @staticmethod
    def lookup_pypi_vulnerabilities(package_name: str) -> List[Dict]:
        """
        Look up known vulnerabilities for a PyPI package

        Args:
            package_name: Name of the PyPI package

        Returns:
            list: List of vulnerabilities
        """
        vulnerabilities = []

        try:
            import requests

            # Use PyPI JSON API
            url = f"https://pypi.org/pypi/{package_name}/json"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # Check for vulnerability information
                # Note: PyPI doesn't directly provide vulnerability data
                # This would need integration with safety-db or similar

        except Exception as e:
            logger.error(f"PyPI lookup failed for {package_name}: {e}")

        return vulnerabilities


# EOF
