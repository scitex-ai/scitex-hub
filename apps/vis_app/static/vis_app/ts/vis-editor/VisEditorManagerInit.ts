/**
 * VisEditor Manager Initialization
 *
 * Extracted from VisEditor.initializeManagers() for file-size compliance.
 * Contains the wiring logic that connects all manager and coordinator instances.
 */

import {
  RulersManager,
  CanvasManager,
  DataTableManager,
  PropertiesManager,
  UIManager,
  DataTabManager,
  CanvasTabManager,
} from "../vis/index.ts";

import { EditorCallbackHandlers } from "./EditorCallbackHandlers.ts";
import {
  CsvDataCoordinator,
  GalleryCoordinator,
  TabStateCoordinator,
  TreeSyncCoordinator,
} from "./coordinators/index.ts";

/**
 * Interface for the VisEditor context passed into initializeAllManagers.
 * Exposes only what the initialization logic needs from the editor instance.
 */
export interface VisEditorContext {
  // Writable manager slots
  rulersManager: RulersManager;
  canvasManager: CanvasManager;
  dataTableManager: DataTableManager;
  propertiesManager: PropertiesManager;
  uiManager: UIManager;
  dataTabManager: DataTabManager;
  canvasTabManager: CanvasTabManager;
  csvDataCoordinator: CsvDataCoordinator;
  galleryCoordinator: GalleryCoordinator;
  tabStateCoordinator: TabStateCoordinator;
  treeSyncCoordinator: TreeSyncCoordinator;
  callbackHandlers: EditorCallbackHandlers;

  // State flags and fields
  isDeleting: boolean;
  firstRowIsHeader: boolean;
  firstColIsIndex: boolean;
  projectOwner: string;
  projectSlug: string;
  figureName: string;

  // Methods called during initialization
  updateStatusBar(message?: string): void;
  updateRulersAreaTransform(): void;
  deleteSelectedObject(): void;
  duplicateSelectedObject(): void;
  restoreCanvasForTab(tabId: string): Promise<void>;
  saveCanvasForCurrentTab(): void;
  refreshFilesTree(): Promise<void>;
  removeFigureById(figureId: string): void;
  syncTreeToFigure(absoluteFigzPath: string): void;
  createQuickPlot(plotType: string): Promise<void>;
  handleSizeAction(
    action: "match-size" | "match-width" | "match-height" | "multiple-crop",
  ): void;
}

/**
 * Initialize all manager and coordinator instances on the editor context.
 * Mirrors the original VisEditor.initializeManagers() logic exactly.
 */
export function initializeAllManagers(editor: VisEditorContext): void {
  // Initialize CanvasManager
  editor.canvasManager = new CanvasManager(
    (message: string) => editor.updateStatusBar(message),
    () => editor.updateRulersAreaTransform(),
  );

  // Initialize RulersManager
  editor.rulersManager = new RulersManager(null, (message: string) =>
    editor.updateStatusBar(message),
  );

  // Initialize DataTableManager
  editor.dataTableManager = new DataTableManager(
    (message: string) => editor.updateStatusBar(message),
    () => editor.propertiesManager.updateColumnDropdowns(),
    () => editor.updateRulersAreaTransform(),
  );

  // Initialize PropertiesManager
  editor.propertiesManager = new PropertiesManager(() =>
    editor.dataTableManager.getCurrentData(),
  );

  // Initialize UIManager
  editor.uiManager = new UIManager(
    (file: File) => editor.dataTableManager.handleFileImport(file),
    () => editor.dataTableManager.loadDemoData(),
    (count: number) => editor.dataTableManager.addColumns(count),
    (count: number) => editor.dataTableManager.addRows(count),
    () => (editor.dataTableManager as any)["copySelectionToClipboard"](),
    (plotType: string) => editor.createQuickPlot(plotType),
    () => editor.canvasManager.zoomIn(),
    () => editor.canvasManager.zoomOut(),
    () => editor.canvasManager.zoomToContent(),
    () => editor.canvasManager.toggleGrid(),
    { value: editor.firstRowIsHeader },
    { value: editor.firstColIsIndex },
    () => editor.dataTableManager.renderEditableDataTable(),
    (message: string) => editor.updateStatusBar(message),
    () => editor.deleteSelectedObject(),
    () => editor.duplicateSelectedObject(),
    () => editor.canvasManager.undo(),
    () => editor.canvasManager.redo(),
    () => editor.canvasManager.copyActiveObject(),
    () => editor.canvasManager.pasteObject(),
    (direction) => editor.canvasManager.alignObjects(direction),
    (action) => editor.canvasManager.arrangeObject(action),
    (direction) => editor.canvasManager.distributeObjects(direction),
    (action) => editor.handleSizeAction(action),
    () => editor.canvasManager.groupObjects(),
    () => editor.canvasManager.ungroupObjects(),
    () => editor.canvasManager.copyView(),
    () => editor.canvasManager.pasteView(),
    (direction, shift) => editor.canvasManager.nudgeObjects(direction, shift),
    () => editor.canvasManager.selectAll(),
    (direction: "L" | "C" | "R" | "T" | "M" | "B" | "S") => {
      if (direction === "S") {
        editor.canvasManager.stackVertically();
      } else {
        editor.canvasManager.alignByAxis(direction);
      }
    },
    () => editor.canvasManager.exitElementSelectionMode(),
    () => editor.canvasManager.toggleCanvasTheme(),
    () => editor.canvasManager.increaseCanvasSize(),
    () => editor.canvasManager.decreaseCanvasSize(),
    () => editor.canvasManager.fitCanvasToContent(),
  );

  // Initialize DataTabManager
  editor.dataTabManager = new DataTabManager();
  editor.dataTabManager.setCallbacks(
    (tabId: string) => {
      console.log("[VisEditor] Data tab changed to:", tabId);
      const tabData = editor.dataTabManager.getTabData(tabId);
      if (tabData && Array.isArray(tabData) && tabData.length > 0) {
        editor.dataTableManager.loadFromArray(tabData, true);
        editor.updateStatusBar(`Loaded data for tab`);
      }
    },
    (tabId: string) => {
      console.log("[VisEditor] Data tab closed:", tabId);
      if (!editor.isDeleting) {
        const figureId = editor.csvDataCoordinator
          .getTabToFigureMap()
          .get(tabId);
        if (figureId) {
          editor.isDeleting = true;
          editor.removeFigureById(figureId);
          editor.csvDataCoordinator.getTabToFigureMap().delete(tabId);
          editor.csvDataCoordinator.getFigureToTabMap().delete(figureId);
          editor.isDeleting = false;
        }
      }
    },
    (tabId: string, newName: string) => {
      console.log("[VisEditor] Data tab renamed:", tabId, "to", newName);
    },
  );

  // Initialize CanvasTabManager
  editor.canvasTabManager = new CanvasTabManager();
  editor.canvasTabManager.setCallbacks(
    async (tabId: string) => {
      console.log("[VisEditor] Canvas tab changed to:", tabId);
      await editor.restoreCanvasForTab(tabId);
      const activeTab = editor.canvasTabManager.getActiveTab();
      if (activeTab) {
        editor.updateStatusBar(`Switched to ${activeTab.figureName}`);
        if (activeTab.figurePath) {
          editor.syncTreeToFigure(activeTab.figurePath);
        }
      }
    },
    (tabId: string) => {
      console.log("[VisEditor] Canvas tab closed:", tabId);
    },
    (tabId: string, newName: string) => {
      console.log("[VisEditor] Canvas tab renamed:", tabId, "to", newName);
    },
    () => {
      editor.saveCanvasForCurrentTab();
    },
    async (figureName: string, figurePath: string) => {
      console.log(
        "[VisEditor] New figz bundle created:",
        figureName,
        figurePath,
      );
      await editor.refreshFilesTree();
      editor.updateStatusBar(`Created ${figureName}`);
    },
  );

  // Initialize TreeSyncCoordinator (no dependencies on other coordinators)
  editor.treeSyncCoordinator = new TreeSyncCoordinator({
    getProjectContext: () => ({
      projectOwner: editor.projectOwner || (window as any).projectOwner,
      projectSlug: editor.projectSlug || (window as any).projectSlug,
    }),
  });

  // Initialize TabStateCoordinator
  editor.tabStateCoordinator = new TabStateCoordinator({
    canvasManager: editor.canvasManager,
    canvasTabManager: editor.canvasTabManager,
    dataTabManager: editor.dataTabManager,
    rulersManager: editor.rulersManager,
    updateStatusBar: (message: string) => editor.updateStatusBar(message),
    updateRulersAreaTransform: () => editor.updateRulersAreaTransform(),
  });

  // Initialize CsvDataCoordinator
  editor.csvDataCoordinator = new CsvDataCoordinator({
    dataTabManager: editor.dataTabManager,
    dataTableManager: editor.dataTableManager,
    propertiesManager: editor.propertiesManager,
    canvasManager: editor.canvasManager,
    galleryCategories: () =>
      editor.galleryCoordinator?.getGalleryCategories() || null,
    updateStatusBar: (message: string) => editor.updateStatusBar(message),
    getTabTypeFromCategory: (category: string) =>
      editor.tabStateCoordinator.getTabTypeFromCategory(category),
  });

  // Initialize callback handlers
  editor.callbackHandlers = new EditorCallbackHandlers({
    canvasManager: editor.canvasManager,
    propertiesManager: editor.propertiesManager,
    dataTableManager: editor.dataTableManager,
    rulersManager: editor.rulersManager,
    syncTreeToPanel: (pltzPath: string) =>
      editor.treeSyncCoordinator.syncTreeToPanel(pltzPath),
    loadCsvDataInTab: (obj: any) =>
      editor.csvDataCoordinator.loadCsvDataInTab(obj),
    loadCsvForBundlePanel: (obj: any) =>
      editor.csvDataCoordinator.loadCsvForBundlePanel(obj),
    loadCsvForImage: (obj: any) =>
      editor.csvDataCoordinator.loadCsvForImage(obj),
    updateStatusBar: (message: string) => editor.updateStatusBar(message),
    inferCsvColumnsFromLabel: (elementName: string, elementInfo: any) =>
      editor.csvDataCoordinator.inferCsvColumnsFromLabel(
        elementName,
        elementInfo,
      ),
    updateRulersAreaTransform: () => editor.updateRulersAreaTransform(),
    getTabTypeFromCategory: (category: string) =>
      editor.tabStateCoordinator.getTabTypeFromCategory(category),
    createPltzBundleFromGallery: (
      plot: any,
      category: string,
      csvData: string[][],
    ) =>
      editor.galleryCoordinator.createPltzBundleFromGallery(
        plot,
        category,
        csvData,
      ),
    getProjectContext: () => ({
      projectOwner: editor.projectOwner || (window as any).projectOwner,
      projectSlug: editor.projectSlug || (window as any).projectSlug,
    }),
    setCurrentPlotState: (
      plot: any,
      plotType: string,
      category: string,
      csvData: string[][],
    ) => {
      editor.galleryCoordinator.setPlotState(plot, plotType, category, csvData);
    },
  });

  // Initialize GalleryCoordinator (needs callbackHandlers)
  editor.galleryCoordinator = new GalleryCoordinator({
    canvasManager: editor.canvasManager,
    dataTableManager: editor.dataTableManager,
    propertiesManager: editor.propertiesManager,
    dataTabManager: editor.dataTabManager,
    csvDataCoordinator: editor.csvDataCoordinator,
    callbackHandlers: editor.callbackHandlers,
    updateStatusBar: (message: string) => editor.updateStatusBar(message),
    getProjectContext: () => ({
      projectOwner: editor.projectOwner || (window as any).projectOwner,
      projectSlug: editor.projectSlug || (window as any).projectSlug,
      figureName: editor.figureName,
    }),
    refreshFilesTree: () => editor.treeSyncCoordinator.refreshFilesTree(),
  });
}
