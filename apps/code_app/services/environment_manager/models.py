#!/usr/bin/env python3
"""
Data Models for Environment Management
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User


class PackageRequirement:
    """Represents a Python package requirement."""

    def __init__(
        self,
        name: str,
        version: Optional[str] = None,
        source: str = "pypi",
        extras: Optional[List[str]] = None,
    ):
        self.name = name
        self.version = version
        self.source = source
        self.extras = extras or []

    def __str__(self):
        """Return pip-compatible requirement string."""
        req = self.name
        if self.extras:
            req += f"[{','.join(self.extras)}]"
        if self.version:
            req += f"=={self.version}"
        return req

    @classmethod
    def from_string(cls, req_string: str):
        """Parse requirement from string like 'numpy==1.21.0' or 'scipy[linalg]'."""
        # Basic parsing - can be enhanced for more complex requirements
        extras = []
        name = req_string
        version = None

        # Extract extras
        if "[" in req_string:
            name, extras_part = req_string.split("[", 1)
            extras = extras_part.rstrip("]").split(",")

        # Extract version
        if "==" in name:
            name, version = name.split("==", 1)
        elif ">=" in name:
            name, version = name.split(">=", 1)
            version = f">={version}"
        elif "<=" in name:
            name, version = name.split("<=", 1)
            version = f"<={version}"

        return cls(name.strip(), version, extras=extras)


class Environment:
    """Represents a Python execution environment."""

    def __init__(self, env_id: str, user: User, name: str = ""):
        self.env_id = env_id
        self.user = user
        self.name = name or f"env_{env_id[:8]}"
        self.base_path = Path(settings.MEDIA_ROOT) / "environments" / str(user.id)
        self.env_path = self.base_path / env_id
        self.requirements: List[PackageRequirement] = []
        self.python_version = "3.11"
        self.created_at = timezone.now()
        self.last_used = timezone.now()

        # Standard scientific packages
        self.base_packages = [
            PackageRequirement("numpy", "1.24.3"),
            PackageRequirement("pandas", "2.0.3"),
            PackageRequirement("matplotlib", "3.7.1"),
            PackageRequirement("seaborn", "0.12.2"),
            PackageRequirement("scipy", "1.10.1"),
            PackageRequirement("scikit-learn", "1.3.0"),
            PackageRequirement("jupyter", "1.0.0"),
            PackageRequirement("ipykernel", "6.25.0"),
        ]

    def add_requirement(self, requirement: PackageRequirement):
        """Add a package requirement to the environment."""
        # Remove existing requirement with same name
        self.requirements = [r for r in self.requirements if r.name != requirement.name]
        self.requirements.append(requirement)

    def get_requirements_file(self) -> str:
        """Generate requirements.txt content."""
        all_reqs = self.base_packages + self.requirements
        return "\n".join(str(req) for req in all_reqs)

    def to_dict(self) -> Dict[str, Any]:
        """Convert environment to dictionary for serialization."""
        return {
            "env_id": self.env_id,
            "name": self.name,
            "python_version": self.python_version,
            "requirements": [str(req) for req in self.requirements],
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], user: User):
        """Create environment from dictionary."""
        env = cls(data["env_id"], user, data["name"])
        env.python_version = data.get("python_version", "3.11")
        env.requirements = [
            PackageRequirement.from_string(req) for req in data.get("requirements", [])
        ]
        env.created_at = timezone.datetime.fromisoformat(data["created_at"])
        env.last_used = timezone.datetime.fromisoformat(data["last_used"])
        return env
