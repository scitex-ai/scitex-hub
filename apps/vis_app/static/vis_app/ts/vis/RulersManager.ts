/**
 * RulersManager - Handles all ruler rendering, unit toggling, and dragging
 *
 * Responsibilities:
 * - Initialize and draw all four rulers (top, bottom, left, right)
 * - Toggle between mm and inch units
 * - Render ruler markings with appropriate intervals
 * - Handle ruler dragging for canvas panning
 * - Synchronize ruler transform with canvas zoom/pan
 */

import { RulerUnit, CANVAS_CONSTANTS } from "./types.ts";
import {
  generateHorizontalRulerMm,
  generateHorizontalRulerInch,
  generateVerticalRulerMm,
  generateVerticalRulerInch,
} from "./RulerSvgGenerators.ts";

export class RulersManager {
  private rulerUnit: RulerUnit = "mm";
  private canvasZoomLevel: number = 0.22; // Start at 22% to match CanvasManager initial zoom
  private canvasPanOffset: { x: number; y: number } = { x: 0, y: 0 };
  private canvasIsPanning: boolean = false;
  private canvasPanStartPoint: { x: number; y: number } | null = null;
  private isDarkTheme: boolean = false; // Track current theme for rulers
  private onTransformUpdate?: () => void; // Callback to VisEditor for transform sync

  constructor(
    private canvas: any, // Fabric.js canvas instance
    private statusBarCallback?: (message: string) => void,
  ) {}

  /**
   * Set callback for transform updates (called from VisEditor)
   */
  public setTransformCallback(callback: () => void): void {
    this.onTransformUpdate = callback;
  }

  /**
   * Get current ruler unit
   */
  public getRulerUnit(): RulerUnit {
    return this.rulerUnit;
  }

  /**
   * Set canvas zoom level (called from main editor)
   */
  public setCanvasZoomLevel(level: number): void {
    this.canvasZoomLevel = level;
  }

  /**
   * Set canvas pan offset (called from main editor)
   */
  public setCanvasPanOffset(offset: { x: number; y: number }): void {
    this.canvasPanOffset = offset;
  }

  /**
   * Get canvas pan offset (for coordination with other managers)
   */
  public getCanvasPanOffset(): { x: number; y: number } {
    return this.canvasPanOffset;
  }

  /**
   * Get canvas zoom level (for coordination with other managers)
   */
  public getCanvasZoomLevel(): number {
    return this.canvasZoomLevel;
  }

  /**
   * Initialize rulers on canvas load
   */
  public initializeRulers(): void {
    // Rulers follow GLOBAL theme, not canvas theme
    const globalTheme =
      localStorage.getItem("scitex-theme-preference") || "dark";
    this.isDarkTheme = globalTheme === "dark";

    // Draw immediately
    this.drawRulers();

    // Also schedule a redraw after DOM is fully ready (belt and suspenders approach)
    requestAnimationFrame(() => {
      this.drawRulers();
    });
  }

  /**
   * Draw all rulers based on canvas dimensions
   * PERFORMANCE: Pre-rendered SVG instead of 840+ DOM elements
   */
  public drawRulers(): void {
    if (!this.canvas) {
      console.warn("[RulersManager] Cannot draw rulers: canvas not set");
      return;
    }

    const startTime = performance.now();
    const canvasWidth = this.canvas.getWidth();
    const canvasHeight = this.canvas.getHeight();
    const dpi = CANVAS_CONSTANTS.DPI;

    // Validate canvas dimensions
    if (
      !canvasWidth ||
      !canvasHeight ||
      canvasWidth <= 0 ||
      canvasHeight <= 0
    ) {
      console.warn(
        `[RulersManager] Invalid canvas dimensions: ${canvasWidth}x${canvasHeight}, retrying...`,
      );
      // Retry after a short delay
      setTimeout(() => this.drawRulers(), 100);
      return;
    }

    // Check if SVG elements exist
    const rulerH = document.getElementById("ruler-h");
    const rulerV = document.getElementById("ruler-v");
    if (!rulerH || !rulerV) {
      console.warn("[RulersManager] Ruler SVG elements not found, retrying...");
      setTimeout(() => this.drawRulers(), 100);
      return;
    }

    // Render all four rulers with pre-generated SVG
    this.renderHorizontalRuler(canvasWidth, dpi, "ruler-h"); // Top
    this.renderHorizontalRuler(canvasWidth, dpi, "ruler-b"); // Bottom
    this.renderVerticalRuler(canvasHeight, dpi, "ruler-v"); // Left
    this.renderVerticalRuler(canvasHeight, dpi, "ruler-r"); // Right

    // Set up click handlers on ruler labels for unit toggle
    this.setupRulerLabelClickHandlers();

    const endTime = performance.now();
    console.log(
      `[RulersManager] All 4 rulers rendered in ${(endTime - startTime).toFixed(2)}ms (canvas: ${canvasWidth}x${canvasHeight})`,
    );
  }

  /**
   * Set up click handlers on ruler labels for unit toggle
   * Click on any "0mm", "10mm", etc. label to toggle between mm and inch
   */
  private setupRulerLabelClickHandlers(): void {
    const rulerLabels = document.querySelectorAll(".ruler-label");
    rulerLabels.forEach((label) => {
      // Remove existing listener to avoid duplicates
      label.removeEventListener("click", this.handleRulerLabelClick);
      label.addEventListener("click", this.handleRulerLabelClick);
    });
  }

  /**
   * Handle click on ruler label - toggle units
   */
  private handleRulerLabelClick = (e: Event): void => {
    e.stopPropagation();
    this.toggleRulerUnit();
  };

  /**
   * Toggle ruler unit between mm and inch
   */
  public toggleRulerUnit(): void {
    this.rulerUnit = this.rulerUnit === "mm" ? "inch" : "mm";

    // Update button label (if it exists - for backward compatibility)
    const label = document.getElementById("ruler-unit-label");
    if (label) {
      label.textContent = this.rulerUnit;
    }

    // Redraw rulers with new unit
    this.drawRulers();

    console.log(`Ruler unit changed to: ${this.rulerUnit}`);
    if (this.statusBarCallback) {
      this.statusBarCallback(`Ruler units: ${this.rulerUnit}`);
    }
  }

  /**
   * Update ruler theme (light/dark)
   */
  public updateRulerTheme(isDark: boolean): void {
    this.isDarkTheme = isDark;
    this.drawRulers(); // Redraw with new theme colors
    console.log(
      `[RulersManager] Theme updated to ${isDark ? "dark" : "light"}`,
    );
  }

  /**
   * Render horizontal ruler as pre-generated SVG (mm or inch)
   * PERFORMANCE: Generates complete SVG string instead of DOM manipulation
   */
  private renderHorizontalRuler(
    width: number,
    dpi: number,
    rulerId: string = "ruler-h",
  ): void {
    const svg = document.getElementById(rulerId);
    if (!svg) return;

    const rulerHeight = 60;
    svg.setAttribute("width", width.toString());
    svg.setAttribute("height", rulerHeight.toString());
    svg.setAttribute("viewBox", `0 0 ${width} ${rulerHeight}`);
    svg.style.width = `${width}px`;
    svg.style.height = `${rulerHeight}px`;

    // Generate complete SVG content as string using extracted generators
    if (this.rulerUnit === "mm") {
      svg.innerHTML = generateHorizontalRulerMm(
        width,
        dpi,
        rulerHeight,
        this.isDarkTheme,
      );
    } else {
      svg.innerHTML = generateHorizontalRulerInch(
        width,
        dpi,
        rulerHeight,
        this.isDarkTheme,
      );
    }
  }

  /**
   * Render vertical ruler as pre-generated SVG (mm or inch)
   * PERFORMANCE: Generates complete SVG string instead of DOM manipulation
   */
  private renderVerticalRuler(
    height: number,
    dpi: number,
    rulerId: string = "ruler-v",
  ): void {
    const svg = document.getElementById(rulerId);
    if (!svg) return;

    const rulerWidth = 60;
    svg.setAttribute("width", rulerWidth.toString());
    svg.setAttribute("height", height.toString());
    svg.setAttribute("viewBox", `0 0 ${rulerWidth} ${height}`);
    svg.style.width = `${rulerWidth}px`;
    svg.style.height = `${height}px`;

    // Generate complete SVG content as string using extracted generators
    if (this.rulerUnit === "mm") {
      svg.innerHTML = generateVerticalRulerMm(
        height,
        dpi,
        rulerWidth,
        this.isDarkTheme,
      );
    } else {
      svg.innerHTML = generateVerticalRulerInch(
        height,
        dpi,
        rulerWidth,
        this.isDarkTheme,
      );
    }
  }

  /**
   * Setup ruler dragging for canvas panning (transform-based)
   */
  public setupRulerDragging(): void {
    const rulerH = document.getElementById("ruler-h");
    const rulerV = document.getElementById("ruler-v");
    const rulerCorners = document.querySelectorAll(".ruler-corner");

    const rulers = [rulerH, rulerV, ...Array.from(rulerCorners)].filter(
      (r) => r,
    ) as HTMLElement[];

    rulers.forEach((ruler) => {
      ruler.style.cursor = "grab";

      ruler.addEventListener("mousedown", (e) => {
        e.preventDefault();
        this.canvasIsPanning = true;
        this.canvasPanStartPoint = { x: e.clientX, y: e.clientY };
        ruler.style.cursor = "grabbing";
      });

      // Double-click (left) to reset pan position to origin
      ruler.addEventListener("dblclick", (e) => {
        e.preventDefault();
        this.canvasPanOffset.x = 0;
        this.canvasPanOffset.y = 0;
        this.updateRulersAreaTransform();
        console.log("[RulersManager] Pan reset to origin (double-click)");
        if (this.statusBarCallback) {
          this.statusBarCallback("Pan reset to origin");
        }
      });

      // Double right-click to reset pan position to origin (same as left double-click)
      let lastRightClickTime = 0;
      const DOUBLE_CLICK_THRESHOLD = 300; // ms
      ruler.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        const now = Date.now();
        if (now - lastRightClickTime < DOUBLE_CLICK_THRESHOLD) {
          // Double right-click - reset pan
          this.canvasPanOffset.x = 0;
          this.canvasPanOffset.y = 0;
          this.updateRulersAreaTransform();
          console.log(
            "[RulersManager] Pan reset to origin (right double-click)",
          );
          if (this.statusBarCallback) {
            this.statusBarCallback("Pan reset to origin");
          }
          lastRightClickTime = 0;
        } else {
          lastRightClickTime = now;
        }
      });

      ruler.addEventListener("mouseenter", () => {
        if (!this.canvasIsPanning) ruler.style.cursor = "grab";
      });

      ruler.addEventListener("mouseleave", () => {
        if (!this.canvasIsPanning) ruler.style.cursor = "default";
      });
    });

    document.addEventListener("mousemove", (e) => {
      if (this.canvasIsPanning && this.canvasPanStartPoint) {
        let deltaX = e.clientX - this.canvasPanStartPoint.x;
        let deltaY = e.clientY - this.canvasPanStartPoint.y;

        if (e.altKey) {
          deltaX *= 0.1;
          deltaY *= 0.1;
        }

        this.canvasPanOffset.x += deltaX;
        this.canvasPanOffset.y += deltaY;
        this.updateRulersAreaTransform();

        this.canvasPanStartPoint = { x: e.clientX, y: e.clientY };
      }
    });

    document.addEventListener("mouseup", () => {
      if (this.canvasIsPanning) {
        this.canvasIsPanning = false;
        this.canvasPanStartPoint = null;

        rulers.forEach((ruler) => {
          ruler.style.cursor = "grab";
        });
      }
    });

    console.log("[RulersManager] Ruler dragging (transform-based) initialized");
  }

  /**
   * Update transform on the entire rulers area (rulers + canvas together)
   * Uses callback to VisEditor to ensure sync with CanvasManager
   */
  public updateRulersAreaTransform(): void {
    if (this.onTransformUpdate) {
      // Use the callback to let VisEditor handle the transform
      // This ensures sync with CanvasManager's zoom/pan state
      this.onTransformUpdate();
    } else {
      // Fallback to local implementation
      const rulersArea = document.querySelector(
        ".vis-rulers-area",
      ) as HTMLElement;
      if (rulersArea) {
        rulersArea.style.transform = `translate(${this.canvasPanOffset.x}px, ${this.canvasPanOffset.y}px) scale(${this.canvasZoomLevel})`;
        rulersArea.style.transformOrigin = "top left";
      }
    }
  }

  /**
   * Reset pan offset to origin and notify CanvasManager
   */
  public resetPanToOrigin(): void {
    this.canvasPanOffset.x = 0;
    this.canvasPanOffset.y = 0;
  }
}
