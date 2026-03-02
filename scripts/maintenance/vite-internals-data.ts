/**
 * Data for vite-internals migration: directory and file renames.
 * Format: [parentDir, oldName, newName]
 */

// Directory renames
export const DIR_RENAMES: [string, string, string][] = [
  // vis_app
  ["apps/vis_app/static/vis_app/ts", "vis", "_vis"],
  ["apps/vis_app/static/vis_app/ts", "vis-editor", "_vis-editor"],
  // console_app
  ["apps/console_app/static/console_app/ts", "workspace", "_workspace"],
  // writer_app: module subdirs
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "spell-checker",
    "_spell-checker",
  ],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "monaco-editor",
    "_monaco-editor",
  ],
  ["apps/writer_app/static/writer_app/ts/modules", "monaco", "_monaco"],
  ["apps/writer_app/static/writer_app/ts/modules", "pdf-viewer", "_pdf-viewer"],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "compilation",
    "_compilation",
  ],
  ["apps/writer_app/static/writer_app/ts/modules", "file-tabs", "_file-tabs"],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "tables-panel",
    "_tables-panel",
  ],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "figures-panel",
    "_figures-panel",
  ],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "citations-panel",
    "_citations-panel",
  ],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "table-preview-modal",
    "_table-preview-modal",
  ],
  ["apps/writer_app/static/writer_app/ts/modules", "file_tree", "_file_tree"],
  ["apps/writer_app/static/writer_app/ts/modules", "file-tree", "_file-tree"],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "editor-controls",
    "_editor-controls",
  ],
  // writer_app: other internal dirs
  ["apps/writer_app/static/writer_app/ts", "writer", "_writer"],
  [
    "apps/writer_app/static/writer_app/ts/utils",
    "section-dropdown",
    "_section-dropdown",
  ],
  // shared: workspace-files-tree
  ["static/shared/ts/components/workspace-files-tree", "handlers", "_handlers"],
  ["static/shared/ts/components/workspace-files-tree", "modals", "_modals"],
  // shared: media-editor
  ["static/shared/ts/components/media-editor", "panels", "_panels"],
  // shared: collaboration
  ["static/shared/ts/collaboration", "ot", "_ot"],
  ["static/shared/ts/collaboration", "writer", "_writer"],
  // shared: utils
  ["static/shared/ts/utils", "element-inspector", "_element-inspector"],
  // shared: components
  ["static/shared/ts/components", "product-tour", "_product-tour"],
  // public_app
  ["apps/public_app/static/public_app/ts", "server-status", "_server-status"],
  // scholar_app
  [
    "apps/scholar_app/static/scholar_app/ts/common",
    "scholar-index",
    "_scholar-index",
  ],
  [
    "apps/scholar_app/static/scholar_app/ts/bibtex",
    "enrichment",
    "_enrichment",
  ],
];

// Individual file renames
export const FILE_RENAMES: [string, string, string][] = [
  // shared/data-table
  ["static/shared/ts/components/data-table", "TableData.ts", "_TableData.ts"],
  [
    "static/shared/ts/components/data-table",
    "TableColumnRow.ts",
    "_TableColumnRow.ts",
  ],
  [
    "static/shared/ts/components/data-table",
    "TableClipboard.ts",
    "_TableClipboard.ts",
  ],
  [
    "static/shared/ts/components/data-table",
    "TableContextMenu.ts",
    "_TableContextMenu.ts",
  ],
  [
    "static/shared/ts/components/data-table",
    "TableFillHandle.ts",
    "_TableFillHandle.ts",
  ],
  [
    "static/shared/ts/components/data-table",
    "TableSelection.ts",
    "_TableSelection.ts",
  ],
  // shared/workspace-files-tree
  [
    "static/shared/ts/components/workspace-files-tree",
    "TreeNavigation.ts",
    "_TreeNavigation.ts",
  ],
  [
    "static/shared/ts/components/workspace-files-tree",
    "HiddenFilesToggle.ts",
    "_HiddenFilesToggle.ts",
  ],
  [
    "static/shared/ts/components/workspace-files-tree",
    "ZenPanelManager.ts",
    "_ZenPanelManager.ts",
  ],
  // shared/media-editor + monaco-editor
  ["static/shared/ts/components/media-editor", "CsvEditor.ts", "_CsvEditor.ts"],
  [
    "static/shared/ts/components/monaco-editor",
    "SharedMonacoEditor.ts",
    "_SharedMonacoEditor.ts",
  ],
  // shared/seekbar
  ["static/shared/ts/components/seekbar", "dom-builder.ts", "_dom-builder.ts"],
  [
    "static/shared/ts/components/seekbar",
    "event-handlers.ts",
    "_event-handlers.ts",
  ],
  [
    "static/shared/ts/components/seekbar",
    "value-calculator.ts",
    "_value-calculator.ts",
  ],
  ["static/shared/ts/components/seekbar", "renderer.ts", "_renderer.ts"],
  // shared/media-viewer
  [
    "static/shared/ts/components/media-viewer",
    "ImageViewer.ts",
    "_ImageViewer.ts",
  ],
  [
    "static/shared/ts/components/media-viewer",
    "BinaryPlaceholder.ts",
    "_BinaryPlaceholder.ts",
  ],
  ["static/shared/ts/components/media-viewer", "PdfViewer.ts", "_PdfViewer.ts"],
  // shared/file-tabs
  [
    "static/shared/ts/components/file-tabs",
    "FileTabManager.ts",
    "_FileTabManager.ts",
  ],
  // writer_app individual files
  ["apps/writer_app/static/writer_app/ts", "helpers.ts", "_helpers.ts"],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "sections.ts",
    "_sections.ts",
  ],
  ["apps/writer_app/static/writer_app/ts/modules", "editor.ts", "_editor.ts"],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "spell-checker.ts",
    "_spell-checker.ts",
  ],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "spell-checker_backup.ts",
    "_spell-checker_backup.ts",
  ],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "writer-file-filter.ts",
    "_writer-file-filter.ts",
  ],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "latex-wrapper.ts",
    "_latex-wrapper.ts",
  ],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "theme-manager.ts",
    "_theme-manager.ts",
  ],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "git-history.ts",
    "_git-history.ts",
  ],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "state-persistence.ts",
    "_state-persistence.ts",
  ],
  [
    "apps/writer_app/static/writer_app/ts/modules",
    "drag-drop.ts",
    "_drag-drop.ts",
  ],
  // writer_app editor internals
  [
    "apps/writer_app/static/writer_app/ts/editor",
    "ot-client.ts",
    "_ot-client.ts",
  ],
  ["apps/writer_app/static/writer_app/ts/editor", "editor.ts", "_editor.ts"],
  [
    "apps/writer_app/static/writer_app/ts/editor",
    "cursor-tracker.ts",
    "_cursor-tracker.ts",
  ],
  [
    "apps/writer_app/static/writer_app/ts/editor",
    "presence-display.ts",
    "_presence-display.ts",
  ],
  [
    "apps/writer_app/static/writer_app/ts/editor/preview-panel",
    "rendering.ts",
    "_rendering.ts",
  ],
  [
    "apps/writer_app/static/writer_app/ts/editor/preview-panel",
    "sync.ts",
    "_sync.ts",
  ],
  [
    "apps/writer_app/static/writer_app/ts/editor/preview-panel",
    "navigation.ts",
    "_navigation.ts",
  ],
  // writer_app utils
  [
    "apps/writer_app/static/writer_app/ts/utils",
    "dom.utils.ts",
    "_dom.utils.ts",
  ],
  [
    "apps/writer_app/static/writer_app/ts/utils",
    "keyboard.utils.ts",
    "_keyboard.utils.ts",
  ],
  [
    "apps/writer_app/static/writer_app/ts/utils",
    "timer.utils.ts",
    "_timer.utils.ts",
  ],
  // public_app view-plot
  [
    "apps/public_app/static/public_app/ts/tools/view-plot",
    "PlotViewer.ts",
    "_PlotViewer.ts",
  ],
  [
    "apps/public_app/static/public_app/ts/tools/view-plot",
    "renderers.ts",
    "_renderers.ts",
  ],
  [
    "apps/public_app/static/public_app/ts/tools/view-plot",
    "utils.ts",
    "_utils.ts",
  ],
  [
    "apps/public_app/static/public_app/ts/tools/view-plot",
    "data.ts",
    "_data.ts",
  ],
  [
    "apps/public_app/static/public_app/ts/tools/view-plot",
    "controls.ts",
    "_controls.ts",
  ],
  [
    "apps/public_app/static/public_app/ts/tools/view-plot",
    "export.ts",
    "_export.ts",
  ],
  [
    "apps/public_app/static/public_app/ts/tools/view-plot",
    "plot-drawers.ts",
    "_plot-drawers.ts",
  ],
  // console_app root-level internals
  [
    "apps/console_app/static/console_app/ts",
    "ansi-colors.ts",
    "_ansi-colors.ts",
  ],
  [
    "apps/console_app/static/console_app/ts",
    "file-tree-builder.ts",
    "_file-tree-builder.ts",
  ],
  [
    "apps/console_app/static/console_app/ts",
    "path-linker.ts",
    "_path-linker.ts",
  ],
  [
    "apps/console_app/static/console_app/ts",
    "pty-input-handlers.ts",
    "_pty-input-handlers.ts",
  ],
  [
    "apps/console_app/static/console_app/ts",
    "pty-terminal.ts",
    "_pty-terminal.ts",
  ],
];

/** All TS source directories to scan for import updates */
export const TS_SEARCH_DIRS = [
  "static/shared/ts",
  "static/workspace_app/ts",
  "apps/console_app/static/console_app/ts",
  "apps/vis_app/static/vis_app/ts",
  "apps/writer_app/static/writer_app/ts",
  "apps/project_app/static/project_app/ts",
  "apps/scholar_app/static/scholar_app/ts",
  "apps/public_app/static/public_app/ts",
  "apps/accounts_app/static/accounts_app/ts",
  "apps/hub_app/static/hub_app/ts",
  "apps/clew_app/static/clew_app/ts",
  "apps/social_app/static/social_app/ts",
  "apps/docs_app/static/docs_app/ts",
];
