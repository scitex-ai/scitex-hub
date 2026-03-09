#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Project API endpoint definitions."""

PROJECT_CATEGORY = {
    "name": "Project API",
    "description": "Project file and Git operations",
    "base_path": "/project/api",
    "auth_required": True,
    "endpoints": [
        {
            "method": "GET",
            "path": "/files/",
            "name": "List Files",
            "description": "List project files",
            "params": [
                {
                    "name": "project_id",
                    "type": "uuid",
                    "required": True,
                    "desc": "Project ID",
                },
            ],
        },
        {
            "method": "POST",
            "path": "/git/commit/",
            "name": "Git Commit",
            "description": "Commit changes to project",
            "params": [
                {
                    "name": "project_id",
                    "type": "uuid",
                    "required": True,
                    "desc": "Project ID",
                },
                {
                    "name": "message",
                    "type": "string",
                    "required": True,
                    "desc": "Commit message",
                },
            ],
        },
    ],
}
