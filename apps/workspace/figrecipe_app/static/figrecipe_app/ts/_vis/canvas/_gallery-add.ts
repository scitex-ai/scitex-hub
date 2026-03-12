/**
 * Gallery panel add operations for bundle canvas.
 * Uses add_panel_to_figz endpoint - panels are embedded inside figz, no standalone pltz.
 */

import type {
  PanelSpec,
  BundleCanvasState,
  BundleCanvasCallbacks,
} from "./_bundle-types.js";
import { getBundlePanels } from "./_panel-ops.js";
import {
  getCSRFToken,
  ensureFigzBundleExists,
  debouncedFigzAutoSave,
  AutoSaveTimer,
} from "./_auto-save.js";

/**
 * Load an embedded panel from figz bundle onto canvas
 */
async function loadEmbeddedPanel(
  figzPath: string,
  panelLabel: string,
  position: { x_mm: number; y_mm: number },
  size: { width_mm: number; height_mm: number },
  state: BundleCanvasState,
  callbacks: BundleCanvasCallbacks,
  hitmapColorMap?: Record<string, any>,
): Promise<void> {
  if (!state.canvas) {
    console.error("[BundleCanvasManager] Canvas not initialized");
    return;
  }

  // Use the new figz panel preview endpoint for embedded panels (include project context for path resolution)
  const previewUrl = `/apps/figrecipe/api/bundles/figz/panel-preview/?path=${encodeURIComponent(figzPath)}&panel=${encodeURIComponent(panelLabel)}&project_owner=${encodeURIComponent(state.projectOwner)}&project_slug=${encodeURIComponent(state.projectSlug)}&t=${Date.now()}`;

  const mmToPx = state.bundleRenderDpi / 25.4;
  const x = position.x_mm * mmToPx;
  const y = position.y_mm * mmToPx;
  const w = size.width_mm * mmToPx;
  const h = size.height_mm * mmToPx;

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

    const hitmapUrl = `/apps/figrecipe/api/bundles/figz/panel-preview/?path=${encodeURIComponent(figzPath)}&panel=${encodeURIComponent(panelLabel)}&project_owner=${encodeURIComponent(state.projectOwner)}&project_slug=${encodeURIComponent(state.projectSlug)}&type=hitmap`;

    img.set({
      left: x,
      top: y,
      scaleX: scaleX,
      scaleY: scaleY,
      selectable: true,
      lockRotation: true,
      panelId: panelLabel,
      panelLabel: panelLabel,
      figzPath: figzPath,
      // Embedded panel - pltzPath points inside figz
      pltzPath: `${figzPath}#${panelLabel}`,
      isBundlePanel: true,
      isEmbedded: true,
      // Hitmap for element picking (ElementSelectionManager reads axisMetadata)
      axisMetadata: hitmapColorMap
        ? { hitmap: hitmapUrl, hitmap_color_map: hitmapColorMap }
        : undefined,
    });

    state.canvas.add(img);

    if (callbacks.processImageForThemeFn) {
      callbacks.processImageForThemeFn(img);
    }

    console.log(
      `[BundleCanvasManager] ✓ Panel ${panelLabel} added (embedded in figz)`,
    );
  } catch (error) {
    console.error(
      `[BundleCanvasManager] ✗ Failed to load embedded panel ${panelLabel}:`,
      error,
    );
  }
}

/**
 * Add a panel from gallery selection - embeds directly in figz (no standalone pltz)
 */
export async function addPanelFromGallery(
  plotType: string,
  state: BundleCanvasState,
  callbacks: BundleCanvasCallbacks,
  timerState: AutoSaveTimer,
  dataCsv?: string,
  galleryCategory?: string,
  galleryPlotName?: string,
): Promise<{ panelLabel: string; bundlePath: string } | null> {
  if (!state.canvas) {
    console.error("[BundleCanvasManager] Canvas not initialized");
    return null;
  }

  const existingPanels = getBundlePanels(state);
  const usedLabels = new Set(
    existingPanels.map((p: any) => p.panelLabel || "A"),
  );
  const labels = "ABCDEFGH".split("");
  const nextLabel = labels.find((l) => !usedLabels.has(l)) || "A";

  const existingCount = existingPanels.length;

  const panelWidthMm = 80;
  const panelHeightMm = 68;
  const paddingMm = 5;

  const col = existingCount % 2;
  const row = Math.floor(existingCount / 2);
  const xMm = paddingMm + col * (panelWidthMm + paddingMm);
  const yMm = paddingMm + row * (panelHeightMm + paddingMm);

  console.log(
    `[BundleCanvasManager] Creating panel ${nextLabel} at (${xMm}mm, ${yMm}mm)`,
  );

  try {
    // Ensure figz bundle exists for first panel
    if (existingPanels.length === 0 && !state.currentFigzPath) {
      console.log(`[BundleCanvasManager] First panel - creating figz bundle`);
      const figzPath = await ensureFigzBundleExists(state);
      if (figzPath) {
        state.currentFigzPath = figzPath;
        if (callbacks.setCurrentFigzPathFn) {
          callbacks.setCurrentFigzPathFn(figzPath);
        }
      }
    }

    // Use the new add-panel endpoint that embeds pltz inside figz
    const response = await fetch("/apps/figrecipe/api/bundles/figz/add-panel/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({
        project_owner: state.projectOwner,
        project_slug: state.projectSlug,
        figure_name: state.figureName,
        panel_label: nextLabel,
        gallery_category: galleryCategory,
        gallery_plot_name: galleryPlotName,
        data_csv: dataCsv,
        position: { x_mm: xMm, y_mm: yMm },
        size: { width_mm: panelWidthMm, height_mm: panelHeightMm },
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }

    const result = await response.json();
    const figzPath = result.figz_path;
    const hitmapColorMap = result.hitmap_color_map;

    console.log(
      `[BundleCanvasManager] Panel ${nextLabel} embedded in figz: ${figzPath}`,
    );

    // Update state with figz path
    state.currentFigzPath = figzPath;
    if (callbacks.setCurrentFigzPathFn) {
      callbacks.setCurrentFigzPathFn(figzPath);
    }

    // Load the embedded panel onto canvas (with hitmap for element picking)
    await loadEmbeddedPanel(
      figzPath,
      nextLabel,
      { x_mm: xMm, y_mm: yMm },
      { width_mm: panelWidthMm, height_mm: panelHeightMm },
      state,
      callbacks,
      hitmapColorMap,
    );

    state.canvas.renderAll();

    if (callbacks.statusBarCallback) {
      callbacks.statusBarCallback(`Panel ${nextLabel} added: ${plotType}`);
    }

    debouncedFigzAutoSave(timerState, state, callbacks);

    return { panelLabel: nextLabel, bundlePath: figzPath };
  } catch (error) {
    console.error("[BundleCanvasManager] Failed to add panel:", error);
    if (callbacks.statusBarCallback) {
      callbacks.statusBarCallback(`Error: ${error}`);
    }
    return null;
  }
}
