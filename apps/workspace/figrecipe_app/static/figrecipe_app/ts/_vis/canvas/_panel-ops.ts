/**
 * Panel loading operations for bundle canvas.
 */

import type {
  PanelSpec,
  BundleCanvasState,
  BundleCanvasCallbacks,
} from "./_bundle-types.js";

/**
 * Load a figz bundle onto the canvas
 */
export async function loadFigzBundle(
  figzPath: string,
  state: BundleCanvasState,
  callbacks: BundleCanvasCallbacks,
  loadPltzPanelFn: (panel: PanelSpec, figzPath: string) => Promise<void>,
): Promise<void> {
  if (!state.canvas) {
    console.error("[BundleCanvasManager] Canvas not initialized");
    return;
  }

  console.log(`[BundleCanvasManager] Loading figz bundle: ${figzPath}`);

  try {
    callbacks.clearCanvasFn();

    const response = await fetch(
      `/apps/figrecipe/api/bundles/figz/load/?path=${encodeURIComponent(figzPath)}&project_owner=${encodeURIComponent(state.projectOwner)}&project_slug=${encodeURIComponent(state.projectSlug)}`,
    );
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to load figz bundle");
    }

    const figzData = await response.json();
    state.currentFigzPath = figzPath;
    if (callbacks.setCurrentFigzPathFn) {
      callbacks.setCurrentFigzPathFn(figzPath);
    }

    const sizeMm = figzData.size_mm || { width: 170, height: 120 };
    callbacks.setCanvasSizeMmFn(sizeMm.width, sizeMm.height);

    const panels = figzData.panels || [];
    for (const panel of panels) {
      await loadPltzPanelFn(panel, figzPath);
    }

    state.canvas.renderAll();

    if (callbacks.statusBarCallback) {
      callbacks.statusBarCallback(
        `Loaded figure: ${figzPath.split("/").pop()}`,
      );
    }

    console.log(
      `[BundleCanvasManager] Loaded figz bundle with ${panels.length} panels`,
    );
    callbacks.saveSessionStateFn();
  } catch (error) {
    console.error("[BundleCanvasManager] Failed to load figz bundle:", error);
    if (callbacks.statusBarCallback) {
      callbacks.statusBarCallback(`Error: ${error}`);
    }
    throw error;
  }
}

/**
 * Load a single pltz panel onto the canvas
 */
export async function loadPltzPanel(
  panel: PanelSpec,
  figzPath: string,
  state: BundleCanvasState,
  callbacks: BundleCanvasCallbacks,
): Promise<void> {
  if (!state.canvas) {
    console.error("[BundleCanvasManager] Canvas not initialized");
    return;
  }

  // Construct path to pltz panel.
  // - Standalone .plt.zip: use figzPath directly (backend handles plain path)
  // - Panel embedded in .fig.zip: use figzPath#label (backend splits on '#')
  const pltzPath =
    figzPath.endsWith(".plt.zip") || figzPath.endsWith(".pltz")
      ? figzPath
      : `${figzPath}#${panel.label}`;
  const previewUrl = `/apps/figrecipe/api/bundles/pltz/preview/?path=${encodeURIComponent(pltzPath)}&project_owner=${encodeURIComponent(state.projectOwner)}&project_slug=${encodeURIComponent(state.projectSlug)}&t=${Date.now()}`;

  const mmToPx = state.bundleRenderDpi / 25.4;
  const x = (panel.position.x_mm || 0) * mmToPx;
  const y = (panel.position.y_mm || 0) * mmToPx;
  const w = (panel.size.width_mm || 80) * mmToPx;
  const h = (panel.size.height_mm || 60) * mmToPx;

  try {
    const fabric = (window as any).fabric;
    const img = await new Promise<any>((resolve, reject) => {
      fabric.Image.fromURL(
        previewUrl,
        (loadedImg: any) => {
          if (loadedImg) resolve(loadedImg);
          else reject(new Error("Failed to load image"));
        },
        { crossOrigin: "anonymous" },
      );
    });

    const scaleX = w / img.width;
    const scaleY = h / img.height;

    img.set({
      left: x,
      top: y,
      scaleX: scaleX,
      scaleY: scaleY,
      selectable: true,
      lockRotation: true,
      panelId: panel.id,
      panelLabel: panel.label,
      pltzPath: pltzPath,
      figzPath: figzPath,
      isBundlePanel: true,
    });

    state.canvas.add(img);

    if (callbacks.processImageForThemeFn) {
      callbacks.processImageForThemeFn(img);
    }

    console.log(`[BundleCanvasManager] ✓ Panel ${panel.label} added`);
  } catch (error) {
    console.error(
      `[BundleCanvasManager] ✗ Failed to load panel ${panel.label}:`,
      error,
    );
  }
}

/**
 * Refresh a panel image after property changes
 */
export async function refreshPanelImage(
  pltzPath: string,
  state: BundleCanvasState,
): Promise<void> {
  if (!state.canvas) return;

  const panelImg = state.canvas
    .getObjects()
    .find((obj: any) => obj.pltzPath === pltzPath && obj.isBundlePanel);

  if (!panelImg) {
    console.warn(`[BundleCanvasManager] Panel not found: ${pltzPath}`);
    return;
  }

  // The backend PltzService handles reading from inside figz ZIP files via scitex
  const previewUrl = `/apps/figrecipe/api/bundles/pltz/preview/?path=${encodeURIComponent(pltzPath)}&project_owner=${encodeURIComponent(state.projectOwner)}&project_slug=${encodeURIComponent(state.projectSlug)}&t=${Date.now()}`;

  try {
    panelImg.setSrc(
      previewUrl,
      () => {
        state.canvas.renderAll();
        console.log(`[BundleCanvasManager] Panel refreshed: ${pltzPath}`);
      },
      { crossOrigin: "anonymous" },
    );
  } catch (error) {
    console.error(`[BundleCanvasManager] Failed to refresh panel:`, error);
  }
}

/**
 * Get all bundle panels on canvas
 */
export function getBundlePanels(state: BundleCanvasState): any[] {
  if (!state.canvas) return [];
  return state.canvas
    .getObjects()
    .filter((obj: any) => obj.isBundlePanel === true);
}

/**
 * Check if an object is a bundle panel
 */
export function isBundlePanel(obj: any): boolean {
  return obj && obj.isBundlePanel === true;
}
