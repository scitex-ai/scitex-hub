/**
 * Vis Editor Module Index
 *
 * Re-exports all modules for easy importing
 */

export { VisEditor } from "./VisEditor";
export { setupLayoutAlgorithms } from "./layout";
export type { LayoutOptions, LayoutAlgorithms } from "./layout";
export { setupInteractionHandlers } from "./interactions";
export type { InteractionHandlers } from "./interactions";
export { setupExportFunctionality } from "./export";
export type { ExportOptions, ExportFunctionality } from "./export";

/**
 * Initialize VisEditor when DOM is ready
 */
export function initializeVisEditor(): void {
  document.addEventListener("DOMContentLoaded", async () => {
    console.log("[VisEditor] DOM loaded, initializing editor...");

    const { VisEditor } = await import("./VisEditor.js");
    const { setupInteractionHandlers } = await import("./interactions.js");

    const editorInstance = new VisEditor();
    const interactionHandlers = setupInteractionHandlers(editorInstance);

    // Setup theme toggle
    interactionHandlers.setupThemeToggle();

    // Setup keyboard shortcuts help modal
    interactionHandlers.setupShortcutsHelp();

    // Setup hit region toggle button (debug visualization)
    interactionHandlers.setupHitRegionToggle();

    // Setup files tree if project context exists
    // Read directly from data attributes to avoid race condition with editor-inline.js
    const editorContainer = document.querySelector(".vis-editor-container");
    const projectOwner =
      editorContainer?.getAttribute("data-project-owner") ||
      (window as any).projectOwner;
    const projectSlug =
      editorContainer?.getAttribute("data-project-slug") ||
      (window as any).projectSlug;
    if (projectOwner && projectSlug) {
      await interactionHandlers.setupFilesTree(projectOwner, projectSlug);

      // Set project context on editor for bundle-based flow
      editorInstance.setProjectContext(projectOwner, projectSlug);

      // Also set project context on canvas manager for auto-save
      const managers = editorInstance.getManagers();
      managers.canvasManager.setBundleProjectContext(projectOwner, projectSlug);

      console.log(
        `[VisEditor] Project context: ${projectOwner}/${projectSlug}`,
      );

      // Inject project context into the global AI panel
      const aiContext = {
        page: "visualizer",
        project: projectSlug,
        project_slug: projectSlug,
      };
      if ((window as any).scitexAI) {
        (window as any).scitexAI.setContext(aiContext);
      }
    }

    // Expose to window for external access
    const managers = editorInstance.getManagers();
    (window as any).visEditor = {
      instance: editorInstance,
      updateCanvasTheme: (isDark: boolean) =>
        editorInstance.updateCanvasTheme(isDark),
      importFile: (file: File) =>
        managers.dataTableManager.handleFileImport(file),
      loadDemoData: () => managers.dataTableManager.loadDemoData(),
      getCurrentData: () => managers.dataTableManager.getCurrentData(),
      getActiveCanvasTab: () => managers.canvasTabManager.getActiveTab(),
      getActiveDataTab: () => managers.dataTabManager.getActiveTab(),
      createCanvasTab: (name?: string) =>
        managers.canvasTabManager.createTab(name),
      createDataTab: (
        name: string,
        type?: any,
        figureName?: string,
        objectName?: string,
      ) =>
        managers.dataTabManager.createTab(name, type, figureName, objectName),
      // Bundle-based flow
      setProjectContext: (owner: string, slug: string, figureName?: string) =>
        editorInstance.setProjectContext(owner, slug, figureName),
      addPanelFromGallery: (plotType: string, dataCsv?: string) =>
        managers.canvasManager.addPanelFromGallery(
          plotType,
          dataCsv,
          projectOwner,
          projectSlug,
        ),
      triggerAutoSave: () =>
        managers.canvasManager.triggerFigzAutoSave(projectOwner, projectSlug),
      // Debug utilities
      plotAllTypes: () => editorInstance.plotAllTypes(),
    };

    // Setup "Plot All" button click handler (dev utility)
    const plotAllBtn = document.getElementById("plot-all-types-btn");
    if (plotAllBtn) {
      plotAllBtn.addEventListener("click", () => {
        console.log("[Dev] Plot All Types button clicked");
        editorInstance.plotAllTypes();
      });
    }

    // Setup export dropdown handlers
    setupExportHandlers(managers.canvasManager);

    // Setup page refresh handlers (beforeunload + periodic save)
    managers.canvasManager.setupBeforeUnloadHandler();

    // Load figure from disk if it exists (figures are always loaded from files, not localStorage)
    await loadFigureFromDiskIfExists(
      managers.canvasManager,
      projectOwner,
      projectSlug,
    );

    // Initialize bundle UI components
    await initializeBundleComponents(editorInstance);

    console.log("[VisEditor] Editor ready");
  });
}

/**
 * Setup export dropdown handlers
 * Wires download dropdown buttons to backend export via scitex package.
 * All exports delegate to scitex.fig.io.export_figz_bundle for proper compositing.
 */
function setupExportHandlers(canvasManager: any): void {
  // PNG (300 DPI) - Uses backend scitex package
  const exportPngBtn = document.getElementById("export-png");
  exportPngBtn?.addEventListener("click", async () => {
    console.log("[Export] PNG (300 DPI) via backend");
    if (canvasManager.exportManager) {
      await canvasManager.exportManager.exportFigureImage("png", 300);
    } else {
      console.error("[Export] ExportManager not initialized");
    }
  });

  // SVG (Vector) - Client-side export (no backend SVG compositing yet)
  const exportSvgBtn = document.getElementById("export-svg");
  exportSvgBtn?.addEventListener("click", () => {
    console.log("[Export] SVG (Vector) - client-side");
    if (canvasManager.exportManager) {
      canvasManager.exportManager.exportAsSvg();
    } else {
      console.error("[Export] ExportManager not initialized");
    }
  });

  // PDF - Uses backend scitex package
  const exportPdfBtn = document.getElementById("export-pdf");
  exportPdfBtn?.addEventListener("click", async () => {
    console.log("[Export] PDF via backend");
    if (canvasManager.exportManager) {
      await canvasManager.exportManager.exportFigureImage("pdf", 300);
    } else {
      console.error("[Export] ExportManager not initialized");
    }
  });

  // JPEG (95%) - Uses backend scitex package
  const exportJpegBtn = document.getElementById("export-jpeg");
  exportJpegBtn?.addEventListener("click", async () => {
    console.log("[Export] JPEG via backend");
    if (canvasManager.exportManager) {
      await canvasManager.exportManager.exportFigureImage("jpg", 300);
    } else {
      console.error("[Export] ExportManager not initialized");
    }
  });

  // FIGZ Bundle (.figz zipped format)
  const exportFigzBtn = document.getElementById("export-figz");
  exportFigzBtn?.addEventListener("click", async () => {
    console.log("[Export] FIGZ Bundle (.figz)");
    if (canvasManager.exportManager) {
      await canvasManager.exportManager.exportAsFigzBundle();
    } else {
      console.error("[Export] ExportManager not initialized");
    }
  });

  console.log(
    "[VisEditor] Export dropdown handlers initialized (backend-based)",
  );
}

/**
 * Load figure from disk if it exists.
 * Figures are always loaded from disk (figz/pltz files), not localStorage.
 */
async function loadFigureFromDiskIfExists(
  canvasManager: any,
  projectOwner?: string,
  projectSlug?: string,
): Promise<void> {
  if (!projectOwner || !projectSlug) {
    console.log("[VisEditor] No project context, skipping auto-load");
    return;
  }

  // Get current figure name from tab manager
  const figureName =
    canvasManager.bundleCanvasManager?.getProjectContext()?.figureName ||
    "Figure1";

  // Construct figz path based on project structure
  // Path: {project_root}/scitex/vis/figures/{figureName}.fig.zip (zipped format)
  const figzPath = `scitex/vis/figures/${figureName}.fig.zip`;

  console.log(`[VisEditor] Checking for figz bundle: ${figzPath}`);

  try {
    // Try to load the figz bundle from disk (include project context for path resolution)
    const response = await fetch(
      `/apps/vis/api/bundles/figz/load/?path=${encodeURIComponent(figzPath)}&project_owner=${encodeURIComponent(projectOwner)}&project_slug=${encodeURIComponent(projectSlug)}`,
    );

    if (response.ok) {
      // figz exists, load it
      await canvasManager.loadFigzBundle(figzPath);
      console.log(`[VisEditor] Loaded figure from disk: ${figzPath}`);
    } else {
      // figz doesn't exist - that's OK, start with empty canvas
      console.log(
        `[VisEditor] No figz bundle found at ${figzPath}, starting fresh`,
      );
    }
  } catch (err) {
    console.log("[VisEditor] No figz bundle to load:", err);
  }
}

/**
 * Initialize bundle managers for canvas-as-figz architecture
 * Canvas = figz bundle, each plot = pltz panel
 */
async function initializeBundleComponents(editorInstance: any): Promise<void> {
  try {
    const { pltzBundleManager, figzBundleManager } =
      await import("../_vis/index.js");

    // Expose bundle managers to window for canvas integration
    (window as any).visEditor.pltzBundleManager = pltzBundleManager;
    (window as any).visEditor.figzBundleManager = figzBundleManager;

    console.log(
      "[VisEditor] Bundle managers initialized (canvas-as-figz mode)",
    );
  } catch (error) {
    console.warn("[VisEditor] Bundle managers not available:", error);
  }
}
