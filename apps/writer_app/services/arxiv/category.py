"""
arXiv Category Management Service

Delegates category data and suggestion algorithm to scitex_writer.export.
Django-specific ORM operations remain here.
"""

from typing import List

from scitex_writer.export import ARXIV_CATEGORIES
from scitex_writer.export import suggest_categories as _suggest_categories

from ...models import ArxivCategory, Manuscript


class ArxivCategoryService:
    """Service for managing arXiv categories and subject classification."""

    def populate_categories(self) -> int:
        """Populate the database with arXiv categories from scitex-writer."""
        created_count = 0
        for cat_data in ARXIV_CATEGORIES:
            _, created = ArxivCategory.objects.get_or_create(
                code=cat_data["code"],
                defaults={
                    "name": cat_data["name"],
                    "description": cat_data["description"],
                },
            )
            if created:
                created_count += 1
        return created_count

    def get_categories_by_field(self, field: str) -> List[ArxivCategory]:
        """Get categories by field (e.g., 'cs', 'math', 'physics')."""
        return ArxivCategory.objects.filter(
            code__startswith=f"{field}.", is_active=True
        ).order_by("code")

    def suggest_categories(
        self, manuscript: Manuscript, max_suggestions: int = 5
    ) -> List[ArxivCategory]:
        """Suggest categories based on manuscript content."""
        content = f"{manuscript.title} {manuscript.abstract}"
        suggestions = _suggest_categories(content, max_suggestions=max_suggestions)

        # Map pure (code, name, score) tuples to Django ArxivCategory objects
        result = []
        for code, _name, _score in suggestions:
            try:
                result.append(ArxivCategory.objects.get(code=code))
            except ArxivCategory.DoesNotExist:
                continue
        return result
