/**
 * Panel Management Utilities
 *
 * This module handles UI panel and sidebar management including:
 * - Sidebar button setup and event listeners
 * - PDF zoom control setup
 * - Panel switching logic (PDF, Citations, Figures, Tables, History, Collaboration)
 * - Lazy CSS loading for panels
 * - Panel state persistence
 *
 * These functions coordinate the right panel UI and provide smooth transitions
 * between different views with lazy resource loading.
 */

import { statePersistence } from "../modules/state-persistence.js";
import { initializeCollaboratorsPanel } from "../collaboration-panel.js";

/**
 * Setup sidebar button listeners
 */
export function setupSidebarButtons(_config: any): void {
  // Button listeners are set up in their respective initialization functions
  // No additional setup needed here
}

/**
 * Setup PDF zoom control buttons
 */
export function setupPDFZoomControls(pdfScrollZoomHandler: any): void {
  const zoomInBtn = document.getElementById("pdf-zoom-in-btn");
  const zoomOutBtn = document.getElementById("pdf-zoom-out-btn");
  const fitWidthBtn = document.getElementById("pdf-fit-width-btn");
  const resetZoomBtn = document.getElementById("pdf-reset-zoom-btn");
  const colorModeBtn = document.getElementById("pdf-color-mode-btn");
  const zoomControls = document.querySelector(
    ".pdf-zoom-controls",
  ) as HTMLElement | null;

  if (zoomInBtn) {
    zoomInBtn.addEventListener("click", () => {
      pdfScrollZoomHandler.zoomIn();
    });
  }

  if (zoomOutBtn) {
    zoomOutBtn.addEventListener("click", () => {
      pdfScrollZoomHandler.zoomOut();
    });
  }

  if (fitWidthBtn) {
    fitWidthBtn.addEventListener("click", () => {
      pdfScrollZoomHandler.fitToWidth();
    });
  }

  if (resetZoomBtn) {
    resetZoomBtn.addEventListener("click", () => {
      pdfScrollZoomHandler.resetZoom();
    });
  }

  // Note: colorModeBtn listener already attached earlier in initialization

  // Show/hide zoom controls based on PDF presence
  const observer = new MutationObserver(() => {
    const hasPDF = document.querySelector(".pdf-preview-container") !== null;
    if (zoomControls) {
      zoomControls.style.display = hasPDF ? "flex" : "none";
    }
  });

  const previewPanel = document.querySelector(".preview-panel");
  if (previewPanel) {
    observer.observe(previewPanel, { childList: true, subtree: true });
  }

  console.log("[Writer] PDF zoom controls initialized");
}

/**
 * Open PDF in new window
 */
export function openPDF(url: string): void {
  const pdfWindow = window.open(url, "_blank");
  if (!pdfWindow) {
    const showToast =
      (window as any).showToast || ((msg: string) => console.warn(msg));
    showToast("Failed to open PDF. Please check popup blocker settings.");
  }
}

/**
 * Lazy load CSS for a specific panel
 * Returns a promise that resolves when CSS is loaded or immediately if already loaded
 */
export function loadPanelCSS(panel: string): Promise<void> {
  return new Promise((resolve) => {
    // Track loaded CSS to avoid duplicates
    if (!(window as any).loadedPanelCSS) {
      (window as any).loadedPanelCSS = new Set<string>();
    }
    const loadedCSS = (window as any).loadedPanelCSS;

    // If already loaded in this session, resolve immediately
    if (loadedCSS.has(panel)) {
      console.log(`[Writer] CSS for ${panel} panel already loaded, skipping`);
      resolve();
      return;
    }

    const cssFiles: Record<string, string> = {
      "citations": "/static/writer_app/css/editor/citations-panel/index.css",
      "figures": "/static/writer_app/css/editor/figures-panel/index.css",
      "tables": "/static/writer_app/css/editor/tables-panel.css",
      "collaboration": "/static/shared/css/collaboration/collaboration.css",
      "history": "/static/writer_app/css/shared/history-timeline/index.css"
    };

    const cssUrl = cssFiles[panel];
    if (!cssUrl) {
      console.warn(`[Writer] No CSS file defined for ${panel} panel`);
      resolve();
      return;
    }

    // Check if link with exact href already exists (from previous page loads)
    const exactMatchSelector = `link[href^="${cssUrl}"]`;
    const existingLink = document.querySelector(exactMatchSelector);
    if (existingLink) {
      console.log(`[Writer] CSS link for ${panel} panel already exists in DOM, marking as loaded`);
      loadedCSS.add(panel);
      resolve();
      return;
    }

    // Create and append link element
    console.log(`[Writer] Loading CSS for ${panel} panel: ${cssUrl}`);
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = `${cssUrl}?v=${Date.now()}`;
    link.setAttribute('data-panel', panel);

    link.onload = () => {
      loadedCSS.add(panel);
      console.log(`[Writer] ✓ Successfully loaded CSS for ${panel} panel`);
      resolve();
    };

    link.onerror = (error) => {
      console.error(`[Writer] ✗ Failed to load CSS for ${panel} panel:`, error);
      console.error(`[Writer] Attempted URL: ${cssUrl}`);
      // Still resolve to not block panel display
      resolve();
    };

    document.head.appendChild(link);
  });
}

/**
 * Switch right panel between PDF, Citations, Figures, Tables, History, and Collaboration views
 */
export function switchRightPanel(view: "pdf" | "citations" | "figures" | "tables" | "history" | "collaboration"): void {
  const pdfView = document.getElementById("pdf-view");
  const citationsView = document.getElementById("citations-view");
  const figuresView = document.getElementById("figures-view");
  const tablesView = document.getElementById("tables-view");
  const historyView = document.getElementById("history-view");
  const collaborationView = document.getElementById("collaboration-view");

  // Get shared header and template headers
  const sharedHeader = document.getElementById("right-panel-header");
  const pdfHeader = document.getElementById("pdf-panel-header");
  const citationsHeader = document.getElementById("citations-panel-header");
  const figuresHeader = document.getElementById("figures-panel-header");
  const tablesHeader = document.getElementById("tables-panel-header");
  const historyHeader = document.getElementById("history-panel-header");
  const collaborationHeader = document.getElementById("collaboration-panel-header");
  // Get all view switch buttons in all panel headers
  const allPdfBtns = document.querySelectorAll(
    '#show-pdf-btn, .view-switch-btn[onclick*="pdf"]',
  );
  const allCitationsBtns = document.querySelectorAll(
    '#show-citations-btn, .view-switch-btn[onclick*="citations"]',
  );
  const allFiguresBtns = document.querySelectorAll(
    '#show-figures-btn, .view-switch-btn[onclick*="figures"]',
  );
  const allTablesBtns = document.querySelectorAll(
    '#show-tables-btn, .view-switch-btn[onclick*="tables"]',
  );
  const allHistoryBtns = document.querySelectorAll(
    '#show-history-btn, .view-switch-btn[onclick*="history"]',
  );
  const allCollaborationBtns = document.querySelectorAll(
    '#show-collaboration-btn, .view-switch-btn[onclick*="collaboration"]',
  );
  const previewPanel = document.querySelector(".preview-panel") as HTMLElement;

  if (!pdfView || !citationsView || !figuresView || !tablesView || !historyView) {
    console.error("[Writer] Panel toggle elements not found");
    return;
  }

  // Hide all views first - remove display style to let CSS control layout
  pdfView.removeAttribute("style");
  pdfView.setAttribute("hidden", "");
  citationsView.removeAttribute("style");
  citationsView.setAttribute("hidden", "");
  figuresView.removeAttribute("style");
  figuresView.setAttribute("hidden", "");
  tablesView.removeAttribute("style");
  tablesView.setAttribute("hidden", "");
  historyView.removeAttribute("style");
  historyView.setAttribute("hidden", "");
  if (collaborationView) {
    collaborationView.removeAttribute("style");
    collaborationView.setAttribute("hidden", "");
  }

  // Remove all active states
  allPdfBtns.forEach((btn) => btn.classList.remove("active"));
  allCitationsBtns.forEach((btn) => btn.classList.remove("active"));
  allFiguresBtns.forEach((btn) => btn.classList.remove("active"));
  allTablesBtns.forEach((btn) => btn.classList.remove("active"));
  allHistoryBtns.forEach((btn) => btn.classList.remove("active"));
  allCollaborationBtns.forEach((btn) => btn.classList.remove("active"));

  // Remove all preview-panel classes
  if (previewPanel) {
    previewPanel.classList.remove("showing-pdf", "showing-citations", "showing-figures", "showing-tables", "showing-history", "showing-collaboration");
  }

  // Update shared header content based on active view
  if (sharedHeader) {
    let templateHeader: HTMLElement | null = null;
    if (view === "pdf") templateHeader = pdfHeader;
    else if (view === "citations") templateHeader = citationsHeader;
    else if (view === "figures") templateHeader = figuresHeader;
    else if (view === "tables") templateHeader = tablesHeader;
    else if (view === "history") templateHeader = historyHeader;
    else if (view === "collaboration") templateHeader = collaborationHeader;

    if (templateHeader) {
      sharedHeader.innerHTML = templateHeader.innerHTML;
      console.log(`[Writer] Updated shared header for ${view} view`);

      // Update active state on buttons in the SHARED header (after innerHTML copy)
      const sharedHeaderBtns = sharedHeader.querySelectorAll('.view-switch-btn');
      sharedHeaderBtns.forEach((btn) => {
        const btnElement = btn as HTMLElement;
        // Check which panel this button switches to
        const onclickAttr = btnElement.getAttribute('onclick');
        if (onclickAttr) {
          // Add active class if this button matches the current view
          if (onclickAttr.includes(`'${view}'`)) {
            btnElement.classList.add('active');
          } else {
            btnElement.classList.remove('active');
          }
        }
      });
      console.log(`[Writer] Updated active button state in shared header for ${view} view`);
    }
  }

  // Show selected view and update states - use hidden attribute, let CSS handle display
  if (view === "citations") {
    // Lazy load CSS first, then show panel
    loadPanelCSS("citations").then(() => {
      citationsView.removeAttribute("hidden");
      if (previewPanel) {
        previewPanel.classList.add("showing-citations");
      }
      allCitationsBtns.forEach((btn) => btn.classList.add("active"));
      statePersistence.saveActivePane("citations");
      console.log("[Writer] Switched to Citations view");

      // Load citations if not already loaded
      const citationsPanel = (window as any).citationsPanel;
      if (citationsPanel && typeof citationsPanel.loadCitations === "function") {
        citationsPanel.loadCitations();
      }
    });
  } else if (view === "figures") {
    // Lazy load CSS first, then show panel
    loadPanelCSS("figures").then(() => {
      figuresView.removeAttribute("hidden");
      if (previewPanel) {
        previewPanel.classList.add("showing-figures");
      }
      allFiguresBtns.forEach((btn) => btn.classList.add("active"));
      statePersistence.saveActivePane("figures");
      console.log("[Writer] Switched to Figures view");

      // Load figures if not already loaded
      const figuresPanel = (window as any).figuresPanel;
      if (figuresPanel && typeof figuresPanel.loadFigures === "function") {
        figuresPanel.loadFigures();
      }
    });
  } else if (view === "tables") {
    // Lazy load CSS first, then show panel
    loadPanelCSS("tables").then(() => {
      tablesView.removeAttribute("hidden");
      if (previewPanel) {
        previewPanel.classList.add("showing-tables");
      }
      allTablesBtns.forEach((btn) => btn.classList.add("active"));
      statePersistence.saveActivePane("tables");
      console.log("[Writer] Switched to Tables view");

      // Load tables if not already loaded
      const tablesPanel = (window as any).tablesPanel;
      if (tablesPanel && typeof tablesPanel.loadTables === "function") {
        tablesPanel.loadTables();
      }
    });
  } else if (view === "history") {
    // Lazy load CSS first, then show panel
    loadPanelCSS("history").then(() => {
      historyView.removeAttribute("hidden");
      if (previewPanel) {
        previewPanel.classList.add("showing-history");
      }
      allHistoryBtns.forEach((btn) => btn.classList.add("active"));
      statePersistence.saveActivePane("history");
      console.log("[Writer] Switched to History view");

      // Initialize and load Git history
      const initGitHistoryManager = (window as any).initGitHistoryManager;
      if (initGitHistoryManager) {
        const gitHistoryManager = initGitHistoryManager();
        if (gitHistoryManager && typeof gitHistoryManager.loadHistory === "function") {
          gitHistoryManager.loadBranches();
          gitHistoryManager.loadStatus();
          gitHistoryManager.loadHistory();
        }
      } else {
        console.error("[Writer] initGitHistoryManager function not found");
      }
    });
  } else if (view === "collaboration") {
    // Lazy load CSS first, then show panel
    loadPanelCSS("collaboration").then(() => {
      if (collaborationView) {
        collaborationView.removeAttribute("hidden");
        if (previewPanel) {
          previewPanel.classList.add("showing-collaboration");
        }
        allCollaborationBtns.forEach((btn) => btn.classList.add("active"));
        statePersistence.saveActivePane("collaboration");
        console.log("[Writer] Switched to Collaboration view");

        // Initialize the collaborators panel
        initializeCollaboratorsPanel();
      } else {
        console.warn("[Writer] Collaboration view not found");
      }
    });
  } else {
    // Default to PDF view - remove hidden attribute, let CSS handle display: flex
    pdfView.removeAttribute("hidden");
    if (previewPanel) {
      previewPanel.classList.add("showing-pdf");
    }
    allPdfBtns.forEach((btn) => btn.classList.add("active"));
    statePersistence.saveActivePane("pdf");
    console.log("[Writer] Switched to PDF view");
  }

  // Legacy save (keeping for backward compatibility)
  localStorage.setItem("writer_right_panel_view", view);
}
