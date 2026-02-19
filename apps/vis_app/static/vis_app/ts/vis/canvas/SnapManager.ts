/**
 * SnapManager - Handles object snapping and alignment guidelines
 *
 * Responsibilities:
 * - Toggle snap functionality on/off
 * - Handle object snapping while moving
 * - Snap to canvas edges and center
 * - Snap to other objects
 * - Snap to axis positions (for SciTeX plots)
 * - Draw alignment guidelines using CSS overlays
 * - Track Alt key for temporary snap disable
 *
 * Dependencies:
 * - Requires canvas instance
 * - Requires zoom/pan information
 * - Requires status bar callback
 */

import { snapToAxisPositions as _snapToAxisPositions } from "./SnapManagerAxisSnap.ts";

export class SnapManager {
  private canvas: any | null = null;

  // Snap state
  private snapEnabled: boolean = true;
  private snapThreshold: number = 10;

  // Guideline overlay (CSS-based for performance)
  private guidelineOverlay: HTMLDivElement | null = null;

  // Track last snap state to prevent oscillation
  private lastSnapX: { guide: number; type: string } | null = null;
  private lastSnapY: { guide: number; type: string } | null = null;

  // Track if Alt key is pressed (for fine adjustment mode - disables snap)
  private altKeyPressed: boolean = false;

  constructor(
    private statusBarCallback?: (message: string) => void,
    private getZoomLevel?: () => number,
    private getPanOffset?: () => { x: number; y: number },
  ) {}

  /**
   * Initialize with canvas instance
   */
  public initialize(canvas: any): void {
    this.canvas = canvas;
    this.setupAltKeyTracking();
  }

  /**
   * Set callbacks for zoom/pan information
   */
  public setCallbacks(
    getZoomLevel: () => number,
    getPanOffset: () => { x: number; y: number },
  ): void {
    this.getZoomLevel = getZoomLevel;
    this.getPanOffset = getPanOffset;
  }

  // ========================================
  // SNAP TOGGLE
  // ========================================

  /**
   * Toggle snap functionality
   */
  public toggleSnap(): void {
    this.snapEnabled = !this.snapEnabled;
    if (this.statusBarCallback) {
      this.statusBarCallback(
        `Snap ${this.snapEnabled ? "enabled" : "disabled"}`,
      );
    }
    console.log(
      `[SnapManager] Snap ${this.snapEnabled ? "enabled" : "disabled"}`,
    );
  }

  /**
   * Check if snap is enabled
   */
  public isSnapEnabled(): boolean {
    return this.snapEnabled;
  }

  // ========================================
  // GUIDELINE OVERLAY INITIALIZATION
  // ========================================

  /**
   * Initialize guideline overlay (CSS-based for performance)
   */
  public initGuidelineOverlay(): void {
    if (this.guidelineOverlay) return;

    const canvasContainer = document.getElementById("canvas-container");
    if (!canvasContainer) return;

    this.guidelineOverlay = document.createElement("div");
    this.guidelineOverlay.id = "snap-guideline-overlay";
    this.guidelineOverlay.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1000;
            overflow: hidden;
        `;
    canvasContainer.appendChild(this.guidelineOverlay);
  }

  // ========================================
  // ALT KEY TRACKING
  // ========================================

  /**
   * Setup Alt key tracking for fine adjustment mode
   */
  public setupAltKeyTracking(): void {
    document.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.altKey && !this.altKeyPressed) {
        this.altKeyPressed = true;
        this.clearAlignmentLines();
      }
    });
    document.addEventListener("keyup", (e: KeyboardEvent) => {
      if (!e.altKey && this.altKeyPressed) {
        this.altKeyPressed = false;
      }
    });
    window.addEventListener("blur", () => {
      this.altKeyPressed = false;
    });
  }

  // ========================================
  // SNAP HANDLING
  // ========================================

  /**
   * Handle object snapping while moving (OPTIMIZED)
   * Uses CSS overlay instead of Fabric.js lines for better performance
   * Includes hysteresis to prevent snap oscillation/fluctuation
   * Hold Alt to temporarily disable snap for fine adjustment
   */
  public handleObjectSnap(target: any): void {
    if (!this.canvas || !target) return;

    if (this.altKeyPressed) {
      this.clearAlignmentLines();
      this.lastSnapX = null;
      this.lastSnapY = null;
      return;
    }

    if (!this.guidelineOverlay) {
      this.initGuidelineOverlay();
    }

    const bound = target.getBoundingRect(true);
    const canvasWidth = this.canvas.getWidth();
    const canvasHeight = this.canvas.getHeight();
    const threshold = this.snapThreshold;

    const zoom = this.getZoomLevel?.() || 1;
    const panOffset = this.getPanOffset?.() || { x: 0, y: 0 };
    const panX = panOffset.x;
    const panY = panOffset.y;

    const movingLeft = bound.left;
    const movingRight = bound.left + bound.width;
    const movingCenterX = bound.left + bound.width / 2;
    const movingTop = bound.top;
    const movingBottom = bound.top + bound.height;
    const movingCenterY = bound.top + bound.height / 2;

    let snapX: number | null = null;
    let snapY: number | null = null;
    let guideX: number | null = null;
    let guideY: number | null = null;
    let snapTypeX: string | null = null;
    let snapTypeY: string | null = null;

    // === SNAP TO CANVAS EDGES AND CENTER ===
    if (Math.abs(movingLeft) < threshold) {
      snapX = target.left! - movingLeft;
      guideX = 0;
      snapTypeX = "L";
    } else if (Math.abs(movingRight - canvasWidth) < threshold) {
      snapX = target.left! + (canvasWidth - movingRight);
      guideX = canvasWidth;
      snapTypeX = "R";
    } else if (Math.abs(movingCenterX - canvasWidth / 2) < threshold) {
      snapX = target.left! + (canvasWidth / 2 - movingCenterX);
      guideX = canvasWidth / 2;
      snapTypeX = "C";
    }

    if (Math.abs(movingTop) < threshold) {
      snapY = target.top! - movingTop;
      guideY = 0;
      snapTypeY = "T";
    } else if (Math.abs(movingBottom - canvasHeight) < threshold) {
      snapY = target.top! + (canvasHeight - movingBottom);
      guideY = canvasHeight;
      snapTypeY = "B";
    } else if (Math.abs(movingCenterY - canvasHeight / 2) < threshold) {
      snapY = target.top! + (canvasHeight / 2 - movingCenterY);
      guideY = canvasHeight / 2;
      snapTypeY = "C";
    }

    // === SNAP TO OTHER OBJECTS ===
    if (snapX === null || snapY === null) {
      const objects = this.canvas.getObjects();
      for (let i = 0; i < objects.length; i++) {
        const obj = objects[i];
        if (
          obj === target ||
          obj.isAlignmentLine ||
          obj.id === "grid-line" ||
          obj.id === "column-guide"
        )
          continue;

        const objBound = obj.getBoundingRect(true);
        const objLeft = objBound.left;
        const objRight = objBound.left + objBound.width;
        const objCenterX = objBound.left + objBound.width / 2;
        const objTop = objBound.top;
        const objBottom = objBound.top + objBound.height;
        const objCenterY = objBound.top + objBound.height / 2;

        if (snapX === null) {
          if (Math.abs(movingLeft - objLeft) < threshold) {
            snapX = target.left! + (objLeft - movingLeft);
            guideX = objLeft;
            snapTypeX = "L";
          } else if (Math.abs(movingRight - objRight) < threshold) {
            snapX = target.left! + (objRight - movingRight);
            guideX = objRight;
            snapTypeX = "R";
          } else if (Math.abs(movingLeft - objRight) < threshold) {
            snapX = target.left! + (objRight - movingLeft);
            guideX = objRight;
            snapTypeX = "R";
          } else if (Math.abs(movingRight - objLeft) < threshold) {
            snapX = target.left! + (objLeft - movingRight);
            guideX = objLeft;
            snapTypeX = "L";
          } else if (Math.abs(movingCenterX - objCenterX) < threshold) {
            snapX = target.left! + (objCenterX - movingCenterX);
            guideX = objCenterX;
            snapTypeX = "C";
          }
        }

        if (snapY === null) {
          if (Math.abs(movingTop - objTop) < threshold) {
            snapY = target.top! + (objTop - movingTop);
            guideY = objTop;
            snapTypeY = "T";
          } else if (Math.abs(movingBottom - objBottom) < threshold) {
            snapY = target.top! + (objBottom - movingBottom);
            guideY = objBottom;
            snapTypeY = "B";
          } else if (Math.abs(movingTop - objBottom) < threshold) {
            snapY = target.top! + (objBottom - movingTop);
            guideY = objBottom;
            snapTypeY = "B";
          } else if (Math.abs(movingBottom - objTop) < threshold) {
            snapY = target.top! + (objTop - movingBottom);
            guideY = objTop;
            snapTypeY = "T";
          } else if (Math.abs(movingCenterY - objCenterY) < threshold) {
            snapY = target.top! + (objCenterY - movingCenterY);
            guideY = objCenterY;
            snapTypeY = "C";
          }
        }

        if (snapX !== null && snapY !== null) break;
      }
    }

    // === SNAP TO AXIS POSITIONS ===
    if (snapX === null || snapY === null) {
      const axisSnapResult = _snapToAxisPositions(
        this.canvas,
        target,
        bound,
        threshold,
      );
      if (axisSnapResult.snapX !== null && snapX === null) {
        snapX = axisSnapResult.snapX;
        guideX = axisSnapResult.guideX;
        snapTypeX = axisSnapResult.typeX;
      }
      if (axisSnapResult.snapY !== null && snapY === null) {
        snapY = axisSnapResult.snapY;
        guideY = axisSnapResult.guideY;
        snapTypeY = axisSnapResult.typeY;
      }
    }

    // === HYSTERESIS ===
    if (snapX !== null && guideX !== null && snapTypeX !== null) {
      if (
        this.lastSnapX &&
        this.lastSnapX.guide === guideX &&
        this.lastSnapX.type === snapTypeX
      ) {
        // Same as last snap - keep it
      } else {
        this.lastSnapX = { guide: guideX, type: snapTypeX };
      }
    } else {
      this.lastSnapX = null;
    }

    if (snapY !== null && guideY !== null && snapTypeY !== null) {
      if (
        this.lastSnapY &&
        this.lastSnapY.guide === guideY &&
        this.lastSnapY.type === snapTypeY
      ) {
        // Same as last snap - keep it
      } else {
        this.lastSnapY = { guide: guideY, type: snapTypeY };
      }
    } else {
      this.lastSnapY = null;
    }

    if (snapX !== null) target.set("left", snapX);
    if (snapY !== null) target.set("top", snapY);

    this.drawGuidelinesCSS(
      guideX,
      guideY,
      canvasWidth,
      canvasHeight,
      zoom,
      panX,
      panY,
      snapTypeX,
      snapTypeY,
      bound,
    );
  }

  /**
   * Snap to axis positions of other plots
   */
  public snapToAxisPositions(
    target: any,
    targetBound: any,
    threshold: number,
  ): {
    snapX: number | null;
    snapY: number | null;
    guideX: number | null;
    guideY: number | null;
    typeX: string | null;
    typeY: string | null;
  } {
    return _snapToAxisPositions(this.canvas, target, targetBound, threshold);
  }

  // ========================================
  // GUIDELINE DRAWING
  // ========================================

  /**
   * Draw guidelines using CSS (optimized - no Fabric.js overhead)
   */
  public drawGuidelinesCSS(
    guideX: number | null,
    guideY: number | null,
    canvasWidth: number,
    canvasHeight: number,
    zoom: number,
    panX: number,
    panY: number,
    snapTypeX: string | null = null,
    snapTypeY: string | null = null,
    objectBound: any = null,
  ): void {
    if (!this.guidelineOverlay) return;

    const edgeColor = "#ff6b6b";
    const axisColor = "#00bcd4";

    const objCenterY = objectBound
      ? (objectBound.top + objectBound.height / 2) * zoom + panY
      : 50;
    const objCenterX = objectBound
      ? (objectBound.left + objectBound.width / 2) * zoom + panX
      : 50;

    let html = "";

    if (guideX !== null && snapTypeX) {
      const screenX = guideX * zoom + panX;
      const isAxisSnap = snapTypeX === "Y";
      const color = isAxisSnap ? axisColor : edgeColor;
      const width = isAxisSnap ? 2 : 1;

      html += `<div style="position:absolute;left:${screenX}px;top:0;width:${width}px;height:100%;background:${color};opacity:0.9;"></div>`;
      const labelStyle = `position:absolute;left:${screenX + 4}px;top:${objCenterY}px;color:${color};font-size:11px;font-weight:bold;text-shadow:0 0 3px #000,0 0 3px #000;padding:2px 4px;border-radius:2px;`;
      html += `<div style="${labelStyle}">${snapTypeX}</div>`;
    }

    if (guideY !== null && snapTypeY) {
      const screenY = guideY * zoom + panY;
      const isAxisSnap = snapTypeY === "X";
      const color = isAxisSnap ? axisColor : edgeColor;
      const width = isAxisSnap ? 2 : 1;

      html += `<div style="position:absolute;left:0;top:${screenY}px;width:100%;height:${width}px;background:${color};opacity:0.9;"></div>`;
      const labelStyle = `position:absolute;left:${objCenterX}px;top:${screenY + 4}px;color:${color};font-size:11px;font-weight:bold;text-shadow:0 0 3px #000,0 0 3px #000;padding:2px 4px;border-radius:2px;`;
      html += `<div style="${labelStyle}">${snapTypeY}</div>`;
    }

    this.guidelineOverlay.innerHTML = html;
  }

  /**
   * Clear alignment guidelines
   */
  public clearAlignmentLines(): void {
    if (this.guidelineOverlay) {
      this.guidelineOverlay.innerHTML = "";
    }
  }

  /**
   * Reset snap state (call when mouse is released)
   */
  public resetSnapState(): void {
    this.lastSnapX = null;
    this.lastSnapY = null;
  }
}
