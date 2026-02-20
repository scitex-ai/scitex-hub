#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP tool data: plt and diagram categories."""

_R = "required"

PLT_TOOLS = {
    "category": "Plotting",
    "prefix": "plt_*",
    "icon": "fa-chart-line",
    "tools": [
        {
            "name": "plt_plot",
            "desc": "Create a matplotlib figure from a declarative specification.",
            "params": [
                {"name": "spec", "type": "dict", "default": _R},
                {"name": "output_path", "type": "str", "default": _R},
                {"name": "dpi", "type": "int", "default": "300"},
                {"name": "save_recipe", "type": "bool", "default": "True"},
            ],
            "returns": "dict",
        },
        {
            "name": "plt_reproduce",
            "desc": "Reproduce a figure from a saved YAML recipe.",
            "params": [
                {"name": "recipe_path", "type": "str", "default": _R},
                {"name": "output_path", "type": "str", "default": "None"},
                {"name": "format", "type": "str", "default": "'png'"},
                {"name": "dpi", "type": "int", "default": "300"},
            ],
            "returns": "dict",
        },
        {
            "name": "plt_compose",
            "desc": "Compose multiple figures into a single figure with panel labels.",
            "params": [
                {"name": "sources", "type": "list[str]", "default": _R},
                {"name": "output_path", "type": "str", "default": _R},
                {"name": "layout", "type": "str", "default": "'horizontal'"},
                {"name": "gap_mm", "type": "float", "default": "5.0"},
                {"name": "dpi", "type": "int", "default": "300"},
                {"name": "panel_labels", "type": "bool", "default": "True"},
            ],
            "returns": "dict",
        },
        {
            "name": "plt_info",
            "desc": "Get information about a recipe file.",
            "params": [
                {"name": "recipe_path", "type": "str", "default": _R},
                {"name": "verbose", "type": "bool", "default": "False"},
            ],
            "returns": "dict",
        },
        {
            "name": "plt_validate",
            "desc": "Validate that a recipe can reproduce its original figure.",
            "params": [
                {"name": "recipe_path", "type": "str", "default": _R},
                {"name": "mse_threshold", "type": "float", "default": "100.0"},
            ],
            "returns": "dict",
        },
        {
            "name": "plt_crop",
            "desc": "Crop whitespace from a figure image.",
            "params": [
                {"name": "input_path", "type": "str", "default": _R},
                {"name": "output_path", "type": "str", "default": "None"},
                {"name": "margin_mm", "type": "float", "default": "1.0"},
            ],
            "returns": "dict",
        },
        {
            "name": "plt_extract_data",
            "desc": "Extract plotted data arrays from a saved recipe.",
            "params": [
                {"name": "recipe_path", "type": "str", "default": _R},
            ],
            "returns": "dict",
        },
    ],
}

DIAGRAM_TOOLS = {
    "category": "Diagrams",
    "prefix": "diagram_*",
    "icon": "fa-project-diagram",
    "tools": [
        {
            "name": "diagram_create",
            "desc": "Create a diagram from a YAML specification file or dictionary.",
            "params": [
                {"name": "spec_dict", "type": "dict", "default": "None"},
                {"name": "spec_path", "type": "str", "default": "None"},
            ],
            "returns": "dict",
        },
        {
            "name": "diagram_compile_mermaid",
            "desc": "Compile diagram specification to Mermaid format.",
            "params": [
                {"name": "spec_dict", "type": "dict", "default": "None"},
                {"name": "spec_path", "type": "str", "default": "None"},
                {"name": "output_path", "type": "str", "default": "None"},
            ],
            "returns": "str",
        },
        {
            "name": "diagram_compile_graphviz",
            "desc": "Compile diagram specification to Graphviz DOT format.",
            "params": [
                {"name": "spec_dict", "type": "dict", "default": "None"},
                {"name": "spec_path", "type": "str", "default": "None"},
                {"name": "output_path", "type": "str", "default": "None"},
            ],
            "returns": "str",
        },
        {
            "name": "diagram_render",
            "desc": "Render diagram to image file (PNG, SVG, PDF).",
            "params": [
                {"name": "spec_dict", "type": "dict", "default": "None"},
                {"name": "spec_path", "type": "str", "default": "None"},
                {"name": "output_path", "type": "str", "default": _R},
            ],
            "returns": "dict",
        },
        {
            "name": "diagram_split",
            "desc": "Split a large diagram into smaller parts for multi-column layouts.",
            "params": [
                {"name": "spec_path", "type": "str", "default": _R},
                {"name": "max_nodes_per_part", "type": "int", "default": "10"},
                {"name": "strategy", "type": "str", "default": "'by_groups'"},
            ],
            "returns": "list",
        },
    ],
}

# EOF
