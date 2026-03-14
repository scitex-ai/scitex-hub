"""
Base Design System Views

Core views for the design system including the main page and section template.
"""

import json
from pathlib import Path

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.views import View


def index(request):
    """Dev app index page."""
    return render(request, "dev_app/index.html")


def _load_components():
    """Load components from JSON."""
    components_path = (
        Path(settings.BASE_DIR) / "staticfiles" / "dev_app" / "data" / "components.json"
    )
    components_data = {"components": [], "metadata": {}}
    if components_path.exists():
        with open(components_path, "r") as f:
            components_data = json.load(f)
    return components_data


class DesignSystemView(View):
    """Main design system page - shows colors."""

    template_name = "dev_app/design.html"

    def get(self, request):
        components_data = _load_components()
        context = {
            "components": components_data.get("components", []),
            "metadata": components_data.get("metadata", {}),
        }
        return render(request, self.template_name, context)


# Section configuration for DesignSectionView
DESIGN_SECTIONS = {
    "typography": {
        "title": "Typography",
        "description": "Typography system and font guidelines.",
        "partial": "dev_app/design_partial/typography.html",
    },
    "colors": {
        "title": "Colors",
        "description": "Color palette and semantic color system.",
        "partial": "dev_app/design_partial/colors.html",
    },
    "workspace-colors": {
        "title": "Workspace Colors",
        "description": "Professional workspace colors for Code, Writer, and Vis apps.",
        "partial": "dev_app/design_partial/workspace_colors.html",
    },
    "workspace-icons": {
        "title": "Workspace Icons",
        "description": "Icon system for Code, Writer, and Vis workspaces.",
        "partial": "dev_app/design_partial/workspace_icons.html",
    },
    "theme": {
        "title": "Theme",
        "description": "Theme system and color mode support.",
        "partial": "dev_app/design_partial/theme.html",
    },
    "code-blocks": {
        "title": "Code Blocks",
        "description": "Code syntax highlighting and code block styles.",
        "partial": "dev_app/design_partial/code.html",
    },
    "terminal-log": {
        "title": "Terminal Log",
        "description": "Terminal-style log display for process monitoring.",
        "partial": "dev_app/design_partial/terminal-log.html",
    },
    "terminal": {
        "title": "Terminal",
        "description": "XTerm.js interactive terminal with CSS-based theming.",
        "partial": "dev_app/design_partial/terminal.html",
    },
    "icons": {
        "title": "Icons",
        "description": "Icon system using FontAwesome and custom SVG icons.",
        "partial": "dev_app/design_partial/icons.html",
    },
    "spacing": {
        "title": "Spacing",
        "description": "Spacing system and layout guidelines.",
        "partial": "dev_app/design_partial/spacing.html",
    },
    "guidelines": {
        "title": "Usage Guidelines",
        "description": "Best practices and usage guidelines.",
        "partial": "dev_app/design_partial/guidelines.html",
    },
    # Component sections
    "hero-guideline": {
        "title": "Hero",
        "description": "Large, attention-grabbing header sections for landing pages.",
        "partial": "dev_app/design_partial/hero-guideline.html",
    },
    "badge": {
        "title": "Badge",
        "description": "Small labels for categorization and status indication.",
        "partial": "dev_app/design_partial/badge.html",
    },
    "button": {
        "title": "Button",
        "description": "Versatile button component with multiple variants, sizes, and states.",
        "partial": "dev_app/design_partial/button.html",
    },
    "card": {
        "title": "Card",
        "description": "Flexible content containers with optional headers, body, and footers.",
        "partial": "dev_app/design_partial/card.html",
    },
    "checkbox": {
        "title": "Checkbox",
        "description": "Standard checkboxes for selecting options.",
        "partial": "dev_app/design_partial/checkbox.html",
    },
    "form-input": {
        "title": "Form Input",
        "description": "Text input fields for collecting user input.",
        "partial": "dev_app/design_partial/form-input.html",
    },
    "toggle-button-checkbox": {
        "title": "Toggle Button Checkbox",
        "description": "Toggle switch styled as a button for binary states.",
        "partial": "dev_app/design_partial/toggle-button-checkbox.html",
    },
    "select-dropdown": {
        "title": "Select Dropdown",
        "description": "Dropdown select menus for choosing options.",
        "partial": "dev_app/design_partial/select-dropdown.html",
    },
    "tabs": {
        "title": "Tabs",
        "description": "Tab navigation for organizing content.",
        "partial": "dev_app/design_partial/tabs.html",
    },
    "breadcrumb": {
        "title": "Breadcrumb",
        "description": "Navigation trail showing current location.",
        "partial": "dev_app/design_partial/breadcrumb.html",
    },
    "dropdown-menu": {
        "title": "Dropdown Menu",
        "description": "Contextual menu overlay for displaying actions.",
        "partial": "dev_app/design_partial/dropdown-menu.html",
    },
    "file-upload": {
        "title": "File Upload",
        "description": "File input controls for uploading files.",
        "partial": "dev_app/design_partial/file-upload.html",
    },
    "segmented-radio-control": {
        "title": "Segmented Radio Control",
        "description": "Segmented control for mutually exclusive options.",
        "partial": "dev_app/design_partial/segmented-radio-control.html",
    },
    "navbar": {
        "title": "Navbar",
        "description": "Top navigation bar with branding and links.",
        "partial": "dev_app/design_partial/navbar.html",
    },
    "alerts": {
        "title": "Alerts",
        "description": "Alert messages for contextual feedback.",
        "partial": "dev_app/design_partial/alerts.html",
    },
    "resizer": {
        "title": "Panel Resizer",
        "description": "Draggable panel resizer with expanded hit area.",
        "partial": "dev_app/design_partial/resizer.html",
    },
    "stx-shell-layout": {
        "title": "Workspace Layout",
        "description": "Workspace pane structure, resizers, highlighters, and sizing rules.",
        "partial": "dev_app/design_partial/stx-shell-layout.html",
    },
    "visitor-system": {
        "title": "Visitor System",
        "description": "Anonymous visitor pool, session management, and read-only fallback.",
        "partial": "dev_app/design_partial/visitor-system.html",
    },
}


class DesignSectionView(View):
    """Generic design section page."""

    template_name = "dev_app/design_section_template.html"

    def get(self, request, section):
        components_data = _load_components()

        if section not in DESIGN_SECTIONS:
            raise Http404(f"Section '{section}' not found")

        section_info = DESIGN_SECTIONS[section]
        context = {
            "components": components_data.get("components", []),
            "metadata": components_data.get("metadata", {}),
            "section_title": section_info["title"],
            "section_description": section_info["description"],
            "section_template": section_info["partial"],
        }
        return render(request, self.template_name, context)
