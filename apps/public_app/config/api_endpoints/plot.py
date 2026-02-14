#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plot API endpoint definitions."""

PLOT_CATEGORY = {
    "name": "Plot API",
    "description": "Create publication-ready figures. Supports GET (browser URL), POST JSON (full spec), and POST multipart (CSV upload).",
    "base_path": "/api",
    "auth_required": False,
    "endpoints": [
        {
            "method": "GET",
            "path": "/plot/",
            "name": "Quick Plot",
            "description": "Create figures by opening a URL in your browser. Returns raw PNG image.",
            "params": [
                {
                    "name": "kind",
                    "type": "string",
                    "required": True,
                    "desc": "Plot type: line, scatter, bar, barh, hist, box, violin, pie, heatmap, step, errorbar, stem",
                },
                {
                    "name": "x",
                    "type": "string",
                    "required": False,
                    "desc": "Comma-separated numbers or labels (for line, scatter, bar)",
                },
                {
                    "name": "y",
                    "type": "string",
                    "required": False,
                    "desc": "Comma-separated numbers (for line, scatter, bar)",
                },
                {
                    "name": "data",
                    "type": "string",
                    "required": False,
                    "desc": "Comma-separated numbers (for hist, box, violin, pie, heatmap)",
                },
                {
                    "name": "data2..data6",
                    "type": "string",
                    "required": False,
                    "desc": "Additional groups (for box, violin)",
                },
                {
                    "name": "labels",
                    "type": "string",
                    "required": False,
                    "desc": "Comma-separated labels (for bar, pie, box, violin)",
                },
                {
                    "name": "yerr",
                    "type": "string",
                    "required": False,
                    "desc": "Comma-separated Y error bar values",
                },
                {
                    "name": "nrows",
                    "type": "int",
                    "required": False,
                    "desc": "Matrix rows for heatmap",
                },
                {
                    "name": "ncols",
                    "type": "int",
                    "required": False,
                    "desc": "Matrix columns for heatmap",
                },
                {
                    "name": "color",
                    "type": "string",
                    "required": False,
                    "desc": "Color name or hex",
                },
                {
                    "name": "title",
                    "type": "string",
                    "required": False,
                    "desc": "Plot title",
                },
                {
                    "name": "xlabel",
                    "type": "string",
                    "required": False,
                    "desc": "X-axis label",
                },
                {
                    "name": "ylabel",
                    "type": "string",
                    "required": False,
                    "desc": "Y-axis label",
                },
                {
                    "name": "width",
                    "type": "int",
                    "required": False,
                    "desc": "Figure width in mm (default: 80)",
                },
                {
                    "name": "height",
                    "type": "int",
                    "required": False,
                    "desc": "Figure height in mm (default: 60)",
                },
            ],
        },
        {
            "method": "POST",
            "path": "/plot/",
            "name": "Create Plot (JSON)",
            "description": "Create figures using full figrecipe declarative specification. Supports multiple overlaid plots, custom styling, and multi-panel layouts.",
            "params": [
                {
                    "name": "figure",
                    "type": "object",
                    "required": False,
                    "desc": "Figure settings: width_mm, height_mm",
                },
                {
                    "name": "plots",
                    "type": "array",
                    "required": True,
                    "desc": "Array of plot specs: {type, x, y, color, label, ...}",
                },
                {
                    "name": "xlabel",
                    "type": "string",
                    "required": False,
                    "desc": "X-axis label",
                },
                {
                    "name": "ylabel",
                    "type": "string",
                    "required": False,
                    "desc": "Y-axis label",
                },
                {
                    "name": "title",
                    "type": "string",
                    "required": False,
                    "desc": "Plot title",
                },
                {
                    "name": "legend",
                    "type": "bool",
                    "required": False,
                    "desc": "Show legend",
                },
                {
                    "name": "figure_format",
                    "type": "string",
                    "required": False,
                    "desc": "Set to 'png' for raw PNG instead of JSON with base64",
                },
            ],
        },
        {
            "method": "POST",
            "path": "/plot/",
            "name": "Plot from CSV Upload",
            "description": "Upload a CSV file and specify column names. Content-Type: multipart/form-data.",
            "params": [
                {
                    "name": "csv_file",
                    "type": "file",
                    "required": True,
                    "desc": "CSV or TSV file (max 10 MB)",
                },
                {
                    "name": "kind",
                    "type": "string",
                    "required": True,
                    "desc": "Plot type: line, scatter, bar, hist, box, violin, etc.",
                },
                {
                    "name": "x_col",
                    "type": "string",
                    "required": False,
                    "desc": "Column name for X-axis",
                },
                {
                    "name": "y_col",
                    "type": "string",
                    "required": False,
                    "desc": "Column name for Y-axis",
                },
                {
                    "name": "data_col",
                    "type": "string",
                    "required": False,
                    "desc": "Column name for distribution data",
                },
                {
                    "name": "color",
                    "type": "string",
                    "required": False,
                    "desc": "Color name or hex",
                },
                {
                    "name": "title",
                    "type": "string",
                    "required": False,
                    "desc": "Plot title",
                },
            ],
        },
    ],
}
