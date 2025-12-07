/**
 * Panel Toggle Functionality for Writer
 * Handles the four-panel (sidebar, editor, preview, details) expand/collapse behavior
 * Similar to Scholar's panel-toggle.ts pattern
 */

console.log(
  "[DEBUG] apps/writer_app/static/writer_app/ts/writer/ui/panel-toggle.ts loaded"
);

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
 * Toggle panel expansion/collapse
 * For sidebar and details: simple toggle collapsed state
 * For editor and preview: three-state system (normal, expanded, collapsed)
 */
export function togglePanel(panelType: PanelType): void {
  const sidebar = document.getElementById("writer-sidebar");
  const sidebarResizer = document.getElementById("sidebar-resizer");
  const details = document.getElementById("writer-details");
  const detailsResizer = document.getElementById("details-resizer");
  const editorPanel = document.querySelector(".latex-panel") as HTMLElement;
  const previewPanel = document.querySelector(".preview-panel") as HTMLElement;
  const panelResizer = document.getElementById("panel-resizer");

  if (panelType === "sidebar") {
    if (!sidebar) {
      console.warn("[Panel Toggle] Sidebar not found");
      return;
    }

    // Toggle sidebar collapsed state
    if (sidebar.classList.contains("collapsed")) {
      // Expand sidebar
      sidebar.classList.remove("collapsed");
      if (sidebarResizer) sidebarResizer.style.display = "";
      saveState({ sidebarCollapsed: false });
      console.log("[Panel Toggle] Sidebar expanded");
    } else {
      // Collapse sidebar
      sidebar.classList.add("collapsed");
      if (sidebarResizer) sidebarResizer.style.display = "none";
      saveState({ sidebarCollapsed: true });
      console.log("[Panel Toggle] Sidebar collapsed");
    }
    updateToggleButtonIcons();
    return;
  }

  if (panelType === "details") {
    if (!details) {
      console.warn("[Panel Toggle] Details panel not found");
      return;
    }

    // Toggle details collapsed state
    if (details.classList.contains("collapsed")) {
      // Expand details
      details.classList.remove("collapsed");
      if (detailsResizer) detailsResizer.style.display = "";
      saveState({ detailsCollapsed: false });
      console.log("[Panel Toggle] Details expanded");
    } else {
      // Collapse details
      details.classList.add("collapsed");
      if (detailsResizer) detailsResizer.style.display = "none";
      saveState({ detailsCollapsed: true });
      console.log("[Panel Toggle] Details collapsed");
    }
    updateToggleButtonIcons();
    return;
  }

  if (!editorPanel || !previewPanel) {
    console.warn("[Panel Toggle] Editor or preview panel not found");
    return;
  }

  if (panelType === "editor") {
    // If editor is collapsed, expand it
    if (editorPanel.classList.contains("collapsed")) {
      editorPanel.classList.remove("collapsed");
      editorPanel.classList.add("expanded");
      previewPanel.classList.remove("expanded");
      previewPanel.classList.add("collapsed");
      saveState({ editorExpanded: true, previewExpanded: false });
    }
    // If editor is already expanded, return to normal
    else if (editorPanel.classList.contains("expanded")) {
      editorPanel.classList.remove("expanded");
      previewPanel.classList.remove("collapsed");
      saveState({ editorExpanded: false, previewExpanded: false });
    }
    // If editor is normal, expand it
    else {
      editorPanel.classList.add("expanded");
      previewPanel.classList.add("collapsed");
      saveState({ editorExpanded: true, previewExpanded: false });
    }
  } else if (panelType === "preview") {
    // If preview is collapsed, expand it
    if (previewPanel.classList.contains("collapsed")) {
      previewPanel.classList.remove("collapsed");
      previewPanel.classList.add("expanded");
      editorPanel.classList.remove("expanded");
      editorPanel.classList.add("collapsed");
      saveState({ previewExpanded: true, editorExpanded: false });
    }
    // If preview is already expanded, return to normal
    else if (previewPanel.classList.contains("expanded")) {
      previewPanel.classList.remove("expanded");
      editorPanel.classList.remove("collapsed");
      saveState({ previewExpanded: false, editorExpanded: false });
    }
    // If preview is normal, expand it
    else {
      previewPanel.classList.add("expanded");
      editorPanel.classList.add("collapsed");
      saveState({ previewExpanded: true, editorExpanded: false });
    }
  }

  // Update resizer visibility
  if (panelResizer) {
    const editorCollapsed = editorPanel.classList.contains("collapsed");
    const previewCollapsed = previewPanel.classList.contains("collapsed");
    // Hide resizer when one panel is fully collapsed
    panelResizer.style.display = editorCollapsed || previewCollapsed ? "none" : "";
  }

  updateToggleButtonIcons();
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
  const sidebarToggle = document.getElementById("sidebar-toggle-btn") || document.getElementById("sidebar-toggle");
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

  // Update editor toggle button
  const editorToggle = document.getElementById("editor-toggle-btn");
  if (editorToggle && editorPanel) {
    const icon = editorToggle.querySelector("i");
    if (icon) {
      if (editorPanel.classList.contains("expanded")) {
        icon.className = "fas fa-compress-alt";
        editorToggle.title = "Restore editor";
      } else if (editorPanel.classList.contains("collapsed")) {
        icon.className = "fas fa-expand-alt";
        editorToggle.title = "Expand editor";
      } else {
        icon.className = "fas fa-expand-alt";
        editorToggle.title = "Maximize editor";
      }
    }
  }

  // Update preview toggle button
  const previewToggle = document.getElementById("preview-toggle-btn");
  if (previewToggle && previewPanel) {
    const icon = previewToggle.querySelector("i");
    if (icon) {
      if (previewPanel.classList.contains("expanded")) {
        icon.className = "fas fa-compress-alt";
        previewToggle.title = "Restore preview";
      } else if (previewPanel.classList.contains("collapsed")) {
        icon.className = "fas fa-expand-alt";
        previewToggle.title = "Expand preview";
      } else {
        icon.className = "fas fa-expand-alt";
        previewToggle.title = "Maximize preview";
      }
    }
  }
}

/**
 * Restore panel states from localStorage on page load
 */
export function restorePanelStates(): void {
  const state = getStoredState();
  const sidebar = document.getElementById("writer-sidebar");
  const sidebarResizer = document.getElementById("sidebar-resizer");
  const details = document.getElementById("writer-details");
  const detailsResizer = document.getElementById("details-resizer");
  const editorPanel = document.querySelector(".latex-panel") as HTMLElement;
  const previewPanel = document.querySelector(".preview-panel") as HTMLElement;
  const panelResizer = document.getElementById("panel-resizer");

  // Restore sidebar state
  if (sidebar && state.sidebarCollapsed) {
    sidebar.classList.add("collapsed");
    if (sidebarResizer) sidebarResizer.style.display = "none";
  }

  // Restore details state
  if (details && state.detailsCollapsed) {
    details.classList.add("collapsed");
    if (detailsResizer) detailsResizer.style.display = "none";
  }

  // Restore editor/preview states
  if (editorPanel && previewPanel) {
    if (state.editorExpanded) {
      editorPanel.classList.add("expanded");
      previewPanel.classList.add("collapsed");
      if (panelResizer) panelResizer.style.display = "none";
    } else if (state.previewExpanded) {
      previewPanel.classList.add("expanded");
      editorPanel.classList.add("collapsed");
      if (panelResizer) panelResizer.style.display = "none";
    }
  }

  updateToggleButtonIcons();
  console.log("[Panel Toggle] Panel states restored:", state);
}

/**
 * Initialize panel toggle functionality
 */
export function initPanelToggle(): void {
  console.log("[Panel Toggle] Initializing...");

  // Restore saved states
  restorePanelStates();

  // Set up global function for onclick handlers
  (window as any).toggleWriterPanel = togglePanel;

  // Set up click handlers for toggle buttons
  const sidebarToggle = document.getElementById("sidebar-toggle-btn") || document.getElementById("sidebar-toggle");
  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      togglePanel("sidebar");
    });
  }

  const detailsToggle = document.getElementById("details-toggle");
  if (detailsToggle) {
    detailsToggle.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      togglePanel("details");
    });
  }

  // Set up keyboard shortcuts
  document.addEventListener("keydown", (e: KeyboardEvent) => {
    // Ctrl+\ to toggle sidebar
    if (e.ctrlKey && e.key === "\\") {
      e.preventDefault();
      togglePanel("sidebar");
    }
    // Ctrl+Shift+D to toggle details
    if (e.ctrlKey && e.shiftKey && e.key === "D") {
      e.preventDefault();
      togglePanel("details");
    }
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
