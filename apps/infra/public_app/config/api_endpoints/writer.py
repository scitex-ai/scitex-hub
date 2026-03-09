#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Writer API endpoint definitions."""

WRITER_CATEGORY = {
    "name": "Writer API",
    "description": "LaTeX manuscript compilation",
    "base_path": "/writer/api",
    "auth_required": True,
    "endpoints": [
        {
            "method": "POST",
            "path": "/compile/",
            "name": "Compile Manuscript",
            "description": "Compile LaTeX project to PDF",
            "params": [
                {
                    "name": "project_id",
                    "type": "uuid",
                    "required": True,
                    "desc": "Project ID",
                },
                {
                    "name": "output_format",
                    "type": "string",
                    "required": False,
                    "desc": "Output: pdf, html",
                },
            ],
        },
        {
            "method": "GET",
            "path": "/sections/",
            "name": "List Sections",
            "description": "Get manuscript sections",
            "params": [
                {
                    "name": "project_id",
                    "type": "uuid",
                    "required": True,
                    "desc": "Project ID",
                },
            ],
        },
    ],
}
