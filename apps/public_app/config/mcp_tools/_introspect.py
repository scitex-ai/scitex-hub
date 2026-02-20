#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP tool data: introspect and project categories."""

_R = "required"

INTROSPECT_TOOLS = {
    "category": "Introspect",
    "prefix": "introspect_*",
    "icon": "fa-search",
    "tools": [
        {
            "name": "introspect_signature",
            "desc": "Get function/class signature with parameters and types.",
            "params": [
                {"name": "dotted_path", "type": "str", "default": _R},
                {"name": "include_defaults", "type": "bool", "default": "True"},
                {"name": "include_annotations", "type": "bool", "default": "True"},
            ],
            "returns": "str",
        },
        {
            "name": "introspect_source",
            "desc": "Get source code of a Python object.",
            "params": [
                {"name": "dotted_path", "type": "str", "default": _R},
                {"name": "max_lines", "type": "int", "default": "None"},
                {"name": "include_decorators", "type": "bool", "default": "True"},
            ],
            "returns": "str",
        },
        {
            "name": "introspect_dir",
            "desc": "List members of module/class (like dir()). filter: all|public|private.",
            "params": [
                {"name": "dotted_path", "type": "str", "default": _R},
                {"name": "filter", "type": "str", "default": "'public'"},
                {"name": "kind", "type": "str", "default": "None"},
            ],
            "returns": "str",
        },
        {
            "name": "introspect_api",
            "desc": "List the API tree of a module recursively.",
            "params": [
                {"name": "dotted_path", "type": "str", "default": _R},
                {"name": "max_depth", "type": "int", "default": "5"},
                {"name": "docstring", "type": "bool", "default": "False"},
            ],
            "returns": "str",
        },
        {
            "name": "introspect_docstring",
            "desc": "Get docstring of a Python object. format: raw|parsed|summary.",
            "params": [
                {"name": "dotted_path", "type": "str", "default": _R},
                {"name": "format", "type": "str", "default": "'raw'"},
            ],
            "returns": "str",
        },
        {
            "name": "introspect_exports",
            "desc": "Get __all__ exports of a module.",
            "params": [
                {"name": "dotted_path", "type": "str", "default": _R},
            ],
            "returns": "str",
        },
        {
            "name": "introspect_examples",
            "desc": "Find usage examples in tests/examples directories.",
            "params": [
                {"name": "dotted_path", "type": "str", "default": _R},
                {"name": "search_paths", "type": "str", "default": "None"},
                {"name": "max_results", "type": "int", "default": "10"},
            ],
            "returns": "str",
        },
        {
            "name": "introspect_class_hierarchy",
            "desc": "Get class inheritance hierarchy (MRO + subclasses).",
            "params": [
                {"name": "dotted_path", "type": "str", "default": _R},
                {"name": "include_builtins", "type": "bool", "default": "False"},
                {"name": "max_depth", "type": "int", "default": "10"},
            ],
            "returns": "str",
        },
        {
            "name": "introspect_type_hints",
            "desc": "Get detailed type hint analysis for function/class.",
            "params": [
                {"name": "dotted_path", "type": "str", "default": _R},
                {"name": "include_extras", "type": "bool", "default": "True"},
            ],
            "returns": "str",
        },
        {
            "name": "introspect_imports",
            "desc": "Get all imports from a module (AST-based static analysis).",
            "params": [
                {"name": "dotted_path", "type": "str", "default": _R},
                {"name": "categorize", "type": "bool", "default": "True"},
            ],
            "returns": "str",
        },
        {
            "name": "introspect_dependencies",
            "desc": "Get module dependencies (what it imports).",
            "params": [
                {"name": "dotted_path", "type": "str", "default": _R},
                {"name": "recursive", "type": "bool", "default": "False"},
                {"name": "max_depth", "type": "int", "default": "3"},
            ],
            "returns": "str",
        },
        {
            "name": "introspect_call_graph",
            "desc": "Get function call graph (with timeout protection).",
            "params": [
                {"name": "dotted_path", "type": "str", "default": _R},
                {"name": "max_depth", "type": "int", "default": "2"},
                {"name": "timeout_seconds", "type": "int", "default": "10"},
            ],
            "returns": "str",
        },
    ],
}

PROJECT_TOOLS = {
    "category": "Project Files",
    "prefix": "project_*",
    "icon": "fa-folder-open",
    "tools": [
        {
            "name": "project_list_files",
            "desc": "List files and directories in a project directory.",
            "params": [
                {"name": "root_path", "type": "str", "default": _R},
                {"name": "relative_path", "type": "str", "default": "'.'"},
                {"name": "max_depth", "type": "int", "default": "3"},
            ],
            "returns": "str",
        },
        {
            "name": "project_read_file",
            "desc": "Read the content of a file in a project.",
            "params": [
                {"name": "root_path", "type": "str", "default": _R},
                {"name": "relative_path", "type": "str", "default": _R},
            ],
            "returns": "str",
        },
        {
            "name": "project_write_file",
            "desc": "Write or create a file in a project.",
            "params": [
                {"name": "root_path", "type": "str", "default": _R},
                {"name": "relative_path", "type": "str", "default": _R},
                {"name": "content", "type": "str", "default": _R},
            ],
            "returns": "str",
        },
        {
            "name": "project_search_files",
            "desc": "Search project files by name glob and/or content substring.",
            "params": [
                {"name": "root_path", "type": "str", "default": _R},
                {"name": "name_pattern", "type": "str", "default": "''"},
                {"name": "content_pattern", "type": "str", "default": "''"},
            ],
            "returns": "str",
        },
    ],
}

# EOF
