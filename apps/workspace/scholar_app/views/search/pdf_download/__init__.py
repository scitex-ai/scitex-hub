#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF download package for Scholar Search.

Provides server-side PDF download functionality using scitex.scholar's
PDF downloader with stealth mode support.
"""

from __future__ import annotations

from .bulk import api_download_pdf_bulk
from .single import api_download_pdf
from .status import api_check_pdf_status, api_serve_pdf

__all__ = [
    "api_download_pdf",
    "api_check_pdf_status",
    "api_download_pdf_bulk",
    "api_serve_pdf",
]


# EOF
