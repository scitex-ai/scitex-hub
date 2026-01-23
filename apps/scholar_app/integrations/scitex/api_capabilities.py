"""API endpoint for SciTeX capabilities check."""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .pipelines import SCITEX_AVAILABLE, SCITEX_IMPORT_ERROR

logger = logging.getLogger(__name__)

def api_scitex_capabilities(request):
    """
    API endpoint to get search engine capabilities.

    Returns information about available engines and their supported features.
    """
    if not SCITEX_AVAILABLE:
        return JsonResponse({"available": False, "error": SCITEX_IMPORT_ERROR})

    pipeline = get_parallel_pipeline()
    if not pipeline:
        return JsonResponse(
            {"available": False, "error": "Failed to initialize pipeline"}
        )

    # Get capabilities for all engines
    capabilities = {}
    for engine_name in pipeline.engines:
        capabilities[engine_name] = pipeline.get_engine_capabilities(engine_name)

    return JsonResponse(
        {
            "available": True,
            "engines": capabilities,
            "statistics": pipeline.get_statistics(),
        }
    )


# EOF

# EOF
