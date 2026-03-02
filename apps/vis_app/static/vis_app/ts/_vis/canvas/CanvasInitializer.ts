/**
 * CanvasInitializer - Handles Fabric.js canvas initialization and event setup
 *
 * Responsibilities:
 * - Create Fabric.js canvas instance
 * - Initialize all specialized managers
 * - Setup canvas event listeners
 * - Handle selection events and callbacks
 */

import { CANVAS_CONSTANTS } from "../types";
import { GridManager } from "./GridManager";
import { ExportManager } from "./ExportManager";
import { UndoRedoManager } from "./UndoRedoManager";
import { ThemeManager } from "./ThemeManager";
import { ZoomPanManager } from "./ZoomPanManager";
import { SelectionManager } from "./SelectionManager";
import { ObjectManager } from "./ObjectManager";
import { TransformManager } from "./TransformManager";
import { GroupManager } from "./GroupManager";
import { AlignmentManager } from "./AlignmentManager";
import { SnapManager } from "./SnapManager";
import { CropManager } from "./CropManager";
import { ElementSelectionManager } from "./ElementSelectionManager";
import { ContextMenuManager } from "./ContextMenuManager";
import { CanvasResizeManager } from "./CanvasResizeManager";
import { SessionManager } from "./SessionManager";
import { BundleCanvasManager } from "./BundleCanvasManager";
import { NudgeManager } from "./NudgeManager";
import { AxisDebugManager } from "./AxisDebugManager";

export interface CanvasManagerRefs {
  canvas: any;
  gridManager: GridManager;
  exportManager: ExportManager;
  undoRedoManager: UndoRedoManager;
  themeManager: ThemeManager;
  zoomPanManager: ZoomPanManager;
  selectionManager: SelectionManager;
  objectManager: ObjectManager;
  transformManager: TransformManager;
  groupManager: GroupManager;
  alignmentManager: AlignmentManager;
  snapManager: SnapManager;
  cropManager: CropManager;
  elementSelectionManager: ElementSelectionManager;
  contextMenuManager: ContextMenuManager;
  canvasResizeManager: CanvasResizeManager;
  sessionManager: SessionManager;
  bundleCanvasManager: BundleCanvasManager;
  nudgeManager: NudgeManager;
  axisDebugManager: AxisDebugManager;
}

export interface InitCallbacks {
  statusBarCallback?: (message: string) => void;
  rulersAreaTransformCallback?: () => void;
  selectionCallback?: (obj: any | null) => void;
  onObjectResizedCallback?: (
    obj: any,
    newWidth: number,
    newHeight: number,
  ) => void;
  saveUndoState: () => void;
  saveCanvasContent: () => void;
  processSvgGroupForDarkMode: (group: any) => void;
  processNewImageForTheme: (img: any) => void;
  setCanvasSizeMm: (w: number, h: number) => void;
  clearCanvas: () => void;
  saveSessionState: () => void;
  setCurrentFigzPath: (path: string | null) => void;
  getCurrentFigzPath: () => string | null;
  getProjectContext: () => { owner: string; slug: string; figureName: string };
  loadFigzBundle: (path: string) => Promise<void>;
  exitElementSelectionMode: () => void;
  enterGroupEditMode: (group: any) => void;
}

/**
 * Initialize Fabric.js canvas and all managers
 */
export function initializeCanvas(
  callbacks: InitCallbacks,
): CanvasManagerRefs | null {
  const startTime = performance.now();
  console.log("[CanvasInitializer] Starting canvas initialization...");

  const canvasElement = document.getElementById(
    "vis-canvas",
  ) as HTMLCanvasElement;
  if (!canvasElement) {
    console.error(
      "[CanvasInitializer] Canvas element #vis-canvas not found in DOM",
    );
    return null;
  }

  if (typeof fabric === "undefined") {
    console.error("[CanvasInitializer] Fabric.js is not loaded!");
    return null;
  }

  const defaultWidth = CANVAS_CONSTANTS.MAX_CANVAS_WIDTH;
  const defaultHeight = CANVAS_CONSTANTS.MAX_CANVAS_HEIGHT;

  // Get initial theme
  const globalTheme = localStorage.getItem("scitex-theme-preference") || "dark";
  const savedCanvasTheme = localStorage.getItem("canvas-theme") || globalTheme;
  const initialIsDark = savedCanvasTheme === "dark";
  // Light mode uses warm white (#fdfcfa) matching --workspace-bg-elevated
  const initialBgColor = initialIsDark ? "#2a2a2a" : "#fdfcfa";

  try {
    // Create Fabric.js canvas
    const canvas = new fabric.Canvas("vis-canvas", {
      width: defaultWidth,
      height: defaultHeight,
      backgroundColor: initialBgColor,
      selection: true,
      selectionKey: ["ctrlKey", "shiftKey"],
      selectionColor: "rgba(100, 150, 255, 0.15)",
      selectionBorderColor: "#4a9eff",
      selectionLineWidth: 2,
    });

    // Set default object selection styling
    fabric.Object.prototype.set({
      borderColor: "#4a9eff",
      borderScaleFactor: 2,
      cornerColor: "#4a9eff",
      cornerStyle: "circle",
      cornerSize: 10,
      cornerStrokeColor: "#fff",
      transparentCorners: false,
      padding: 4,
    });

    const canvasCreateTime = performance.now();
    console.log(
      `[CanvasInitializer] Fabric.js canvas created in ${(canvasCreateTime - startTime).toFixed(2)}ms`,
    );

    // Initialize all managers
    const gridManager = new GridManager(canvas, callbacks.statusBarCallback);
    const exportManager = new ExportManager(
      canvas,
      callbacks.statusBarCallback,
    );
    const undoRedoManager = new UndoRedoManager(
      canvas,
      callbacks.statusBarCallback,
    );
    const themeManager = new ThemeManager(
      canvas,
      initialIsDark,
      callbacks.statusBarCallback,
    );
    const zoomPanManager = new ZoomPanManager(
      canvas,
      callbacks.rulersAreaTransformCallback,
      callbacks.statusBarCallback,
    );
    const selectionManager = new SelectionManager(
      canvas,
      callbacks.statusBarCallback,
    );

    const objectManager = new ObjectManager(
      canvas,
      () => themeManager.isDark(),
      (img) => themeManager.updateImageForTheme(img),
      (group) => callbacks.processSvgGroupForDarkMode(group),
      callbacks.saveUndoState,
      callbacks.saveCanvasContent,
      callbacks.statusBarCallback,
    );

    const transformManager = new TransformManager(
      canvas,
      callbacks.saveUndoState,
      callbacks.saveCanvasContent,
      callbacks.statusBarCallback,
    );

    const groupManager = new GroupManager(
      canvas,
      callbacks.saveUndoState,
      callbacks.saveCanvasContent,
      callbacks.statusBarCallback,
    );

    const alignmentManager = new AlignmentManager(
      callbacks.statusBarCallback,
      callbacks.saveUndoState,
      callbacks.saveCanvasContent,
    );
    alignmentManager.initialize(canvas);

    const snapManager = new SnapManager(
      callbacks.statusBarCallback,
      () => zoomPanManager.getZoomLevel(),
      () => zoomPanManager.getPanOffset(),
    );
    snapManager.initialize(canvas);

    const cropManager = new CropManager(
      callbacks.statusBarCallback,
      callbacks.saveUndoState,
      callbacks.saveCanvasContent,
      () => zoomPanManager.getZoomLevel(),
      () => zoomPanManager.getPanOffset(),
    );
    cropManager.initialize(canvas);

    const elementSelectionManager = new ElementSelectionManager(
      canvas,
      callbacks.statusBarCallback,
    );

    const contextMenuManager = new ContextMenuManager(
      canvas,
      () => elementSelectionManager.getSelectedElementNames(),
      callbacks.statusBarCallback,
    );

    const canvasResizeManager = new CanvasResizeManager(
      canvas,
      () => zoomPanManager.getZoomLevel(),
      () => zoomPanManager.getPanOffset(),
      () => {
        if (callbacks.rulersAreaTransformCallback) {
          callbacks.rulersAreaTransformCallback();
        }
        if (gridManager.isGridEnabled()) {
          gridManager.drawGrid(themeManager.isDark());
        }
      },
      callbacks.statusBarCallback,
    );

    const bundleCanvasManager = new BundleCanvasManager(
      canvas,
      callbacks.statusBarCallback,
      callbacks.setCanvasSizeMm,
      callbacks.clearCanvas,
      callbacks.saveSessionState,
      callbacks.processNewImageForTheme,
      callbacks.setCurrentFigzPath,
    );

    const sessionManager = new SessionManager(
      canvas,
      callbacks.getCurrentFigzPath,
      callbacks.getProjectContext,
      callbacks.loadFigzBundle,
    );

    const nudgeManager = new NudgeManager(
      canvas,
      callbacks.saveCanvasContent,
      callbacks.statusBarCallback,
    );
    const axisDebugManager = new AxisDebugManager(
      canvas,
      callbacks.statusBarCallback,
    );

    // Draw initial grid if enabled
    if (gridManager.isGridEnabled()) {
      gridManager.drawGrid(initialIsDark);
    }

    // Restore saved view state
    zoomPanManager.restoreViewState();

    console.log(
      `[CanvasInitializer] ✅ Total init: ${(performance.now() - startTime).toFixed(2)}ms`,
    );

    return {
      canvas,
      gridManager,
      exportManager,
      undoRedoManager,
      themeManager,
      zoomPanManager,
      selectionManager,
      objectManager,
      transformManager,
      groupManager,
      alignmentManager,
      snapManager,
      cropManager,
      elementSelectionManager,
      contextMenuManager,
      canvasResizeManager,
      sessionManager,
      bundleCanvasManager,
      nudgeManager,
      axisDebugManager,
    };
  } catch (error) {
    console.error("[CanvasInitializer] Error initializing canvas:", error);
    return null;
  }
}

/**
 * Setup canvas event listeners
 */
export function setupCanvasEventListeners(
  refs: CanvasManagerRefs,
  callbacks: InitCallbacks,
): void {
  const { canvas, snapManager, elementSelectionManager, bundleCanvasManager } =
    refs;

  // Save canvas when objects are modified
  canvas.on("object:modified", () => {
    callbacks.saveCanvasContent();
  });

  // Selection cleared
  canvas.on("selection:cleared", () => {
    callbacks.saveCanvasContent();
    if (callbacks.selectionCallback) {
      callbacks.selectionCallback(null);
    }
    callbacks.exitElementSelectionMode();
  });

  // Selection created - auto-enter element selection for plots
  canvas.on("selection:created", (e: any) => {
    handleSelectionEvent(e, refs, callbacks);
  });

  canvas.on("selection:updated", (e: any) => {
    handleSelectionEvent(e, refs, callbacks);
  });

  // Double-click to enter group edit mode (non-plot groups only)
  canvas.on("mouse:dblclick", (e: any) => {
    const target = e.target;
    if (target && target.type === "group") {
      const isPlotImage =
        target.plotInfo || target.csvData || target.axisMetadata;
      if (isPlotImage) {
        if (callbacks.statusBarCallback) {
          callbacks.statusBarCallback(
            "Plot data cannot be edited (scientific integrity)",
          );
        }
        return;
      }
      callbacks.enterGroupEditMode(target);
    }
  });

  // Snap to other objects while moving
  canvas.on("object:moving", (e: any) => {
    if (snapManager.isSnapEnabled()) {
      snapManager.handleObjectSnap(e.target);
    }
  });

  // Clear guidelines and handle resize on object modified
  canvas.on("object:modified", (e: any) => {
    snapManager.clearAlignmentLines();
    callbacks.saveCanvasContent();

    const obj = e.target;
    if (obj && (obj.scaleX !== 1 || obj.scaleY !== 1)) {
      if (obj.csvData && obj.plotInfo && callbacks.onObjectResizedCallback) {
        const newWidth = Math.round(obj.width * obj.scaleX);
        const newHeight = Math.round(obj.height * obj.scaleY);
        callbacks.onObjectResizedCallback(obj, newWidth, newHeight);
      }
    }

    if (callbacks.selectionCallback && obj) {
      callbacks.selectionCallback(obj);
    }

    if (obj && obj.isBundlePanel) {
      bundleCanvasManager.debouncedFigzAutoSave();
    }
  });

  // Clear guidelines on mouse up
  canvas.on("mouse:up", () => {
    snapManager.clearAlignmentLines();
  });

  console.log("[CanvasInitializer] Canvas event listeners setup complete");
}

/**
 * Handle selection events
 */
function handleSelectionEvent(
  e: any,
  refs: CanvasManagerRefs,
  callbacks: InitCallbacks,
): void {
  const { canvas, elementSelectionManager } = refs;

  if (callbacks.selectionCallback && e.selected && e.selected.length > 0) {
    const activeObj = canvas.getActiveObject();
    callbacks.selectionCallback(activeObj || e.selected[0]);

    // Only auto-enter element selection for single plot images/groups
    if (e.selected.length === 1) {
      const selected = e.selected[0];
      if (
        (selected.type === "image" || selected.type === "group") &&
        selected.axisMetadata?.element_bboxes
      ) {
        elementSelectionManager.enterElementSelectionMode(selected, {
          x: 0,
          y: 0,
        });
      } else {
        elementSelectionManager.exitElementSelectionMode();
      }
    } else {
      elementSelectionManager.exitElementSelectionMode();
    }
  }
}
