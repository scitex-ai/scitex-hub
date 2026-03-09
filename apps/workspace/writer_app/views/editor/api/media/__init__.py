#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Media API views - modular structure."""

from .figures import figures_api, refresh_figures_index, upload_figures
from .tables import tables_api, refresh_tables_index, upload_tables
from .table_data import table_data_api, table_update_api

__all__ = [
    # Figures
    "figures_api",
    "refresh_figures_index",
    "upload_figures",
    # Tables
    "tables_api",
    "refresh_tables_index",
    "upload_tables",
    # Table data
    "table_data_api",
    "table_update_api",
]

# EOF
