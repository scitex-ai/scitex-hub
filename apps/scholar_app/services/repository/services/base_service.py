"""Base repository service abstract class."""

import requests
import logging
import mimetypes
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from django.utils import timezone
from ....models import RepositoryConnection, Dataset, DatasetFile
from .exceptions import AuthenticationError, APIError

logger = logging.getLogger(__name__)


class BaseRepositoryService(ABC):
    """Base class for repository service implementations"""

    def __init__(self, repository_connection: RepositoryConnection):
        self.connection = repository_connection
        self.repository = repository_connection.repository
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the repository"""
        pass

    @abstractmethod
    def create_dataset(self, metadata: Dict) -> Dict:
        """Create a new dataset in the repository"""
        pass

    @abstractmethod
    def update_dataset(self, dataset_id: str, metadata: Dict) -> Dict:
        """Update an existing dataset"""
        pass

    @abstractmethod
    def upload_file(
        self, dataset_id: str, file_path: str, file_data: bytes, metadata: Dict = None
    ) -> Dict:
        """Upload a file to a dataset"""
        pass

    @abstractmethod
    def get_dataset(self, dataset_id: str) -> Dict:
        """Retrieve dataset metadata"""
        pass

    @abstractmethod
    def list_datasets(self, filters: Dict = None) -> List[Dict]:
        """List datasets for the authenticated user"""
        pass

    @abstractmethod
    def publish_dataset(self, dataset_id: str) -> Dict:
        """Publish a dataset (make it public)"""
        pass

    @abstractmethod
    def get_download_url(self, dataset_id: str, file_id: str) -> str:
        """Get download URL for a file"""
        pass

    def _make_request(
        self,
        method: str,
        url: str,
        headers: Dict = None,
        data: Any = None,
        files: Dict = None,
        timeout: int = 30,
    ) -> requests.Response:
        """Make an HTTP request with proper error handling"""
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                files=files,
                timeout=timeout,
            )

            # Log request for debugging
            self.logger.debug(f"{method} {url} - Status: {response.status_code}")

            return response

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            raise APIError(f"Request failed: {e}")

    def _handle_api_error(self, response: requests.Response) -> None:
        """Handle API error responses"""
        if response.status_code == 401:
            raise AuthenticationError("Authentication failed")
        elif response.status_code == 403:
            raise AuthenticationError("Access forbidden")
        elif response.status_code == 404:
            raise APIError("Resource not found")
        elif response.status_code >= 400:
            try:
                error_data = response.json()
                error_message = error_data.get(
                    "message", f"API error: {response.status_code}"
                )
            except ValueError:
                error_message = f"API error: {response.status_code} - {response.text}"
            raise APIError(error_message)

    def sync_dataset_from_repository(self, repository_dataset_id: str) -> Dataset:
        """Sync a dataset from the repository to local database"""
        # Get dataset metadata from repository
        repo_data = self.get_dataset(repository_dataset_id)

        # Create or update local dataset
        dataset, created = Dataset.objects.get_or_create(
            repository_connection=self.connection,
            repository_id=repository_dataset_id,
            defaults={
                "title": repo_data.get("title", ""),
                "description": repo_data.get("description", ""),
                "owner": self.connection.user,
                "status": "published" if repo_data.get("published") else "draft",
                "repository_url": repo_data.get("url", ""),
                "repository_doi": repo_data.get("doi", ""),
                "version": repo_data.get("version", "1.0"),
                "last_synced": timezone.now(),
            },
        )

        if not created:
            # Update existing dataset
            dataset.title = repo_data.get("title", dataset.title)
            dataset.description = repo_data.get("description", dataset.description)
            dataset.repository_url = repo_data.get("url", dataset.repository_url)
            dataset.repository_doi = repo_data.get("doi", dataset.repository_doi)
            dataset.version = repo_data.get("version", dataset.version)
            dataset.last_synced = timezone.now()
            dataset.save()

        # Sync files
        files_data = repo_data.get("files", [])
        for file_data in files_data:
            self._sync_dataset_file(dataset, file_data)

        return dataset

    def _sync_dataset_file(self, dataset: Dataset, file_data: Dict) -> DatasetFile:
        """Sync a single file from repository"""
        dataset_file, created = DatasetFile.objects.get_or_create(
            dataset=dataset,
            repository_file_id=file_data.get("id", ""),
            defaults={
                "filename": file_data.get("filename", ""),
                "file_path": file_data.get("path", ""),
                "file_type": self._determine_file_type(file_data.get("filename", "")),
                "file_format": self._get_file_extension(file_data.get("filename", "")),
                "size_bytes": file_data.get("size", 0),
                "checksum_md5": file_data.get("checksum", ""),
                "download_url": file_data.get("download_url", ""),
                "mime_type": mimetypes.guess_type(file_data.get("filename", ""))[0]
                or "",
            },
        )

        if not created:
            # Update existing file
            dataset_file.filename = file_data.get("filename", dataset_file.filename)
            dataset_file.size_bytes = file_data.get("size", dataset_file.size_bytes)
            dataset_file.download_url = file_data.get(
                "download_url", dataset_file.download_url
            )
            dataset_file.save()

        return dataset_file

    def _determine_file_type(self, filename: str) -> str:
        """Determine file type based on filename"""
        filename_lower = filename.lower()

        if filename_lower in ["readme.md", "readme.txt", "readme"]:
            return "readme"
        elif filename_lower.endswith((".py", ".r", ".m", ".ipynb", ".sh", ".bat")):
            return "code"
        elif filename_lower.endswith((".pdf", ".doc", ".docx", ".txt", ".md")):
            return "documentation"
        elif filename_lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".eps")):
            return "figure"
        elif filename_lower.endswith(
            (".csv", ".xlsx", ".json", ".xml", ".h5", ".hdf5", ".nc")
        ):
            return "data"
        elif filename_lower.startswith("license"):
            return "license"
        else:
            return "data"  # Default to data

    def _get_file_extension(self, filename: str) -> str:
        """Get file extension"""
        parts = filename.split(".")
        return parts[-1] if len(parts) > 1 else ""



# EOF
