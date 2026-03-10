"""
arXiv Category Management Service

Handles category population, filtering, and suggestion based on manuscript content.
"""

from typing import List

from ...models import ArxivCategory, Manuscript


class ArxivCategoryService:
    """Service for managing arXiv categories and subject classification."""

    def __init__(self):
        self.categories_url = "https://arxiv.org/category_taxonomy"

    def populate_categories(self) -> int:
        """
        Populate the database with current arXiv categories.

        Returns:
            int: Number of categories created/updated
        """
        # This would fetch from arXiv's category API in a real implementation
        # For now, we'll create some common categories
        categories_data = [
            # Computer Science
            {
                "code": "cs.AI",
                "name": "Artificial Intelligence",
                "description": "Covers all areas of AI",
            },
            {
                "code": "cs.CL",
                "name": "Computation and Language",
                "description": "Natural language processing, computational linguistics",
            },
            {
                "code": "cs.CV",
                "name": "Computer Vision and Pattern Recognition",
                "description": "Image processing, computer vision",
            },
            {
                "code": "cs.LG",
                "name": "Machine Learning",
                "description": "Machine learning research",
            },
            {
                "code": "cs.NI",
                "name": "Networking and Internet Architecture",
                "description": "Network protocols, internet architecture",
            },
            {
                "code": "cs.SE",
                "name": "Software Engineering",
                "description": "Software development, engineering practices",
            },
            # Mathematics
            {
                "code": "math.ST",
                "name": "Statistics Theory",
                "description": "Mathematical statistics",
            },
            {
                "code": "math.PR",
                "name": "Probability",
                "description": "Probability theory",
            },
            {
                "code": "math.NA",
                "name": "Numerical Analysis",
                "description": "Numerical methods and analysis",
            },
            # Physics
            {
                "code": "physics.comp-ph",
                "name": "Computational Physics",
                "description": "Computational methods in physics",
            },
            {
                "code": "physics.data-an",
                "name": "Data Analysis, Statistics and Probability",
                "description": "Data analysis in physics",
            },
            # Quantitative Biology
            {
                "code": "q-bio.BM",
                "name": "Biomolecules",
                "description": "Molecular biology, biochemistry",
            },
            {
                "code": "q-bio.GN",
                "name": "Genomics",
                "description": "Genomics and bioinformatics",
            },
            # Statistics
            {
                "code": "stat.AP",
                "name": "Applications",
                "description": "Applied statistics",
            },
            {
                "code": "stat.ML",
                "name": "Machine Learning",
                "description": "Statistical machine learning",
            },
        ]

        created_count = 0
        for cat_data in categories_data:
            category, created = ArxivCategory.objects.get_or_create(
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
        """
        Get categories by field (e.g., 'cs', 'math', 'physics').

        Args:
            field: Field prefix (e.g., 'cs', 'math')

        Returns:
            List of ArxivCategory objects
        """
        return ArxivCategory.objects.filter(
            code__startswith=f"{field}.", is_active=True
        ).order_by("code")

    def suggest_categories(
        self, manuscript: Manuscript, max_suggestions: int = 5
    ) -> List[ArxivCategory]:
        """
        Suggest categories based on manuscript content.

        Args:
            manuscript: Manuscript to analyze
            max_suggestions: Maximum number of suggestions

        Returns:
            List of suggested ArxivCategory objects
        """
        # Simple keyword-based suggestion system
        content = f"{manuscript.title} {manuscript.abstract}".lower()

        category_keywords = {
            "cs.AI": [
                "artificial intelligence",
                "ai",
                "machine learning",
                "deep learning",
                "neural network",
            ],
            "cs.CL": [
                "natural language",
                "nlp",
                "language model",
                "text processing",
                "linguistics",
            ],
            "cs.CV": [
                "computer vision",
                "image processing",
                "object detection",
                "recognition",
            ],
            "cs.LG": [
                "machine learning",
                "learning algorithm",
                "classification",
                "regression",
            ],
            "stat.ML": [
                "statistical learning",
                "bayesian",
                "statistics",
                "probabilistic",
            ],
            "math.ST": ["statistics", "statistical theory", "hypothesis testing"],
            "q-bio.GN": ["genomics", "bioinformatics", "dna", "rna", "genome"],
        }

        suggestions = []
        for code, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content)
            if score > 0:
                try:
                    category = ArxivCategory.objects.get(code=code)
                    suggestions.append((category, score))
                except ArxivCategory.DoesNotExist:
                    continue

        # Sort by score and return top suggestions
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [cat for cat, score in suggestions[:max_suggestions]]
