/**
 * ElementSelectionManager - Manages element-level selection within plot images
 *
 * This provides Flask-editor-like element selection for the Django vis app.
 * It allows users to click on specific elements (traces, labels, axes) within
 * a plot image and see them highlighted.
 *
 * Selection Strategy:
 * 1. Hitmap (if loaded): Fast 24-bit RGB ID lookup with neighborhood sampling
 * 2. Fallback: Legacy bbox/geometry-based proximity detection
 *
 * Hover effects use the ORIGINAL figure's geometry and colors (not hitmap colors).
 */

import type { Canvas as FabricCanvas } from "fabric";
import {
  HitmapManager,
  hitmapManager,
  type HitmapElementInfo,
  type HitmapColorMap,
} from "./HitmapManager";
import {
  PROXIMITY_THRESHOLD,
  SCATTER_THRESHOLD,
  isElementBbox,
} from "./ElementSelectionTypes";
import { drawElementOverlay } from "./ElementOverlayRenderer";

// Re-export all types from ElementSelectionTypes for backward compatibility
export type {
  GeometryPx,
  ElementBbox,
  ElementBboxesMeta,
  ElementBboxes,
} from "./ElementSelectionTypes";
export { isElementBbox } from "./ElementSelectionTypes";

export class ElementSelectionManager {
  private canvas: FabricCanvas | null = null;
  private hoveredElement: string | null = null;
  private selectedElement: string | null = null;
  private overlayCanvas: HTMLCanvasElement | null = null;
  private statusCallback: ((msg: string) => void) | null = null;

  // Cycle selection state
  private elementsAtCursor: string[] = [];
  private currentCycleIndex: number = 0;

  // Hitmap manager reference
  private hitmapManager: HitmapManager = hitmapManager;

  constructor() {
    console.log("[ElementSelectionManager] Initialized");
  }

  /**
   * Load hitmap for fast element picking
   * @param hitmapUrl - URL to plot_hitmap.png
   * @param colorMap - Mapping from element ID to element info
   */
  public async loadHitmap(
    hitmapUrl: string,
    colorMap: HitmapColorMap,
  ): Promise<void> {
    await this.hitmapManager.load(hitmapUrl, colorMap);
  }

  /**
   * Check if hitmap is loaded and ready
   */
  public isHitmapReady(): boolean {
    return this.hitmapManager.isReady();
  }

  /**
   * Find element using hitmap (fast path)
   * @param imgX - X coordinate in image pixels
   * @param imgY - Y coordinate in image pixels
   * @param displayWidth - Current display width
   * @param displayHeight - Current display height
   */
  public findElementByHitmap(
    imgX: number,
    imgY: number,
    displayWidth: number,
    displayHeight: number,
  ): string | null {
    if (!this.hitmapManager.isReady()) return null;

    // Scale display coordinates to hitmap coordinates
    const { width: hitmapW, height: hitmapH } =
      this.hitmapManager.getDimensions();
    const hx = (imgX / displayWidth) * hitmapW;
    const hy = (imgY / displayHeight) * hitmapH;

    // Use neighborhood sampling for thin lines
    const elements = this.hitmapManager.getElementsInNeighborhood(hx, hy, 2);
    if (elements.length > 0) {
      return elements[0].label;
    }
    return null;
  }

  /**
   * Find all elements at position using hitmap (for cycle selection)
   */
  public findAllElementsByHitmap(
    imgX: number,
    imgY: number,
    displayWidth: number,
    displayHeight: number,
  ): string[] {
    if (!this.hitmapManager.isReady()) return [];

    const { width: hitmapW, height: hitmapH } =
      this.hitmapManager.getDimensions();
    const hx = (imgX / displayWidth) * hitmapW;
    const hy = (imgY / displayHeight) * hitmapH;

    const elements = this.hitmapManager.getElementsInNeighborhood(hx, hy, 3);
    return elements.map((e) => e.label);
  }

  /**
   * Get hitmap element info by label
   */
  public getHitmapElementInfo(label: string): HitmapElementInfo | null {
    const elements = this.hitmapManager.getAllElements();
    return elements.find((e) => e.label === label) || null;
  }

  /**
   * Set the Fabric canvas reference
   */
  public setCanvas(canvas: FabricCanvas): void {
    this.canvas = canvas;
  }

  /**
   * Set status bar callback
   */
  public setStatusCallback(callback: (msg: string) => void): void {
    this.statusCallback = callback;
  }

  /**
   * Find the element at a given point within a plot image
   */
  public findElementAt(
    bboxes: import("./ElementSelectionTypes.ts").ElementBboxes,
    imgX: number,
    imgY: number,
  ): string | null {
    // Multi-panel aware hit detection with specificity hierarchy:
    // 1. Data elements with points (lines, scatter) - proximity detection
    // 2. Small elements (labels, ticks, legends, bars, fills)
    // 3. Panel bboxes - lowest priority (fallback)

    // First: Check for data elements with points (lines, scatter)
    let closestDataElement: string | null = null;
    let minDistance = Infinity;

    for (const [name, value] of Object.entries(bboxes)) {
      if (!isElementBbox(value)) continue;
      const bbox = value;
      if (bbox.points && bbox.points.length > 0) {
        // Check if cursor is within general bbox area first
        if (
          imgX >= bbox.x0 - SCATTER_THRESHOLD &&
          imgX <= bbox.x1 + SCATTER_THRESHOLD &&
          imgY >= bbox.y0 - SCATTER_THRESHOLD &&
          imgY <= bbox.y1 + SCATTER_THRESHOLD
        ) {
          const elementType = bbox.element_type || "line";
          let dist: number;

          if (elementType === "scatter") {
            dist = this.distanceToNearestPoint(imgX, imgY, bbox.points);
          } else {
            dist = this.distanceToLine(imgX, imgY, bbox.points);
          }

          if (dist < minDistance) {
            minDistance = dist;
            closestDataElement = name;
          }
        }
      }
    }

    // Use appropriate threshold based on element type
    if (closestDataElement) {
      const bbox = bboxes[closestDataElement];
      if (isElementBbox(bbox)) {
        const threshold =
          bbox.element_type === "scatter"
            ? SCATTER_THRESHOLD
            : PROXIMITY_THRESHOLD;
        if (minDistance <= threshold) {
          return closestDataElement;
        }
      }
    }

    // Second: Collect all bbox matches, excluding panels and data elements with points
    const elementMatches: {
      name: string;
      area: number;
      bbox: import("./ElementSelectionTypes.ts").ElementBbox;
    }[] = [];
    const panelMatches: {
      name: string;
      area: number;
      bbox: import("./ElementSelectionTypes.ts").ElementBbox;
    }[] = [];

    for (const [name, value] of Object.entries(bboxes)) {
      if (!isElementBbox(value)) continue;
      const bbox = value;
      if (
        imgX >= bbox.x0 &&
        imgX <= bbox.x1 &&
        imgY >= bbox.y0 &&
        imgY <= bbox.y1
      ) {
        const area = (bbox.x1 - bbox.x0) * (bbox.y1 - bbox.y0);
        const isPanel =
          bbox.is_panel || name.endsWith("_panel") || name === "panel";
        const hasPoints = bbox.points && bbox.points.length > 0;

        if (hasPoints) {
          // Already handled above with proximity
          continue;
        } else if (isPanel) {
          panelMatches.push({ name, area, bbox });
        } else {
          elementMatches.push({ name, area, bbox });
        }
      }
    }

    // Return smallest non-panel element if any
    if (elementMatches.length > 0) {
      elementMatches.sort((a, b) => a.area - b.area);
      return elementMatches[0].name;
    }

    // Fallback to panel selection (useful for multi-panel figures)
    if (panelMatches.length > 0) {
      panelMatches.sort((a, b) => a.area - b.area);
      return panelMatches[0].name;
    }

    return null;
  }

  /**
   * Find all elements at cursor position (for cycle selection)
   */
  public findAllElementsAt(
    bboxes: import("./ElementSelectionTypes.ts").ElementBboxes,
    imgX: number,
    imgY: number,
  ): string[] {
    const results: { name: string; distance: number; priority: number }[] = [];

    for (const [name, value] of Object.entries(bboxes)) {
      if (!isElementBbox(value)) continue;
      const bbox = value;
      let match = false;
      let distance = Infinity;
      let priority = 0; // Lower = more specific

      const hasPoints = bbox.points && bbox.points.length > 0;
      const elementType = bbox.element_type || "";
      const isPanel =
        bbox.is_panel || name.endsWith("_panel") || name === "panel";

      // Check data elements with points (lines, scatter)
      if (hasPoints) {
        if (
          imgX >= bbox.x0 - SCATTER_THRESHOLD &&
          imgX <= bbox.x1 + SCATTER_THRESHOLD &&
          imgY >= bbox.y0 - SCATTER_THRESHOLD &&
          imgY <= bbox.y1 + SCATTER_THRESHOLD
        ) {
          if (elementType === "scatter") {
            distance = this.distanceToNearestPoint(imgX, imgY, bbox.points!);
            if (distance <= SCATTER_THRESHOLD) {
              match = true;
              priority = 1; // Scatter points = high priority
            }
          } else {
            distance = this.distanceToLine(imgX, imgY, bbox.points!);
            if (distance <= PROXIMITY_THRESHOLD) {
              match = true;
              priority = 2; // Lines = high priority
            }
          }
        }
      }

      // Check bbox containment
      if (
        imgX >= bbox.x0 &&
        imgX <= bbox.x1 &&
        imgY >= bbox.y0 &&
        imgY <= bbox.y1
      ) {
        const area = (bbox.x1 - bbox.x0) * (bbox.y1 - bbox.y0);

        if (!match) {
          match = true;
          distance = 0;
        }

        if (isPanel) {
          priority = 100; // Panels = lowest priority
        } else if (!hasPoints) {
          // Small elements like labels, ticks - use area for priority
          priority = 10 + Math.min(area / 10000, 50);
        }
      }

      if (match) {
        results.push({ name, distance, priority });
      }
    }

    // Sort by priority (lower first), then by distance
    results.sort((a, b) => {
      if (a.priority !== b.priority) return a.priority - b.priority;
      return a.distance - b.distance;
    });

    return results.map((r) => r.name);
  }

  /**
   * Distance to nearest point in scatter
   */
  private distanceToNearestPoint(
    px: number,
    py: number,
    points: number[][],
  ): number {
    let minDist = Infinity;
    for (const [x, y] of points) {
      const dist = Math.sqrt((px - x) ** 2 + (py - y) ** 2);
      if (dist < minDist) minDist = dist;
    }
    return minDist;
  }

  /**
   * Distance to nearest line segment
   */
  private distanceToLine(px: number, py: number, points: number[][]): number {
    let minDist = Infinity;
    for (let i = 0; i < points.length - 1; i++) {
      const [x1, y1] = points[i];
      const [x2, y2] = points[i + 1];
      const dist = this.distanceToSegment(px, py, x1, y1, x2, y2);
      if (dist < minDist) minDist = dist;
    }
    return minDist;
  }

  /**
   * Distance from point to line segment
   */
  private distanceToSegment(
    px: number,
    py: number,
    x1: number,
    y1: number,
    x2: number,
    y2: number,
  ): number {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const lenSq = dx * dx + dy * dy;

    if (lenSq === 0) {
      return Math.sqrt((px - x1) ** 2 + (py - y1) ** 2);
    }

    let t = ((px - x1) * dx + (py - y1) * dy) / lenSq;
    t = Math.max(0, Math.min(1, t));

    const projX = x1 + t * dx;
    const projY = y1 + t * dy;

    return Math.sqrt((px - projX) ** 2 + (py - projY) ** 2);
  }

  /**
   * Draw element highlight overlay on an image
   * Delegates to ElementOverlayRenderer for rendering logic.
   */
  public drawElementOverlay(
    ctx: CanvasRenderingContext2D,
    bbox: import("./ElementSelectionTypes.ts").ElementBbox,
    scaleX: number,
    scaleY: number,
    type: "hover" | "selected",
  ): void {
    drawElementOverlay(ctx, bbox, scaleX, scaleY, type);
  }

  /**
   * Get current hovered element
   */
  public getHoveredElement(): string | null {
    return this.hoveredElement;
  }

  /**
   * Get current selected element
   */
  public getSelectedElement(): string | null {
    return this.selectedElement;
  }

  /**
   * Set selected element
   */
  public setSelectedElement(name: string | null): void {
    this.selectedElement = name;
  }

  /**
   * Set hovered element
   */
  public setHoveredElement(name: string | null): void {
    this.hoveredElement = name;
  }

  /**
   * Handle cycle selection (Alt+click or right-click)
   */
  public cycleSelection(
    bboxes: import("./ElementSelectionTypes.ts").ElementBboxes,
    imgX: number,
    imgY: number,
  ): string | null {
    const allElements = this.findAllElementsAt(bboxes, imgX, imgY);

    if (allElements.length > 0) {
      // Check if cursor moved to different location
      if (
        JSON.stringify(allElements) !== JSON.stringify(this.elementsAtCursor)
      ) {
        this.elementsAtCursor = allElements;
        this.currentCycleIndex = 0;
      } else {
        // Cycle to next element
        this.currentCycleIndex =
          (this.currentCycleIndex + 1) % this.elementsAtCursor.length;
      }

      this.selectedElement = this.elementsAtCursor[this.currentCycleIndex];

      const total = this.elementsAtCursor.length;
      const current = this.currentCycleIndex + 1;
      console.log(
        `[ElementSelection] Cycle: ${current}/${total} - ${this.selectedElement}`,
      );

      if (this.statusCallback) {
        const selectedBbox = bboxes[this.selectedElement];
        const label =
          (isElementBbox(selectedBbox) ? selectedBbox.label : null) ||
          this.selectedElement;
        this.statusCallback(`Selected: ${label} (${current}/${total})`);
      }

      return this.selectedElement;
    }

    return null;
  }

  /**
   * Reset cycle state
   */
  public resetCycle(): void {
    this.elementsAtCursor = [];
    this.currentCycleIndex = 0;
  }
}

// Singleton instance
export const elementSelectionManager = new ElementSelectionManager();
