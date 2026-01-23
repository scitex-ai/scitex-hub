"""Zenodo repository service implementation."""

import json
import logging
from typing import Dict, List
from django.conf import settings
from django.utils import timezone
from ....models import RepositoryConnection
from .base_service import BaseRepositoryService
from .exceptions import APIError
from .zenodo_utils import format_zenodo_metadata

logger = logging.getLogger(__name__)
class ZenodoService(BaseRepositoryService):
    """Service for interacting with Zenodo repository"""

    def __init__(self, repository_connection: RepositoryConnection):
        super().__init__(repository_connection)
        self.base_url = self.repository.api_base_url.rstrip("/")
        self.sandbox_mode = getattr(settings, "ZENODO_SANDBOX_MODE", True)

        if self.sandbox_mode:
            self.base_url = self.base_url.replace("zenodo.org", "sandbox.zenodo.org")

    def authenticate(self) -> bool:
        """Test authentication with Zenodo"""
        try:
            headers = {"Authorization": f"Bearer {self.connection.api_token}"}
            response = self._make_request(
                "GET", f"{self.base_url}/api/deposit/depositions", headers=headers
            )

            if response.status_code == 200:
                self.connection.status = "active"
                self.connection.last_verified = timezone.now()
                self.connection.save()
                return True
            else:
                self._handle_api_error(response)

        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            self.connection.status = "invalid"
            self.connection.last_error = str(e)
            self.connection.save()
            return False

    def create_dataset(self, metadata: Dict) -> Dict:
        """Create a new deposition in Zenodo"""
        headers = {
            "Authorization": f"Bearer {self.connection.api_token}",
            "Content-Type": "application/json",
        }

        # Prepare Zenodo metadata format
        zenodo_metadata = format_zenodo_metadata(metadata)

        data = json.dumps({"metadata": zenodo_metadata})

        response = self._make_request(
            "POST",
            f"{self.base_url}/api/deposit/depositions",
            headers=headers,
            data=data,
        )

        if response.status_code == 201:
            result = response.json()
            self.logger.info(f"Created Zenodo deposition: {result['id']}")
            return {
                "id": str(result["id"]),
                "url": result.get("links", {}).get("html", ""),
                "bucket_url": result.get("links", {}).get("bucket", ""),
                "status": result.get("state", "draft"),
                "doi": result.get("doi", ""),
                "conceptdoi": result.get("conceptdoi", ""),
                "metadata": result.get("metadata", {}),
            }
        else:
            self._handle_api_error(response)

    def update_dataset(self, dataset_id: str, metadata: Dict) -> Dict:
        """Update a Zenodo deposition"""
        headers = {
            "Authorization": f"Bearer {self.connection.api_token}",
            "Content-Type": "application/json",
        }

        zenodo_metadata = format_zenodo_metadata(metadata)
        data = json.dumps({"metadata": zenodo_metadata})

        response = self._make_request(
            "PUT",
            f"{self.base_url}/api/deposit/depositions/{dataset_id}",
            headers=headers,
            data=data,
        )

        if response.status_code == 200:
            result = response.json()
            self.logger.info(f"Updated Zenodo deposition: {dataset_id}")
            return {
                "id": str(result["id"]),
                "url": result.get("links", {}).get("html", ""),
                "status": result.get("state", "draft"),
                "doi": result.get("doi", ""),
                "metadata": result.get("metadata", {}),
            }
        else:
            self._handle_api_error(response)

    def upload_file(
        self, dataset_id: str, file_path: str, file_data: bytes, metadata: Dict = None
    ) -> Dict:
        """Upload a file to a Zenodo deposition"""
        # First, get the bucket URL
        dataset_info = self.get_dataset(dataset_id)
        bucket_url = dataset_info.get("bucket_url")

        if not bucket_url:
            raise APIError("No bucket URL found for dataset")

        headers = {"Authorization": f"Bearer {self.connection.api_token}"}

        # Upload file to bucket
        filename = file_path.split("/")[-1]
        files = {"file": (filename, file_data)}

        response = self._make_request(
            "PUT", f"{bucket_url}/{filename}", headers=headers, data=file_data
        )

        if response.status_code in [200, 201]:
            result = response.json()
            self.logger.info(
                f"Uploaded file {filename} to Zenodo deposition {dataset_id}"
            )
            return {
                "file_id": result.get("id"),
                "filename": result.get("filename"),
                "size": result.get("size"),
                "checksum": result.get("checksum"),
                "download_url": result.get("links", {}).get("download", ""),
            }
        else:
            self._handle_api_error(response)

    def get_dataset(self, dataset_id: str) -> Dict:
        """Get Zenodo deposition information"""
        headers = {"Authorization": f"Bearer {self.connection.api_token}"}

        response = self._make_request(
            "GET",
            f"{self.base_url}/api/deposit/depositions/{dataset_id}",
            headers=headers,
        )

        if response.status_code == 200:
            result = response.json()
            return {
                "id": str(result["id"]),
                "title": result.get("metadata", {}).get("title", ""),
                "description": result.get("metadata", {}).get("description", ""),
                "url": result.get("links", {}).get("html", ""),
                "bucket_url": result.get("links", {}).get("bucket", ""),
                "doi": result.get("doi", ""),
                "conceptdoi": result.get("conceptdoi", ""),
                "status": result.get("state", "draft"),
                "published": result.get("submitted", False),
                "version": result.get("metadata", {}).get("version", "1.0"),
                "files": [
                    {
                        "id": f.get("id"),
                        "filename": f.get("filename"),
                        "size": f.get("size"),
                        "checksum": f.get("checksum"),
                        "download_url": f.get("links", {}).get("download", ""),
                    }
                    for f in result.get("files", [])
                ],
                "metadata": result.get("metadata", {}),
            }
        else:
            self._handle_api_error(response)

    def list_datasets(self, filters: Dict = None) -> List[Dict]:
        """List Zenodo depositions for the authenticated user"""
        headers = {"Authorization": f"Bearer {self.connection.api_token}"}

        params = {}
        if filters:
            if "status" in filters:
                params["status"] = filters["status"]
            if "sort" in filters:
                params["sort"] = filters["sort"]
            if "page" in filters:
                params["page"] = filters["page"]
            if "size" in filters:
                params["size"] = filters["size"]

        response = self._make_request(
            "GET", f"{self.base_url}/api/deposit/depositions", headers=headers
        )

        if response.status_code == 200:
            results = response.json()
            return [
                {
                    "id": str(result["id"]),
                    "title": result.get("metadata", {}).get("title", ""),
                    "description": result.get("metadata", {}).get("description", ""),
                    "url": result.get("links", {}).get("html", ""),
                    "doi": result.get("doi", ""),
                    "status": result.get("state", "draft"),
                    "published": result.get("submitted", False),
                    "created_at": result.get("created"),
                    "updated_at": result.get("modified"),
                }
                for result in results
            ]
        else:
            self._handle_api_error(response)

    def publish_dataset(self, dataset_id: str) -> Dict:
        """Publish a Zenodo deposition"""
        headers = {"Authorization": f"Bearer {self.connection.api_token}"}

        response = self._make_request(
            "POST",
            f"{self.base_url}/api/deposit/depositions/{dataset_id}/actions/publish",
            headers=headers,
        )

        if response.status_code == 202:
            result = response.json()
            self.logger.info(f"Published Zenodo deposition: {dataset_id}")
            return {
                "id": str(result["id"]),
                "doi": result.get("doi"),
                "url": result.get("links", {}).get("html", ""),
                "status": result.get("state", "published"),
            }
        else:
            self._handle_api_error(response)

    def get_download_url(self, dataset_id: str, file_id: str) -> str:
        """Get download URL for a file in Zenodo"""
        dataset_info = self.get_dataset(dataset_id)
        for file_info in dataset_info.get("files", []):
            if file_info["id"] == file_id:
                return file_info["download_url"]

        raise APIError(f"File {file_id} not found in dataset {dataset_id}")
# EOF
