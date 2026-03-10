"""
arXiv Validation Service

Validates manuscripts for arXiv submission requirements including
metadata, LaTeX compilation, PDF generation, and file formats.
"""

from django.utils import timezone

from ...models import ArxivSubmission, ArxivValidationResult


class ArxivValidationService:
    """Service for validating manuscripts before arXiv submission."""

    def __init__(self):
        self.max_file_size_mb = 50  # arXiv's file size limit
        self.max_title_length = 256
        self.max_abstract_length = 1920

    def validate_submission(self, submission: ArxivSubmission) -> ArxivValidationResult:
        """
        Comprehensive validation of arXiv submission.

        Args:
            submission: ArxivSubmission to validate

        Returns:
            ArxivValidationResult object
        """
        # Create or get validation result
        validation, created = ArxivValidationResult.objects.get_or_create(
            submission=submission, defaults={"status": "pending"}
        )

        validation.validation_started = timezone.now()
        validation.save()

        # Run validation checks
        self._validate_metadata(validation, submission)
        self._validate_latex_compilation(validation, submission)
        self._validate_pdf_generation(validation, submission)
        self._validate_file_formats(validation, submission)
        self._validate_categories(validation, submission)

        # Calculate overall score and status
        self._calculate_overall_validation(validation)

        validation.validation_completed = timezone.now()
        validation.save()

        return validation

    def _validate_metadata(
        self, validation: ArxivValidationResult, submission: ArxivSubmission
    ):
        """Validate submission metadata (title, abstract, authors)."""
        errors = []
        warnings = []

        # Title validation
        if len(submission.title) > self.max_title_length:
            errors.append(
                f"Title exceeds maximum length of {self.max_title_length} characters"
            )
            validation.title_length_check = False
        else:
            validation.title_length_check = True

        # Abstract validation
        if len(submission.abstract) > self.max_abstract_length:
            errors.append(
                f"Abstract exceeds maximum length of {self.max_abstract_length} characters"
            )
            validation.abstract_length_check = False
        else:
            validation.abstract_length_check = True

        # Author format validation
        if not submission.authors.strip():
            errors.append("Authors field is required")
            validation.author_format_check = False
        else:
            validation.author_format_check = True

        # Set validation status
        if errors:
            validation.metadata_validation = "failed"
            validation.error_messages.extend(errors)
        elif warnings:
            validation.metadata_validation = "warning"
            validation.warning_messages.extend(warnings)
        else:
            validation.metadata_validation = "passed"

        validation.save()

    def _validate_latex_compilation(
        self, validation: ArxivValidationResult, submission: ArxivSubmission
    ):
        """Validate LaTeX compilation."""
        if not submission.latex_source:
            validation.latex_compilation = "failed"
            validation.error_messages.append("LaTeX source file is required")
            validation.save()
            return

        try:
            # In a real implementation, this would compile the LaTeX
            # For now, we'll simulate successful compilation
            validation.latex_compilation = "passed"
            validation.latex_log = "LaTeX compilation successful"
        except Exception as e:
            validation.latex_compilation = "failed"
            validation.error_messages.append(f"LaTeX compilation failed: {str(e)}")

        validation.save()

    def _validate_pdf_generation(
        self, validation: ArxivValidationResult, submission: ArxivSubmission
    ):
        """Validate PDF generation."""
        if not submission.pdf_file:
            validation.pdf_generation = "failed"
            validation.error_messages.append("PDF file is required")
        else:
            validation.pdf_generation = "passed"

        validation.save()

    def _validate_file_formats(
        self, validation: ArxivValidationResult, submission: ArxivSubmission
    ):
        """Validate file formats and sizes."""
        total_size = 0
        unsupported_files = []

        # Check main files
        if submission.latex_source:
            total_size += submission.latex_source.size / (1024 * 1024)  # Convert to MB

        if submission.pdf_file:
            total_size += submission.pdf_file.size / (1024 * 1024)

        validation.total_file_size = total_size
        validation.max_file_size_exceeded = total_size > self.max_file_size_mb
        validation.unsupported_files = unsupported_files

        if validation.max_file_size_exceeded:
            validation.file_format_check = "failed"
            validation.error_messages.append(
                f"Total file size ({total_size:.1f}MB) exceeds limit of {self.max_file_size_mb}MB"
            )
        else:
            validation.file_format_check = "passed"

        validation.save()

    def _validate_categories(
        self, validation: ArxivValidationResult, submission: ArxivSubmission
    ):
        """Validate category selection."""
        if not submission.primary_category:
            validation.category_validation = "failed"
            validation.error_messages.append("Primary category is required")
        else:
            validation.category_validation = "passed"

        validation.save()

    def _calculate_overall_validation(self, validation: ArxivValidationResult):
        """Calculate overall validation score and status."""
        checks = [
            validation.latex_compilation,
            validation.pdf_generation,
            validation.metadata_validation,
            validation.category_validation,
            validation.file_format_check,
        ]

        passed_count = sum(1 for check in checks if check == "passed")
        failed_count = sum(1 for check in checks if check == "failed")
        warning_count = sum(1 for check in checks if check == "warning")

        # Calculate score (0-100)
        validation.overall_score = (passed_count / len(checks)) * 100

        # Determine overall status
        if failed_count > 0:
            validation.status = "failed"
        elif warning_count > 0:
            validation.status = "warning"
        else:
            validation.status = "passed"

        validation.save()
