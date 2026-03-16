/**
 * Panel Toggle Functionality for Writer
 * Handles the editor/preview panel expand/collapse behavior
 *
 * NOTE: Sidebar and Details panel toggle is now handled by shared/resizer
 * via data-h-resizer attributes. This module only handles the editor/preview split
 * which uses binary collapse/expand with shared accordion behavior.
 */

// Storage keys for persistence
const STORAGE_KEY_SIDEBAR = "scitex-writer-sidebar-collapsed";
const STORAGE_KEY_DETAILS = "scitex-writer-details-collapsed";
const STORAGE_KEY_EDITOR = "scitex-writer-editor-expanded";
const STORAGE_KEY_PREVIEW = "scitex-writer-preview-expanded";

type PanelType = "sidebar" | "editor" | "preview" | "details";

interface PanelState {
  sidebarCollapsed: boolean;
  detailsCollapsed: boolean;
  editorExpanded: boolean;
  previewExpanded: boolean;
}

/**
 * Get current panel state from localStorage
 */
function getStoredState(): PanelState {
  return {
    sidebarCollapsed: localStorage.getItem(STORAGE_KEY_SIDEBAR) === "true",
    detailsCollapsed: localStorage.getItem(STORAGE_KEY_DETAILS) === "true",
    editorExpanded: localStorage.getItem(STORAGE_KEY_EDITOR) === "true",
    previewExpanded: localStorage.getItem(STORAGE_KEY_PREVIEW) === "true",
  };
}

/**
 * Save panel state to localStorage
 */
function saveState(state: Partial<PanelState>): void {
  if (state.sidebarCollapsed !== undefined) {
    localStorage.setItem(STORAGE_KEY_SIDEBAR, String(state.sidebarCollapsed));
  }
  if (state.detailsCollapsed !== undefined) {
    localStorage.setItem(STORAGE_KEY_DETAILS, String(state.detailsCollapsed));
  }
  if (state.editorExpanded !== undefined) {
    localStorage.setItem(STORAGE_KEY_EDITOR, String(state.editorExpanded));
  }
  if (state.previewExpanded !== undefined) {
    localStorage.setItem(STORAGE_KEY_PREVIEW, String(state.previewExpanded));
  }
}

/**
 * Clear inline width/flex styles from a panel so CSS classes take effect.
 * The PanelResizer sets inline styles (width, flexShrink, flexGrow) that
 * override CSS .collapsed/.expanded rules — clearing them lets flex layout work.
 */
function clearInlineStyles(panel: HTMLElement): void {
  panel.style.width = "";
  panel.style.flex = "";
  panel.style.flexShrink = "";
  panel.style.flexGrow = "";
}

/**
 * Toggle panel expansion/collapse
 * For sidebar and details: simple toggle collapsed state
 * For editor and preview: binary collapse/expand (shared accordion behavior)
 */
export function togglePanel(panelType: PanelType): void {
  const editorPanel = document.querySelector(".latex-panel") as HTMLElement;
  const previewPanel = document.querySelector(".preview-panel") as HTMLElement;
  const panelResizer = document.getElementById("writer-editor-resizer");

  // NOTE: Sidebar and Details toggle is handled by shared/workspace-panel-resizer.ts
  // This function only handles editor/preview toggle for the unique three-state behavior
  if (panelType === "sidebar" || panelType === "details") {
    console.log(
      `[Panel Toggle] ${panelType} is now handled by WorkspacePanelResizer`,
    );
    return;
  }

  if (!editorPanel || !previewPanel) {
    console.warn("[Panel Toggle] Editor or preview panel not found");
    return;
  }

  // Simple binary toggle: collapse this panel / expand it back
  const targetPanel = panelType === "editor" ? editorPanel : previewPanel;
  const otherPanel = panelType === "editor" ? previewPanel : editorPanel;
  const wasCollapsed = targetPanel.classList.contains("collapsed");

  console.log(
    `[Panel Toggle] ${panelType}: wasCollapsed=${wasCollapsed}, editor.classes=[${editorPanel.className}], preview.classes=[${previewPanel.className}]`,
  );

  if (wasCollapsed) {
    // Expand: return both panels to normal
    targetPanel.classList.remove("collapsed");
    otherPanel.classList.remove("expanded");
    // Clear inline styles so CSS flex defaults take over
    clearInlineStyles(targetPanel);
    clearInlineStyles(otherPanel);
    saveState({ editorExpanded: false, previewExpanded: false });
    console.log(`[Panel Toggle] ${panelType}: expanded → normal state`);
  } else {
    // Collapse this panel, expand the other
    targetPanel.classList.add("collapsed");
    targetPanel.classList.remove("expanded");
    otherPanel.classList.add("expanded");
    otherPanel.classList.remove("collapsed");
    // Clear inline styles so CSS .collapsed/.expanded classes take effect
    clearInlineStyles(targetPanel);
    clearInlineStyles(otherPanel);
    saveState({
      editorExpanded: panelType === "preview",
      previewExpanded: panelType === "editor",
    });
    console.log(`[Panel Toggle] ${panelType}: collapsed, other expanded`);
  }

  // Update resizer visibility
  if (panelResizer) {
    const editorCollapsed = editorPanel.classList.contains("collapsed");
    const previewCollapsed = previewPanel.classList.contains("collapsed");
    // Hide resizer when one panel is fully collapsed
    panelResizer.style.display =
      editorCollapsed || previewCollapsed ? "none" : "";
  }

  updateToggleButtonIcons();

  // Re-fit PDF after CSS transition completes (0.3s transition on flex)
  setTimeout(() => {
    const pdfViewer = (window as any).pdfViewerInstance;
    if (pdfViewer && typeof pdfViewer.fitWidth === "function") {
      pdfViewer.fitWidth();
      console.log("[Panel Toggle] PDF re-fitted to new panel width");
    }
    window.dispatchEvent(new Event("resize"));
  }, 350);

  console.log(`[Panel Toggle] ${panelType} panel toggled`);
}

/**
 * Update toggle button icons based on current panel states
 */
function updateToggleButtonIcons(): void {
  const sidebar = document.getElementById("writer-sidebar");
  const details = document.getElementById("writer-details");
  const editorPanel = document.querySelector(".latex-panel") as HTMLElement;
  const previewPanel = document.querySelector(".preview-panel") as HTMLElement;

  // Update sidebar toggle button (try both IDs for compatibility)
  const sidebarToggle =
    document.getElementById("stx-shell-sidebar__toggle-btn") ||
    document.getElementById("stx-shell-sidebar__toggle");
  if (sidebarToggle && sidebar) {
    const icon = sidebarToggle.querySelector("i");
    if (icon) {
      if (sidebar.classList.contains("collapsed")) {
        icon.className = "fas fa-chevron-right";
        sidebarToggle.title = "Expand sidebar";
      } else {
        icon.className = "fas fa-chevron-left";
        sidebarToggle.title = "Collapse sidebar";
      }
    }
  }

  // Update details toggle button
  const detailsToggle = document.getElementById("details-toggle");
  if (detailsToggle && details) {
    const icon = detailsToggle.querySelector("i");
    if (icon) {
      if (details.classList.contains("collapsed")) {
        icon.className = "fas fa-chevron-left";
        detailsToggle.title = "Expand details";
      } else {
        icon.className = "fas fa-chevron-right";
        detailsToggle.title = "Collapse details";
      }
    }
  }

  // Editor toggle: chevron icon is static, only update title
  const editorToggle = document.getElementById("editor-toggle-btn");
  if (editorToggle && editorPanel) {
    editorToggle.title = editorPanel.classList.contains("collapsed")
      ? "Expand editor"
      : "Collapse editor (Ctrl+Shift+E)";
  }

  // Preview toggle: chevron icon is static, only update title
  const previewToggle = document.getElementById("preview-toggle-btn");
  if (previewToggle && previewPanel) {
    previewToggle.title = previewPanel.classList.contains("collapsed")
      ? "Expand preview"
      : "Collapse preview (Ctrl+Shift+P)";
  }
}

/**
 * Restore panel states from localStorage on page load
 * NOTE: Only restores editor/preview states. Sidebar/details are restored by WorkspacePanelResizer.
 */
export function restorePanelStates(): void {
  const state = getStoredState();
  const editorPanel = document.querySelector(".latex-panel") as HTMLElement;
  const previewPanel = document.querySelector(".preview-panel") as HTMLElement;
  const panelResizer = document.getElementById("writer-editor-resizer");

  // NOTE: Sidebar and details state restoration is handled by WorkspacePanelResizer

  // Restore editor/preview states only
  if (editorPanel && previewPanel) {
    if (state.editorExpanded) {
      editorPanel.classList.add("expanded");
      previewPanel.classList.add("collapsed");
      clearInlineStyles(editorPanel);
      clearInlineStyles(previewPanel);
      if (panelResizer) panelResizer.style.display = "none";
    } else if (state.previewExpanded) {
      previewPanel.classList.add("expanded");
      editorPanel.classList.add("collapsed");
      clearInlineStyles(editorPanel);
      clearInlineStyles(previewPanel);
      if (panelResizer) panelResizer.style.display = "none";
    }
  }

  updateToggleButtonIcons();
  console.log("[Panel Toggle] Editor/preview states restored:", state);
}

/**
 * Initialize panel toggle functionality
 * NOTE: Only handles editor/preview toggle. Sidebar/details handled by WorkspacePanelResizer.
 */
export function initPanelToggle(): void {
  console.log("[Panel Toggle] Initializing (editor/preview only)...");

  // Restore saved states (only for editor/preview, not sidebar/details)
  restorePanelStates();

  // Set up global function for onclick handlers
  (window as any).toggleWriterPanel = togglePanel;

  // NOTE: Sidebar and details toggle click handlers are now set up by
  // shared/workspace-panel-resizer.ts via data-toggle-btn attributes

  // Click/double-click on panel headers to collapse/expand
  const editorPanelEl = document.querySelector(".latex-panel") as HTMLElement;
  const previewPanelEl = document.querySelector(
    ".preview-panel",
  ) as HTMLElement;
  const editorHeader = editorPanelEl?.querySelector(
    ".panel-header",
  ) as HTMLElement;
  const previewHeader = previewPanelEl?.querySelector(
    ".panel-header",
  ) as HTMLElement;

  // Double-click on header to collapse when expanded
  if (editorHeader)
    editorHeader.addEventListener("dblclick", () => togglePanel("editor"));
  if (previewHeader)
    previewHeader.addEventListener("dblclick", () => togglePanel("preview"));

  // Single-click on collapsed strip to expand (toggle button is hidden via CSS)
  if (editorPanelEl) {
    editorPanelEl.addEventListener("click", () => {
      if (editorPanelEl.classList.contains("collapsed")) {
        togglePanel("editor");
      }
    });
  }
  if (previewPanelEl) {
    previewPanelEl.addEventListener("click", () => {
      if (previewPanelEl.classList.contains("collapsed")) {
        togglePanel("preview");
      }
    });
  }

  // Set up keyboard shortcuts for editor/preview only
  document.addEventListener("keydown", (e: KeyboardEvent) => {
    // Ctrl+Shift+E to toggle editor expand
    if (e.ctrlKey && e.shiftKey && e.key === "E") {
      e.preventDefault();
      togglePanel("editor");
    }
    // Ctrl+Shift+P to toggle preview expand
    if (e.ctrlKey && e.shiftKey && e.key === "P") {
      e.preventDefault();
      togglePanel("preview");
    }
  });

  console.log("[Panel Toggle] Initialized");
}

// Make functions available globally
(window as any).toggleWriterPanel = togglePanel;
(window as any).initWriterPanelToggle = initPanelToggle;

// Auto-initialize ONLY on writer pages (check for writer-specific elements)
// This prevents conflict with WorkspacePanelResizer on other pages like scholar
function shouldAutoInit(): boolean {
  // Only init on writer pages - check for writer-specific sidebar
  const writerSidebar = document.getElementById("writer-sidebar");
  const writerWorkspace = document.querySelector(".writer-workspace");
  return !!(writerSidebar || writerWorkspace);
}

if (shouldAutoInit()) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPanelToggle);
  } else {
    initPanelToggle();
  }
}
