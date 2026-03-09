"""figrecipe handler package — thin Django wrappers around figrecipe Python API.

Exports HANDLERS dict for the catch-all dispatcher (figrecipe.py),
plus individual parameterized handlers for call/<id> and download/<fmt>.
"""

from ._annotation import (
    handle_get_captions,
    handle_update_annotation_position,
    handle_update_caption,
)
from ._axis import (
    handle_get_axes_positions,
    handle_get_axis_info,
    handle_get_labels,
    handle_get_legend_info,
    handle_update_axes_position,
    handle_update_axis_type,
    handle_update_label,
    handle_update_legend_position,
)
from ._core import handle_hitmap, handle_ping, handle_preview, handle_update
from ._datatable import (
    handle_datatable_data,
    handle_datatable_import,
    handle_datatable_plot,
)
from ._downloads import handle_download_csv, handle_download_fig
from ._elements import (
    handle_calls,
    handle_single_call,
    handle_update_call,
    handle_update_element_color,
)
from ._files import (
    handle_api_delete,
    handle_api_download_recipe,
    handle_api_duplicate,
    handle_api_files,
    handle_api_new,
    handle_api_rename,
    handle_api_switch,
)
from ._image import (
    handle_add_image_from_url,
    handle_add_image_panel,
    handle_load_recipe,
)
from ._style import (
    handle_diff,
    handle_get_theme,
    handle_list_themes,
    handle_overrides,
    handle_restore,
    handle_save,
    handle_style,
    handle_switch_theme,
)

# fmt: off
HANDLERS = {
    # ── Core ──────────────────────────────────────────────────────
    "preview":                      handle_preview,
    "ping":                         handle_ping,
    "update":                       handle_update,
    "hitmap":                       handle_hitmap,

    # ── Style ─────────────────────────────────────────────────────
    "style":                        handle_style,
    "overrides":                    handle_overrides,
    "theme":                        handle_get_theme,
    "list_themes":                  handle_list_themes,
    "switch_theme":                 handle_switch_theme,
    "save":                         handle_save,
    "restore":                      handle_restore,
    "diff":                         handle_diff,

    # ── Axis ──────────────────────────────────────────────────────
    "get_labels":                   handle_get_labels,
    "update_label":                 handle_update_label,
    "update_axis_type":             handle_update_axis_type,
    "get_axis_info":                handle_get_axis_info,
    "get_legend_info":              handle_get_legend_info,
    "update_legend_position":       handle_update_legend_position,
    "get_axes_positions":           handle_get_axes_positions,
    "update_axes_position":         handle_update_axes_position,

    # ── Elements ──────────────────────────────────────────────────
    "calls":                        handle_calls,
    "update_call":                  handle_update_call,
    "update_element_color":         handle_update_element_color,

    # ── Annotation ────────────────────────────────────────────────
    "update_annotation_position":   handle_update_annotation_position,
    "get_captions":                 handle_get_captions,
    "update_caption":               handle_update_caption,

    # ── Datatable ─────────────────────────────────────────────────
    "datatable/data":               handle_datatable_data,
    "datatable/plot":               handle_datatable_plot,
    "datatable/import":             handle_datatable_import,

    # ── Downloads ─────────────────────────────────────────────────
    "download/csv":                 handle_download_csv,
    # download/<fmt> handled by prefix match in dispatcher

    # ── Image drops ───────────────────────────────────────────────
    "add_image_panel":              handle_add_image_panel,
    "add_image_from_url":           handle_add_image_from_url,
    "load_recipe":                  handle_load_recipe,

    # ── Files (Workflow 1) ────────────────────────────────────────
    "api/files":                    handle_api_files,
    "api/switch":                   handle_api_switch,
    "api/new":                      handle_api_new,
    "api/delete":                   handle_api_delete,
    "api/rename":                   handle_api_rename,
    "api/duplicate":                handle_api_duplicate,
    "api/download":                 handle_api_download_recipe,
}
# fmt: on

__all__ = [
    "HANDLERS",
    "handle_single_call",
    "handle_download_fig",
]
