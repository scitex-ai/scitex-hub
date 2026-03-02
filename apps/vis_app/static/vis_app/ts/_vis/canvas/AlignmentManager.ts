/**
 * AlignmentManager - Handles object alignment and arrangement operations
 *
 * Responsibilities:
 * - Align objects (left/right/top/bottom/center)
 * - Distribute objects horizontally/vertically
 * - Align plots by axis metadata (Y-axis, X-axis, etc.)
 * - Stack plots vertically with Y-axis alignment
 * - Arrange objects (bring to front/send to back)
 * - Debug axis alignment with visual lines
 *
 * Dependencies:
 * - Requires canvas instance
 * - Requires undo/save callbacks
 * - Requires status bar callback
 */

import {
  alignByAxis as _alignByAxis,
  stackVertically as _stackVertically,
} from "./AlignmentManagerAxisOps";

import {
  showAxisDebugLines as _showAxisDebugLines,
  clearAxisDebugLines as _clearAxisDebugLines,
} from "./AlignmentManagerDebug";

export class AlignmentManager {
  private canvas: any | null = null;

  // Debug lines for axis alignment visualization
  private axisDebugLines: any[] = [];

  constructor(
    private statusBarCallback?: (message: string) => void,
    private saveUndoStateCallback?: () => void,
    private saveCanvasContentCallback?: () => void,
  ) {}

  /**
   * Initialize with canvas instance
   */
  public initialize(canvas: any): void {
    this.canvas = canvas;
  }

  /**
   * Set callbacks for undo/save operations
   */
  public setCallbacks(
    saveUndoState: () => void,
    saveCanvasContent: () => void,
  ): void {
    this.saveUndoStateCallback = saveUndoState;
    this.saveCanvasContentCallback = saveCanvasContent;
  }

  // ========================================
  // ALIGNMENT OPERATIONS
  // ========================================

  /**
   * Align selected objects
   * - Single object: Aligns to canvas (like PowerPoint aligns to slide)
   * - Multiple objects: Aligns objects relative to each other
   */
  public alignObjects(
    alignment: "left" | "right" | "top" | "bottom" | "center-h" | "center-v",
  ): void {
    if (!this.canvas) return;

    const activeObject = this.canvas.getActiveObject();
    if (!activeObject) return;

    this.saveUndoStateCallback?.();

    const alignmentNames: Record<string, string> = {
      left: "Left",
      right: "Right",
      top: "Top",
      bottom: "Bottom",
      "center-h": "Horizontal Center",
      "center-v": "Vertical Center",
    };

    // Single object - align to canvas
    if (activeObject.type !== "activeSelection") {
      const canvasWidth = this.canvas.getWidth();
      const canvasHeight = this.canvas.getHeight();
      const bound = activeObject.getBoundingRect(true);

      switch (alignment) {
        case "left":
          activeObject.set("left", activeObject.left! - bound.left);
          break;
        case "right":
          activeObject.set(
            "left",
            activeObject.left! + (canvasWidth - (bound.left + bound.width)),
          );
          break;
        case "top":
          activeObject.set("top", activeObject.top! - bound.top);
          break;
        case "bottom":
          activeObject.set(
            "top",
            activeObject.top! + (canvasHeight - (bound.top + bound.height)),
          );
          break;
        case "center-h":
          activeObject.set(
            "left",
            activeObject.left! +
              (canvasWidth / 2 - (bound.left + bound.width / 2)),
          );
          break;
        case "center-v":
          activeObject.set(
            "top",
            activeObject.top! +
              (canvasHeight / 2 - (bound.top + bound.height / 2)),
          );
          break;
      }
      activeObject.setCoords();

      this.canvas.renderAll();
      this.saveCanvasContentCallback?.();

      if (this.statusBarCallback) {
        this.statusBarCallback(
          `Aligned to canvas: ${alignmentNames[alignment]}`,
        );
      }
      return;
    }

    // Multiple objects - align relative to each other
    const objects = (activeObject as any).getObjects();
    if (objects.length < 2) return;

    // Calculate bounds of all selected objects
    let minLeft = Infinity,
      maxRight = -Infinity;
    let minTop = Infinity,
      maxBottom = -Infinity;

    objects.forEach((obj: any) => {
      const bound = obj.getBoundingRect(true);
      minLeft = Math.min(minLeft, bound.left);
      maxRight = Math.max(maxRight, bound.left + bound.width);
      minTop = Math.min(minTop, bound.top);
      maxBottom = Math.max(maxBottom, bound.top + bound.height);
    });

    const centerX = (minLeft + maxRight) / 2;
    const centerY = (minTop + maxBottom) / 2;

    objects.forEach((obj: any) => {
      const bound = obj.getBoundingRect(true);

      switch (alignment) {
        case "left":
          obj.set("left", obj.left! - (bound.left - minLeft));
          break;
        case "right":
          obj.set("left", obj.left! + (maxRight - (bound.left + bound.width)));
          break;
        case "top":
          obj.set("top", obj.top! - (bound.top - minTop));
          break;
        case "bottom":
          obj.set("top", obj.top! + (maxBottom - (bound.top + bound.height)));
          break;
        case "center-h":
          obj.set(
            "left",
            obj.left! + (centerX - (bound.left + bound.width / 2)),
          );
          break;
        case "center-v":
          obj.set("top", obj.top! + (centerY - (bound.top + bound.height / 2)));
          break;
      }
      obj.setCoords();
    });

    this.canvas.renderAll();
    this.saveCanvasContentCallback?.();

    if (this.statusBarCallback) {
      this.statusBarCallback(`Aligned: ${alignmentNames[alignment]}`);
    }
  }

  /**
   * Distribute selected objects evenly
   */
  public distributeObjects(direction: "horizontal" | "vertical"): void {
    if (!this.canvas) return;

    const activeObject = this.canvas.getActiveObject();
    if (!activeObject || activeObject.type !== "activeSelection") {
      if (this.statusBarCallback) {
        this.statusBarCallback("Select multiple objects to distribute");
      }
      return;
    }

    const objects = (activeObject as any).getObjects();
    if (objects.length < 3) {
      if (this.statusBarCallback) {
        this.statusBarCallback("Select at least 3 objects to distribute");
      }
      return;
    }

    this.saveUndoStateCallback?.();

    const objectsWithBounds = objects.map((obj: any) => {
      const bound = obj.getBoundingRect(true, true);
      return {
        obj,
        bound,
        centerX: bound.left + bound.width / 2,
        centerY: bound.top + bound.height / 2,
      };
    });

    objectsWithBounds.sort((a: any, b: any) => {
      return direction === "horizontal"
        ? a.centerX - b.centerX
        : a.centerY - b.centerY;
    });

    const first = objectsWithBounds[0];
    const last = objectsWithBounds[objectsWithBounds.length - 1];

    const totalSpace =
      direction === "horizontal"
        ? last.centerX - first.centerX
        : last.centerY - first.centerY;

    const spacing = totalSpace / (objectsWithBounds.length - 1);

    for (let i = 1; i < objectsWithBounds.length - 1; i++) {
      const item = objectsWithBounds[i];
      const obj = item.obj;

      if (direction === "horizontal") {
        const targetCenterX = first.centerX + spacing * i;
        const deltaX = targetCenterX - item.centerX;
        obj.set("left", (obj.left || 0) + deltaX);
      } else {
        const targetCenterY = first.centerY + spacing * i;
        const deltaY = targetCenterY - item.centerY;
        obj.set("top", (obj.top || 0) + deltaY);
      }
      obj.setCoords();
    }

    activeObject.setCoords();

    this.canvas.renderAll();
    this.saveCanvasContentCallback?.();

    if (this.statusBarCallback) {
      this.statusBarCallback(
        `Distributed: ${direction === "horizontal" ? "Horizontally" : "Vertically"}`,
      );
    }
  }

  // ========================================
  // AXIS-BASED ALIGNMENT (FOR SCITEX PLOTS)
  // ========================================

  /**
   * Align by axis with direction support (like regular alignment)
   * @param direction - L=left(Y-axis), C=center-H, R=right, T=top, M=middle-V, B=bottom(X-axis)
   */
  public alignByAxis(direction: "L" | "C" | "R" | "T" | "M" | "B" = "L"): void {
    _alignByAxis(
      this.canvas,
      direction,
      this.saveUndoStateCallback,
      this.saveCanvasContentCallback,
      this.statusBarCallback,
    );
  }

  /**
   * Stack selected plots vertically with Y-axis alignment.
   */
  public stackVertically(): void {
    _stackVertically(
      this.canvas,
      this.saveUndoStateCallback,
      this.saveCanvasContentCallback,
      this.statusBarCallback,
    );
  }

  // ========================================
  // ARRANGEMENT (Z-ORDER)
  // ========================================

  /**
   * Bring active object to front
   */
  public bringToFront(): void {
    if (!this.canvas) return;

    const active = this.canvas.getActiveObject();
    if (active) {
      this.canvas.bringToFront(active);
      this.canvas.renderAll();
      this.saveCanvasContentCallback?.();

      if (this.statusBarCallback) {
        this.statusBarCallback("Brought to front");
      }
    }
  }

  /**
   * Send active object to back
   */
  public sendToBack(): void {
    if (!this.canvas) return;

    const active = this.canvas.getActiveObject();
    if (active) {
      this.canvas.sendToBack(active);
      this.canvas.renderAll();
      this.saveCanvasContentCallback?.();

      if (this.statusBarCallback) {
        this.statusBarCallback("Sent to back");
      }
    }
  }

  /**
   * Arrange object (bring to front or send to back)
   */
  public arrangeObject(action: "front" | "back"): void {
    if (action === "front") {
      this.bringToFront();
    } else {
      this.sendToBack();
    }
  }

  // ========================================
  // DEBUG VISUALIZATION
  // ========================================

  /**
   * Show debug lines indicating axis positions on figures
   * Red = Y-axis (x0), Blue = X-axis (y1), Green = plot bounds
   */
  public showAxisDebugLines(objects?: any[]): void {
    this.axisDebugLines = _showAxisDebugLines(
      this.canvas,
      this.axisDebugLines,
      this.statusBarCallback,
      objects,
    );

    // Auto-clear after 5 seconds
    setTimeout(() => this.clearAxisDebugLines(), 5000);
  }

  /**
   * Clear axis debug lines from canvas
   */
  public clearAxisDebugLines(): void {
    this.axisDebugLines = _clearAxisDebugLines(
      this.canvas,
      this.axisDebugLines,
    );
  }
}
