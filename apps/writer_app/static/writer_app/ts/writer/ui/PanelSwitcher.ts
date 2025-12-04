/**
 * Panel Switcher Module
 * Handles switching between PDF, Citations, Figures, Tables, History, and Collaboration panels
 * Includes lazy CSS loading for better performance
 */

import { statePersistence } from "../../modules/state-persistence.js";
import { initializeCollaboratorsPanel } from "../../collaboration-panel.js";

export class PanelSwitcher {
  private loadedCSS: Set<string> = new Set();
  private validPanels = ['pdf', 'citations', 'figures', 'tables', 'history', 'collaboration'];

  constructor() {
    // Track loaded CSS to avoid duplicates
    if (!(window as any).loadedPanelCSS) {
      (window as any).loadedPanelCSS = this.loadedCSS;
    } else {
      this.loadedCSS = (window as any).loadedPanelCSS;
    }

    // Setup hash change listener
    this.setupHashChangeListener();

    // Handle initial hash on page load
    this.handleInitialHash();
  }

  /**
   * Setup hash change event listener for URL-based panel navigation
   */
  private setupHashChangeListener(): void {
    window.addEventListener('hashchange', () => {
      const panel = this.getPanelFromHash();
      if (panel) {
        console.log('[PanelSwitcher] Hash changed, switching to:', panel);
        this.switchPanel(panel as any);
      }
    });
  }

  /**
   * Handle initial hash on page load
   */
  private handleInitialHash(): void {
    // Defer to allow DOM to be ready
    setTimeout(() => {
      const panel = this.getPanelFromHash();
      if (panel) {
        console.log('[PanelSwitcher] Initial hash detected, switching to:', panel);
        this.switchPanel(panel as any);
      }
    }, 100);
  }

  /**
   * Get panel name from URL hash
   */
  private getPanelFromHash(): string | null {
    const hash = window.location.hash.slice(1); // Remove #
    if (hash && this.validPanels.includes(hash)) {
      return hash;
    }
    return null;
  }

  /**
   * Update URL hash to reflect current panel
   */
  private updateUrlHash(panel: string): void {
    // Only update if it's a valid panel and different from current
    if (this.validPanels.includes(panel)) {
      const currentHash = window.location.hash.slice(1);
      if (currentHash !== panel) {
        // Use replaceState to avoid adding to browser history for every switch
        const url = new URL(window.location.href);
        url.hash = panel;
        history.replaceState(null, '', url.toString());
        console.log('[PanelSwitcher] URL hash updated to:', panel);
      }
    }
  }

  /**
   * Lazy load CSS for a specific panel
   * Returns a promise that resolves when CSS is loaded or immediately if already loaded
   */
  private loadPanelCSS(panel: string): Promise<void> {
    return new Promise((resolve) => {
      // If already loaded in this session, resolve immediately
      if (this.loadedCSS.has(panel)) {
        console.log(
          `[PanelSwitcher] CSS for ${panel} panel already loaded, skipping`,
        );
        resolve();
        return;
      }

      const cssFiles: Record<string, string> = {
        citations: "/static/writer_app/css/editor/citations-panel/index.css",
        figures: "/static/writer_app/css/editor/figures-panel/index.css",
        tables: "/static/writer_app/css/editor/tables-panel.css",
        collaboration: "/static/shared/css/collaboration/collaboration.css",
        history: "/static/writer_app/css/shared/history-timeline.css",
      };

      const cssUrl = cssFiles[panel];
      if (!cssUrl) {
        console.warn(`[PanelSwitcher] No CSS file defined for ${panel} panel`);
        resolve();
        return;
      }

      // Check if link with exact href already exists (from previous page loads)
      const exactMatchSelector = `link[href^="${cssUrl}"]`;
      const existingLink = document.querySelector(exactMatchSelector);
      if (existingLink) {
        console.log(
          `[PanelSwitcher] CSS link for ${panel} panel already exists in DOM, marking as loaded`,
        );
        this.loadedCSS.add(panel);
        resolve();
        return;
      }

      // Create and append link element
      console.log(`[PanelSwitcher] Loading CSS for ${panel} panel: ${cssUrl}`);
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = `${cssUrl}?v=${Date.now()}`;
      link.setAttribute("data-panel", panel);

      link.onload = () => {
        this.loadedCSS.add(panel);
        console.log(
          `[PanelSwitcher] ✓ Successfully loaded CSS for ${panel} panel`,
        );
        resolve();
      };

      link.onerror = (error) => {
        console.error(
          `[PanelSwitcher] ✗ Failed to load CSS for ${panel} panel:`,
          error,
        );
        console.error(`[PanelSwitcher] Attempted URL: ${cssUrl}`);
        // Still resolve to not block panel display
        resolve();
      };

      document.head.appendChild(link);
    });
  }

  /**
   * Switch right panel between PDF, Citations, Figures, Tables, History, and Collaboration views
   */
  switchPanel(
    view: "pdf" | "citations" | "figures" | "tables" | "history" | "collaboration",
  ): void {
    // Update URL hash to reflect current panel
    this.updateUrlHash(view);

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
    const collaborationHeader = document.getElementById(
      "collaboration-panel-header",
    );

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
    const previewPanel = document.querySelector(
      ".preview-panel",
    ) as HTMLElement;

    if (
      !pdfView ||
      !citationsView ||
      !figuresView ||
      !tablesView ||
      !historyView
    ) {
      console.error("[PanelSwitcher] Panel toggle elements not found");
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
      previewPanel.classList.remove(
        "showing-pdf",
        "showing-citations",
        "showing-figures",
        "showing-tables",
        "showing-history",
        "showing-collaboration",
      );
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
        console.log(
          `[PanelSwitcher] Updated shared header for ${view} view`,
        );

        // Update active state on buttons in the SHARED header (after innerHTML copy)
        const sharedHeaderBtns =
          sharedHeader.querySelectorAll(".view-switch-btn");
        sharedHeaderBtns.forEach((btn) => {
          const btnElement = btn as HTMLElement;
          // Check which panel this button switches to
          const onclickAttr = btnElement.getAttribute("onclick");
          if (onclickAttr) {
            // Add active class if this button matches the current view
            if (onclickAttr.includes(`'${view}'`)) {
              btnElement.classList.add("active");
            } else {
              btnElement.classList.remove("active");
            }
          }
        });
        console.log(
          `[PanelSwitcher] Updated active button state in shared header for ${view} view`,
        );
      }
    }

    // Show selected view and update states - use hidden attribute, let CSS handle display
    if (view === "citations") {
      this.loadPanelCSS("citations").then(() => {
        citationsView.removeAttribute("hidden");
        if (previewPanel) {
          previewPanel.classList.add("showing-citations");
        }
        allCitationsBtns.forEach((btn) => btn.classList.add("active"));
        statePersistence.saveActivePane("citations");
        console.log("[PanelSwitcher] Switched to Citations view");

        // Load citations if not already loaded
        const citationsPanel = (window as any).citationsPanel;
        if (
          citationsPanel &&
          typeof citationsPanel.loadCitations === "function"
        ) {
          citationsPanel.loadCitations();
        }
      });
    } else if (view === "figures") {
      this.loadPanelCSS("figures").then(() => {
        figuresView.removeAttribute("hidden");
        if (previewPanel) {
          previewPanel.classList.add("showing-figures");
        }
        allFiguresBtns.forEach((btn) => btn.classList.add("active"));
        statePersistence.saveActivePane("figures");
        console.log("[PanelSwitcher] Switched to Figures view");

        // Load figures if not already loaded
        const figuresPanel = (window as any).figuresPanel;
        if (figuresPanel && typeof figuresPanel.loadFigures === "function") {
          figuresPanel.loadFigures();
        }
      });
    } else if (view === "tables") {
      this.loadPanelCSS("tables").then(() => {
        tablesView.removeAttribute("hidden");
        if (previewPanel) {
          previewPanel.classList.add("showing-tables");
        }
        allTablesBtns.forEach((btn) => btn.classList.add("active"));
        statePersistence.saveActivePane("tables");
        console.log("[PanelSwitcher] Switched to Tables view");

        // Load tables if not already loaded
        const tablesPanel = (window as any).tablesPanel;
        if (tablesPanel && typeof tablesPanel.loadTables === "function") {
          tablesPanel.loadTables();
        }
      });
    } else if (view === "history") {
      this.loadPanelCSS("history").then(() => {
        historyView.removeAttribute("hidden");
        if (previewPanel) {
          previewPanel.classList.add("showing-history");
        }
        allHistoryBtns.forEach((btn) => btn.classList.add("active"));
        statePersistence.saveActivePane("history");
        console.log("[PanelSwitcher] Switched to History view");

        // Initialize and load Git history
        const initGitHistoryManager = (window as any).initGitHistoryManager;
        if (initGitHistoryManager) {
          const gitHistoryManager = initGitHistoryManager();
          if (
            gitHistoryManager &&
            typeof gitHistoryManager.loadHistory === "function"
          ) {
            gitHistoryManager.loadBranches();
            gitHistoryManager.loadStatus();
            gitHistoryManager.loadHistory();
          }
        } else {
          console.error(
            "[PanelSwitcher] initGitHistoryManager function not found",
          );
        }
      });
    } else if (view === "collaboration") {
      this.loadPanelCSS("collaboration").then(() => {
        if (collaborationView) {
          collaborationView.removeAttribute("hidden");
          if (previewPanel) {
            previewPanel.classList.add("showing-collaboration");
          }
          allCollaborationBtns.forEach((btn) => btn.classList.add("active"));
          statePersistence.saveActivePane("collaboration");
          console.log("[PanelSwitcher] Switched to Collaboration view");

          // Initialize the collaborators panel
          initializeCollaboratorsPanel();
        } else {
          console.warn("[PanelSwitcher] Collaboration view not found");
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
      console.log("[PanelSwitcher] Switched to PDF view");
    }

    // Legacy save (keeping for backward compatibility)
    localStorage.setItem("writer_right_panel_view", view);
  }

  /**
   * Automatically switch panel based on section name
   * Determines the most appropriate panel (PDF, Figures, or Tables) for a given section
   */
  autoSwitchForSection(section: string | null, doctype: string = 'manuscript'): void {
    if (!section) {
      // Default to PDF if no section
      this.switchPanel('pdf');
      return;
    }

    const sectionLower = section.toLowerCase();

    // Check if this is a figures section
    if (sectionLower.includes('figure') || sectionLower === 'figures') {
      console.log(`[PanelSwitcher] Auto-switching to Figures panel for section: ${section}`);
      this.switchPanel('figures');
      return;
    }

    // Check if this is a tables section
    if (sectionLower.includes('table') || sectionLower === 'tables') {
      console.log(`[PanelSwitcher] Auto-switching to Tables panel for section: ${section}`);
      this.switchPanel('tables');
      return;
    }

    // For supplementary material, prefer figures/tables if mentioned
    if (doctype === 'supplementary') {
      // Check content type from section name
      if (sectionLower.includes('result') || sectionLower.includes('method')) {
        this.switchPanel('figures');
        return;
      }
    }

    // Default to PDF for text sections (abstract, introduction, methods, results, discussion, etc.)
    console.log(`[PanelSwitcher] Auto-switching to PDF panel for section: ${section}`);
    this.switchPanel('pdf');
  }
}
