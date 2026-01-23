"""
Repository integration for Writer manuscripts.
Integrates manuscript submissions with research data repositories for
data sharing, supplementary materials, and reproducible research.
"""

from .service import ManuscriptRepositoryIntegrator
from .utils import auto_create_supplementary_dataset

__all__ = [
    "ManuscriptRepositoryIntegrator",
    "auto_create_supplementary_dataset",
]
