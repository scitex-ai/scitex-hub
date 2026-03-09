#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-cloud/apps/scholar_app/views/bibtex/enrichment.py

"""
BibTeX Enrichment API

Synchronous BibTeX enrichment endpoint for API access.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
def bibtex_enrich_sync(request):
    """
    Synchronous BibTeX enrichment API endpoint.

    Upload a BibTeX file and get the enriched version directly.
    Requires API key authentication.

    Usage:
        curl https://scitex.cloud/scholar/api/bibtex/enrich/ \
          -H "Authorization: Bearer YOUR_API_KEY" \
          -F "bibtex_file=@original.bib" \
          -o enriched.bib
    """
    from scitex.scholar.pipelines import ScholarPipelineMetadataParallel
    from scitex.scholar.storage import BibTeXHandler

    # Check API authentication (decorator applied in urls.py)
    if not hasattr(request, "api_user"):
        return JsonResponse(
            {
                "success": False,
                "error": "API key required",
                "detail": "Use Authorization: Bearer YOUR_API_KEY header",
            },
            status=401,
        )

    # Check if file was uploaded
    if "bibtex_file" not in request.FILES:
        return JsonResponse(
            {
                "success": False,
                "error": "No file uploaded",
                "detail": "Include bibtex_file in multipart form data",
            },
            status=400,
        )

    bibtex_file = request.FILES["bibtex_file"]

    # Validate file extension
    if not bibtex_file.name.endswith(".bib"):
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid file type",
                "detail": "File must have .bib extension",
            },
            status=400,
        )

    # Get parameters
    use_cache = request.POST.get("use_cache", "true").lower() in (
        "true",
        "1",
        "on",
        "yes",
    )
    num_workers = int(request.POST.get("num_workers", 4))

    try:
        # Save to temporary file
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".bib", delete=False
        ) as tmp_input:
            for chunk in bibtex_file.chunks():
                tmp_input.write(chunk)
            tmp_input_path = Path(tmp_input.name)

        # Load papers
        bibtex_handler = BibTeXHandler()
        papers = bibtex_handler.papers_from_bibtex(tmp_input_path)

        if not papers:
            return JsonResponse(
                {
                    "success": False,
                    "error": "No papers found",
                    "detail": "BibTeX file contains no valid entries",
                },
                status=400,
            )

        # Enrich papers
        pipeline = ScholarPipelineMetadataParallel(num_workers=num_workers)

        async def enrich():
            return await asyncio.wait_for(
                pipeline.enrich_papers_async(
                    papers=papers,
                    force=not use_cache,
                ),
                timeout=600,
            )

        enriched_papers = asyncio.run(enrich())

        # Create temporary output file path
        tmp_output = tempfile.NamedTemporaryFile(
            mode="w", suffix=".bib", delete=False, encoding="utf-8"
        )
        tmp_output_path = Path(tmp_output.name)
        tmp_output.close()

        bibtex_handler.papers_to_bibtex(enriched_papers, tmp_output_path)

        # Return enriched file
        response = FileResponse(
            open(tmp_output_path, "rb"), content_type="application/x-bibtex"
        )

        original_name = Path(bibtex_file.name).stem
        response["Content-Disposition"] = (
            f'attachment; filename="{original_name}-enriched.bib"'
        )

        # Cleanup temp files
        tmp_input_path.unlink(missing_ok=True)

        return response

    except asyncio.TimeoutError:
        return JsonResponse(
            {
                "success": False,
                "error": "Enrichment timeout",
                "detail": "Processing exceeded 10 minutes",
            },
            status=408,
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": "Enrichment failed", "detail": str(e)},
            status=500,
        )


# EOF
