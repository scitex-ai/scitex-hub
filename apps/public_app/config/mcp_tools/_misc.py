#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP tool data: clew, template, dev, audio, ui, capture, usage categories."""

_R = "required"

CLEW_TOOLS = {
    "category": "Clew (Provenance)",
    "prefix": "clew_*",
    "icon": "fa-link",
    "tools": [
        {
            "name": "clew_list",
            "desc": "List all tracked runs with verification status.",
            "params": [
                {"name": "limit", "type": "int", "default": "50"},
                {"name": "status_filter", "type": "str", "default": "None"},
            ],
            "returns": "str",
        },
        {
            "name": "clew_run",
            "desc": "Verify a specific session run by checking all file hashes.",
            "params": [
                {"name": "session_or_path", "type": "str", "default": _R},
            ],
            "returns": "str",
        },
        {
            "name": "clew_chain",
            "desc": "Verify the dependency chain for a target file.",
            "params": [
                {"name": "target_file", "type": "str", "default": _R},
            ],
            "returns": "str",
        },
        {
            "name": "clew_status",
            "desc": "Show verification status summary (like git status).",
            "params": [],
            "returns": "str",
        },
        {
            "name": "clew_stats",
            "desc": "Show verification database statistics.",
            "params": [],
            "returns": "str",
        },
        {
            "name": "clew_mermaid",
            "desc": "Generate Mermaid diagram for verification DAG.",
            "params": [
                {"name": "session_id", "type": "str", "default": "None"},
                {"name": "target_file", "type": "str", "default": "None"},
            ],
            "returns": "str",
        },
    ],
}

TEMPLATE_TOOLS = {
    "category": "Templates",
    "prefix": "template_*",
    "icon": "fa-copy",
    "tools": [
        {
            "name": "template_clone_template",
            "desc": "Create a new project by cloning a template.",
            "params": [
                {"name": "template_id", "type": "str", "default": _R},
                {"name": "project_name", "type": "str", "default": _R},
                {"name": "target_dir", "type": "str", "default": "None"},
            ],
            "returns": "str",
        },
        {
            "name": "template_list_git_strategies",
            "desc": "List available git initialization strategies for template cloning.",
            "params": [],
            "returns": "str",
        },
        {
            "name": "template_get_code_template",
            "desc": "Get a code template for scripts and modules (session, io, config, etc.).",
            "params": [
                {"name": "template_id", "type": "str", "default": _R},
                {"name": "filepath", "type": "str", "default": "None"},
                {"name": "docstring", "type": "str", "default": "None"},
            ],
            "returns": "str",
        },
        {
            "name": "template_list_code_templates",
            "desc": "List all available code templates for scripts and modules.",
            "params": [],
            "returns": "str",
        },
    ],
}

DEV_TOOLS = {
    "category": "Dev",
    "prefix": "dev_*",
    "icon": "fa-code",
    "tools": [
        {
            "name": "dev_list_versions",
            "desc": "List versions across the scitex ecosystem.",
            "params": [
                {"name": "packages", "type": "list[str]", "default": "None"},
            ],
            "returns": "str",
        },
        {
            "name": "dev_get_config",
            "desc": "Get current developer configuration.",
            "params": [],
            "returns": "str",
        },
        {
            "name": "dev_test_local",
            "desc": "Run project tests locally via pytest.",
            "params": [
                {"name": "module", "type": "str", "default": "''"},
                {"name": "fast", "type": "bool", "default": "False"},
                {"name": "coverage", "type": "bool", "default": "False"},
            ],
            "returns": "str",
        },
        {
            "name": "dev_test_hpc",
            "desc": "Run project tests on HPC (Spartan) via Slurm.",
            "params": [
                {"name": "module", "type": "str", "default": "''"},
                {"name": "fast", "type": "bool", "default": "False"},
                {"name": "hpc_cpus", "type": "int", "default": "8"},
            ],
            "returns": "str",
        },
        {
            "name": "dev_test_hpc_poll",
            "desc": "Check HPC test job status.",
            "params": [
                {"name": "job_id", "type": "str", "default": "None"},
            ],
            "returns": "str",
        },
        {
            "name": "dev_test_hpc_result",
            "desc": "Fetch full HPC test output.",
            "params": [
                {"name": "job_id", "type": "str", "default": "None"},
            ],
            "returns": "str",
        },
        {
            "name": "dev_rename",
            "desc": "Bulk rename files, contents, directories, and symlinks.",
            "params": [
                {"name": "pattern", "type": "str", "default": _R},
                {"name": "replacement", "type": "str", "default": _R},
                {"name": "directory", "type": "str", "default": "'.'"},
            ],
            "returns": "str",
        },
    ],
}

AUDIO_UI_TOOLS = {
    "category": "Audio, UI & Capture",
    "prefix": "audio_* / ui_* / capture_*",
    "icon": "fa-volume-up",
    "tools": [
        {
            "name": "audio_speak",
            "desc": "Convert text to speech with smart routing.",
            "params": [
                {"name": "text", "type": "str", "default": _R},
                {"name": "backend", "type": "str", "default": "None"},
                {"name": "voice", "type": "str", "default": "None"},
            ],
            "returns": "str",
        },
        {
            "name": "ui_notify",
            "desc": "Send a notification via configured backends.",
            "params": [
                {"name": "message", "type": "str", "default": _R},
                {"name": "title", "type": "str", "default": "None"},
                {"name": "level", "type": "str", "default": "'info'"},
            ],
            "returns": "str",
        },
        {
            "name": "ui_get_notification_config",
            "desc": "Get current notification configuration.",
            "params": [],
            "returns": "str",
        },
        {
            "name": "capture_capture_screenshot",
            "desc": "Capture screenshot - monitor, window, browser, or everything.",
            "params": [
                {"name": "monitor_id", "type": "int", "default": "0"},
                {"name": "all", "type": "bool", "default": "False"},
                {"name": "quality", "type": "int", "default": "85"},
            ],
            "returns": "str",
        },
    ],
}

USAGE_TOOLS = {
    "category": "Usage",
    "prefix": "usage_*",
    "icon": "fa-book-open",
    "tools": [
        {
            "name": "usage_show",
            "desc": "Show usage examples for a scitex module (plt, stats, session, etc.).",
            "params": [
                {"name": "topic", "type": "str", "default": "''"},
            ],
            "returns": "str",
        },
        {
            "name": "usage_list",
            "desc": "List available usage topics.",
            "params": [],
            "returns": "str",
        },
    ],
}

# EOF
