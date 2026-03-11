"""Shared components catalog — available UI components for app plugins.

Lists CSS and TypeScript components that apps can import from the shared
static directory. Used by scaffold to generate import statements and by
docs to show available components.
"""

from __future__ import annotations

SHARED_COMPONENTS = {
    "seekbar": {
        "label": "ScitexSeekbar",
        "description": "Dual-handle range slider with value display",
        "css": [],
        "ts": ["shared/ts/components/seekbar.ts"],
        "usage": '<scitex-seekbar min="0" max="100" value="50"></scitex-seekbar>',
    },
    "data-table": {
        "label": "DataTableManager",
        "description": "Full spreadsheet component with selection, editing, virtual scroll, CSV import",
        "css": [
            "shared/css/components/data-table/index.css",
            "shared/css/components/data-table/data-table.css",
        ],
        "ts": ["shared/ts/components/data-table/DataTableManager.ts"],
        "usage": "new DataTableManager(container, options)",
    },
    "resizer": {
        "label": "Resizer",
        "description": "Horizontal/vertical panel splitter",
        "css": ["shared/css/components/resizer.css"],
        "ts": ["shared/ts/components/resizer/index.ts"],
        "usage": "new HorizontalResizer(leftEl, rightEl, options)",
    },
    "confirm-modal": {
        "label": "ConfirmModal",
        "description": "Modern confirmation dialog with customizable buttons",
        "css": [],
        "ts": ["shared/ts/components/confirm-modal.ts"],
        "usage": 'await confirmModal({ title: "Delete?", message: "...", confirmLabel: "Delete" })',
    },
    "tabs": {
        "label": "Tabs",
        "description": "Tab navigation component",
        "css": ["shared/css/components/tabs.css"],
        "ts": [],
        "usage": '<div class="tab-nav"><button class="tab-btn active">Tab 1</button></div>',
    },
    "toggles": {
        "label": "Toggles",
        "description": "Toggle switch component",
        "css": ["shared/css/components/toggles.css"],
        "ts": [],
        "usage": (
            '<label class="toggle-switch">'
            '<input type="checkbox">'
            '<span class="toggle-slider"></span>'
            "</label>"
        ),
    },
    "dropdown": {
        "label": "Dropdown",
        "description": "Dropdown menu component",
        "css": ["shared/css/components/dropdown.css"],
        "ts": [],
        "usage": (
            '<div class="dropdown">'
            '<button class="dropdown-toggle">Menu</button>'
            '<div class="dropdown-menu">...</div>'
            "</div>"
        ),
    },
}


def get_component(name: str) -> dict | None:
    """Get a shared component by name."""
    return SHARED_COMPONENTS.get(name)


def get_all_components() -> dict:
    """Get all available shared components."""
    return dict(SHARED_COMPONENTS)


def get_css_imports(component_names: list[str]) -> list[str]:
    """Get CSS import paths for a list of components."""
    imports = []
    for name in component_names:
        comp = SHARED_COMPONENTS.get(name)
        if comp:
            imports.extend(comp.get("css", []))
    return imports


def get_ts_imports(component_names: list[str]) -> list[str]:
    """Get TypeScript import paths for a list of components."""
    imports = []
    for name in component_names:
        comp = SHARED_COMPONENTS.get(name)
        if comp:
            imports.extend(comp.get("ts", []))
    return imports


# EOF
