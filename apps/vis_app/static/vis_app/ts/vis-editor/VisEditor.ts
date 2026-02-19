/**
 * SciTeX Vis Editor - Main Coordinator Class
 *
 * Lightweight coordinator that:
 * - Initializes all manager modules
 * - Connects managers through callbacks
 * - Maintains overall editor state
 */

import {
  RulersManager,
  CanvasManager,
  DataTableManager,
  PropertiesManager,
  UIManager,
  DataTabManager,
  CanvasTabManager,
  FigureDropHandler,
  SciTeXEditor,
} from "../vis/index.ts";

import { EditorCallbackHandlers } from "./EditorCallbackHandlers.ts";
import {
  CsvDataCoordinator,
  GalleryCoordinator,
  TabStateCoordinator,
  TreeSyncCoordinator,
} from "./coordinators/index.ts";
import { initializeAllManagers } from "./VisEditorManagerInit.ts";

/**
 * VisEditor - Coordinator class that manages all editor components
 */
export class VisEditor {
  // Manager instances
  rulersManager!: RulersManager;
  canvasManager!: CanvasManager;
  dataTableManager!: DataTableManager;
  propertiesManager!: PropertiesManager;
  uiManager!: UIManager;
  dataTabManager!: DataTabManager;
  canvasTabManager!: CanvasTabManager;

  // Coordinators
  csvDataCoordinator!: CsvDataCoordinator;
  galleryCoordinator!: GalleryCoordinator;
  tabStateCoordinator!: TabStateCoordinator;
  treeSyncCoordinator!: TreeSyncCoordinator;

  // SciTeX integration
  private figureDropHandler!: FigureDropHandler;
  private scitexEditor!: SciTeXEditor;
  callbackHandlers!: EditorCallbackHandlers;

  // Deletion flag to prevent recursive deletion
  isDeleting: boolean = false;

  // Shared references for managers
  firstRowIsHeader: boolean = true;
  firstColIsIndex: boolean = false;

  // Project context for bundle-based flow
  projectOwner: string = "";
  projectSlug: string = "";
  figureName: string = "Figure1";

  constructor() {
    console.log("[VisEditor] Initializing modular Vis Editor...");
    initializeAllManagers(this);
    this.initializeEditor();
  }

  /**
   * Save current canvas state to the active tab
   */
  saveCanvasForCurrentTab(): void {
    this.tabStateCoordinator.saveCanvasForCurrentTab();
  }

  /**
   * Restore canvas content from a specific tab
   */
  async restoreCanvasForTab(tabId: string): Promise<void> {
    return this.tabStateCoordinator.restoreCanvasForTab(tabId);
  }

  /**
   * Initialize editor components
   */
  private async initializeEditor(): Promise<void> {
    const totalStart = performance.now();
    console.log("[VisEditor] Starting optimized initialization...");

    // PHASE 1: CRITICAL PATH
    this.uiManager.initializeEventListeners();
    this.dataTabManager.initializeEventListeners();
    this.dataTabManager.renderTabs();
    this.canvasTabManager.initializeEventListeners();
    this.canvasTabManager.renderTabs();
    this.dataTableManager.initializeBlankTable();

    // PHASE 2: DEFERRED
    await new Promise((resolve) => setTimeout(resolve, 0));
    this.setupDataTableEvents();
    this.dataTableManager.setupColumnResizing();
    this.uiManager.setupKeyboardShortcuts();

    // PHASE 3: Canvas and heavy graphics
    await new Promise((resolve) => setTimeout(resolve, 0));
    this.canvasManager.initCanvas();
    this.canvasManager.setupCanvasEvents();
    this.canvasManager.setSelectionCallback(
      this.callbackHandlers.createSelectionCallback(),
    );
    this.canvasManager.setObjectResizedCallback(
      async (obj: any, newWidth: number, newHeight: number) => {
        await this.reRenderPlotAtSize(obj, newWidth, newHeight);
      },
    );
    this.canvasManager.setElementSelectionCallback(
      this.callbackHandlers.createElementSelectionCallback(),
    );

    this.rulersManager["canvas"] = this.canvasManager.canvas;
    this.rulersManager.initializeRulers();
    this.rulersManager.setTransformCallback(
      this.callbackHandlers.createTransformCallback(),
    );
    this.rulersManager.setupRulerDragging();
    this.updateRulersAreaTransform();

    this.figureDropHandler = new FigureDropHandler({
      canvasSelector: "#canvas-container",
      dataTableSelector: ".data-table-container",
      canvasManager: this.canvasManager,
      onCsvLoad: (data: string[][]) => {
        console.log("[VisEditor] CSV loaded via drop:", data.length, "rows");
      },
    });

    setTimeout(
      this.callbackHandlers.createCanvasRestorationCallback(
        this.canvasTabManager,
        (tabId: string) => this.restoreCanvasForTab(tabId),
        (objects: any[]) =>
          this.csvDataCoordinator.loadMissingMetadata(objects),
        () => this.saveCanvasForCurrentTab(),
      ),
      100,
    );

    // PHASE 4: Properties and final setup
    await new Promise((resolve) => setTimeout(resolve, 0));
    this.propertiesManager.initPropertiesTabs();
    this.propertiesManager.setupPropertySliders();
    this.uiManager.setPropertiesManager(this.propertiesManager);
    this.uiManager.setDataTableManager(this.dataTableManager);
    this.uiManager.initializeTreeManager();

    this.propertiesManager.setPanelRefreshCallback(async (pltzPath: string) => {
      await this.canvasManager.refreshPanelImage(pltzPath);
    });

    this.initializePlotGallery();
    this.updateStatusBar("Ready");

    document.addEventListener("theme-changed", (e: CustomEvent) => {
      const isDark = e.detail?.theme === "dark";
      this.rulersManager.updateRulerTheme(isDark);
    });

    const totalEnd = performance.now();
    console.log(
      `[VisEditor] Total initialization: ${(totalEnd - totalStart).toFixed(2)}ms`,
    );
  }

  private setupDataTableEvents(): void {
    console.log("[VisEditor] Data table using native scrolling");
  }

  updateRulersAreaTransform(): void {
    const rulersArea = document.querySelector(
      ".vis-rulers-area",
    ) as HTMLElement;
    if (!rulersArea) return;

    const zoom = this.canvasManager.getCanvasZoomLevel();
    const pan = this.canvasManager.getCanvasPanOffset();

    this.rulersManager.setCanvasZoomLevel(zoom);
    this.rulersManager.setCanvasPanOffset(pan);

    rulersArea.style.transform = `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`;
    rulersArea.style.transformOrigin = "0 0";
  }

  updateStatusBar(message?: string): void {
    this.uiManager.updateStatusBar(message);
  }

  /**
   * Create a quick plot using the bundle-based flow
   */
  async createQuickPlot(plotType: string): Promise<void> {
    const currentData = this.dataTableManager.getCurrentData();

    console.log(`[VisEditor] Creating ${plotType} plot via bundle flow...`);
    this.updateStatusBar(`Creating ${plotType} plot...`);

    let dataCsv: string | undefined;
    if (currentData && currentData.rows.length > 0) {
      const headers = currentData.headers || [];
      const rows = currentData.rows.map((row: any[]) => row.join(","));
      dataCsv = [headers.join(","), ...rows].join("\n");
    }

    const { category, plotName } = this.mapPlotTypeToGallery(plotType);

    try {
      await this.canvasManager.addPanelFromGallery(
        plotType,
        dataCsv,
        this.projectOwner,
        this.projectSlug,
        this.figureName,
        category,
        plotName,
      );

      this.updateStatusBar(`Created ${plotType} panel`);
      await this.refreshFilesTree();
    } catch (error) {
      console.error("[VisEditor] Failed to create quick plot:", error);
      this.updateStatusBar(`Failed to create ${plotType} plot`);
    }
  }

  /**
   * Map plot type to gallery category and plot name
   */
  private mapPlotTypeToGallery(plotType: string): {
    category: string;
    plotName: string;
  } {
    const mapping: Record<string, { category: string; plotName: string }> = {
      scatter: { category: "scatter", plotName: "scatter" },
      line: { category: "line", plotName: "plot" },
      lineMarker: { category: "line", plotName: "plot" },
      bar: { category: "categorical", plotName: "bar" },
      histogram: { category: "distribution", plotName: "hist" },
      box: { category: "categorical", plotName: "boxplot" },
      violin: { category: "categorical", plotName: "violinplot" },
      heatmap: { category: "grid", plotName: "stx_heatmap" },
      contour: { category: "contour", plotName: "contour" },
      pie: { category: "special", plotName: "pie" },
      step: { category: "line", plotName: "step" },
      stem: { category: "scatter", plotName: "stem" },
    };
    return mapping[plotType] || { category: "line", plotName: "plot" };
  }

  public updateCanvasTheme(isDark: boolean): void {
    this.canvasManager.updateCanvasTheme(isDark);
  }

  public updateGlobalTheme(isDark: boolean): void {
    this.rulersManager.updateRulerTheme(isDark);
  }

  public deleteSelectedObject(): void {
    this.isDeleting = true;

    const activeObj = this.canvasManager.canvas?.getActiveObject();
    if (activeObj) {
      const objects =
        activeObj.type === "activeSelection"
          ? (activeObj as any).getObjects()
          : [activeObj];

      for (const obj of objects) {
        const objId = obj.id;
        if (objId) {
          const tabId = this.csvDataCoordinator.getFigureToTabMap().get(objId);
          if (tabId) {
            this.dataTabManager.closeTab(tabId);
            this.csvDataCoordinator.getFigureToTabMap().delete(objId);
            this.csvDataCoordinator.getTabToFigureMap().delete(tabId);
          }
        }
      }
    }

    this.canvasManager.removeActiveObject();
    this.canvasManager.saveCanvasContent();
    this.isDeleting = false;
    this.updateStatusBar("Object deleted");
  }

  removeFigureById(figureId: string): void {
    if (!this.canvasManager.canvas) return;

    const objects = this.canvasManager.canvas.getObjects();
    const figure = objects.find((obj: any) => obj.id === figureId);
    if (figure) {
      this.canvasManager.canvas.remove(figure);
      this.canvasManager.canvas.renderAll();
      this.canvasManager.saveCanvasContent();
      this.updateStatusBar("Figure removed");
    }
  }

  public duplicateSelectedObject(): void {
    this.canvasManager.duplicateActiveObject();
  }

  handleSizeAction(
    action: "match-size" | "match-width" | "match-height" | "multiple-crop",
  ): void {
    switch (action) {
      case "match-size":
        this.canvasManager.matchSize();
        break;
      case "match-width":
        this.canvasManager.matchWidth();
        break;
      case "match-height":
        this.canvasManager.matchHeight();
        break;
      case "multiple-crop":
        this.canvasManager.multipleCrop();
        break;
    }
  }

  private initializePlotGallery(): void {
    this.galleryCoordinator.initialize();
  }

  public setProjectContext(
    owner: string,
    slug: string,
    figureName?: string,
  ): void {
    this.projectOwner = owner;
    this.projectSlug = slug;
    if (figureName) this.figureName = figureName;
    console.log(
      `[VisEditor] Project context set: ${owner}/${slug}/${this.figureName}`,
    );
  }

  public getManagers() {
    return {
      canvasManager: this.canvasManager,
      dataTableManager: this.dataTableManager,
      canvasTabManager: this.canvasTabManager,
      dataTabManager: this.dataTabManager,
    };
  }

  public getCanvasManager(): CanvasManager {
    return this.canvasManager;
  }

  public async refreshFilesTree(): Promise<void> {
    return this.treeSyncCoordinator.refreshFilesTree();
  }

  public validateTabsAgainstFilesystem(): void {
    this.tabStateCoordinator.validateTabsAgainstFilesystem();
  }

  public clearAllTabs(): void {
    this.tabStateCoordinator.clearAllTabs();
  }

  private async reRenderPlotAtSize(
    obj: any,
    newWidth: number,
    newHeight: number,
  ): Promise<void> {
    return this.galleryCoordinator.reRenderPlotAtSize(obj, newWidth, newHeight);
  }

  public async plotAllTypes(): Promise<void> {
    return this.galleryCoordinator.plotAllTypes();
  }

  syncTreeToFigure(absoluteFigzPath: string): void {
    this.treeSyncCoordinator.syncTreeToFigure(absoluteFigzPath);
  }
}
