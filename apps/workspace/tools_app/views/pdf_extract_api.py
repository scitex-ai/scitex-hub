#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract text and embedded figures from a PDF, using poppler.

WHY POPPLER AND NOT AN OCR ENGINE. The operator asked for OCR that picks up
"not just characters but images and tables too". Measured in the running
production container (scitex-hub-prod-django-1) on 2026-08-16:

    pdftotext   /usr/bin/pdftotext     present
    pdfimages   /usr/bin/pdfimages     present
    pdftoppm    /usr/bin/pdftoppm      present
    gs          /usr/bin/gs            present
    tesseract   MISSING

So text and figures can be extracted TODAY with nothing added to the image,
because a scientific PDF almost always carries a real text layer — running OCR
over it would be slower AND less accurate than reading the text that is already
there. True OCR is only needed for a SCANNED page, which has no text layer, and
that path needs tesseract in the image.

This module deliberately does only the part that works now, and says so when it
meets a PDF it cannot read (see the empty-text branch) rather than returning a
blank result that looks like success.

WHERE THIS SHOULD EVENTUALLY LIVE. Hub is meant to be a thin wrapper, and
shelling out to poppler is exactly the kind of logic that belongs in a package —
the same argument that moved whisper handling out of hub and into scitex-audio
(PR #611). It is here because there is no document-processing package to put it
in yet, not because this is its home. Carded separately.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

# Generous enough for a paper, small enough that one upload cannot exhaust the
# worker. A rejected file says the limit; it does not fail silently.
_MAX_BYTES = 50 * 1024 * 1024
# A malformed or enormous PDF must not hold a worker forever.
_TIMEOUT_S = 60
# Cap on figures returned, so a slide deck with 400 images does not build a
# 300 MB JSON response. The response reports the true total either way.
_MAX_FIGURES = 40


def _binary(name: str) -> str | None:
    """Return the path to a poppler binary, or None when it is absent."""
    return shutil.which(name)


@require_http_methods(["GET"])
@login_required
def api_pdf_extract_capabilities(request):
    """Report what this deployment can actually do, before the user tries.

    The page uses this to disable controls it cannot honour, rather than
    offering a button that fails on click.
    """
    return JsonResponse(
        {
            "text": bool(_binary("pdftotext")),
            "figures": bool(_binary("pdfimages")),
            # Not wired yet; reported so the UI can say "scanned PDFs are not
            # supported here" instead of appearing to support them.
            "ocr": bool(_binary("tesseract")),
        }
    )


@login_required
@require_http_methods(["POST"])
def api_pdf_extract(request):
    """Extract the text layer, and optionally the embedded figures, from a PDF.

    multipart POST:
      - 'pdf'     the file
      - 'layout'  '1' to preserve column/table layout (pdftotext -layout)
      - 'figures' '1' to also extract embedded images

    Returns {"text": ..., "chars": n, "figures": [...], "figure_count": n}
    or {"error": ...} with a status code that distinguishes the causes.
    """
    pdftotext = _binary("pdftotext")
    if not pdftotext:
        return JsonResponse(
            {
                "error": (
                    "PDF text extraction is unavailable: poppler's pdftotext is "
                    "not installed in this deployment."
                )
            },
            status=503,
        )

    upload = request.FILES.get("pdf")
    if not upload:
        return JsonResponse({"error": "pdf file required"}, status=400)
    if upload.size > _MAX_BYTES:
        return JsonResponse(
            {
                "error": (
                    f"That PDF is {upload.size // (1024 * 1024)} MB. "
                    f"The limit is {_MAX_BYTES // (1024 * 1024)} MB."
                )
            },
            status=413,
        )

    want_layout = request.POST.get("layout") == "1"
    want_figures = request.POST.get("figures") == "1"

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "input.pdf")
        with open(pdf_path, "wb") as fh:
            for chunk in upload.chunks():
                fh.write(chunk)

        cmd = [pdftotext]
        if want_layout:
            cmd.append("-layout")
        cmd += [pdf_path, "-"]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=_TIMEOUT_S
            )
        except subprocess.TimeoutExpired:
            return JsonResponse(
                {"error": f"Extraction timed out after {_TIMEOUT_S}s."}, status=504
            )
        if proc.returncode != 0:
            detail = (proc.stderr or "").strip().splitlines()
            return JsonResponse(
                {
                    "error": "Could not read that PDF"
                    + (f": {detail[-1]}" if detail else ".")
                },
                status=400,
            )

        text = proc.stdout

        figures: list[dict] = []
        figure_count = 0
        if want_figures and _binary("pdfimages"):
            figure_count, figures = _extract_figures(tmpdir, pdf_path)

    # An empty text layer is the SCANNED-PDF case, and it is the one place this
    # tool would otherwise look broken: pdftotext exits 0 and returns nothing.
    # Say what happened and what would be needed, rather than returning "".
    if not text.strip():
        return JsonResponse(
            {
                "text": "",
                "chars": 0,
                "figures": figures,
                "figure_count": figure_count,
                "note": (
                    "This PDF has no text layer — it is most likely a scan. "
                    "Reading it needs OCR, which is not installed on this "
                    "deployment yet. Any embedded figures were still extracted."
                ),
            }
        )

    return JsonResponse(
        {
            "text": text,
            "chars": len(text),
            "figures": figures,
            "figure_count": figure_count,
        }
    )


def _extract_figures(tmpdir: str, pdf_path: str) -> tuple[int, list[dict]]:
    """Return (total found, up to _MAX_FIGURES as base64 PNG data URIs)."""
    import base64

    outdir = os.path.join(tmpdir, "figs")
    os.makedirs(outdir, exist_ok=True)
    try:
        subprocess.run(
            [_binary("pdfimages"), "-png", "-p", pdf_path, os.path.join(outdir, "fig")],
            capture_output=True,
            timeout=_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return 0, []

    names = sorted(n for n in os.listdir(outdir) if n.endswith(".png"))
    figures = []
    for name in names[:_MAX_FIGURES]:
        path = os.path.join(outdir, name)
        # Skip the 1x1 spacers and hairline rules that PDFs are full of; they
        # are not figures and would bury the real ones.
        if os.path.getsize(path) < 4096:
            continue
        with open(path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("ascii")
        figures.append({"name": name, "image": f"data:image/png;base64,{b64}"})
    return len(names), figures


# EOF
