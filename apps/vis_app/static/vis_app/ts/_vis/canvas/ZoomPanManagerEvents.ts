/**
 * ZoomPanManagerEvents - Event setup for ZoomPanManager
 *
 * Extracted from ZoomPanManager.ts for file-size compliance.
 * Contains the setupEvents function that wires mouse/wheel handlers
 * for zoom and pan on the canvas container.
 */

export interface ZoomPanState {
  canvasZoomLevel: number;
  canvasPanOffset: { x: number; y: number };
  canvasIsPanning: boolean;
  canvasIsZoomDragging: boolean;
  canvasPanStartPoint: { x: number; y: number } | null;
  canvasZoomDragStartY: number;
  canvasZoomDragStartLevel: number;
  canvasWheelThrottleFrame: number | null;
  canvasAccumulatedZoomDelta: number;
  canvasLastZoomMousePos: { x: number; y: number };
  canvasAccumulatedPanDelta: { x: number; y: number };
  canvasDragThrottleFrame: number | null;
  pendingDragUpdate: boolean;
  panThrottleFrame: number | null;
  pendingPanUpdate: { x: number; y: number } | null;
  rightClickPanOccurred: boolean;
}

export interface ZoomPanCallbacks {
  updateCanvasTransform: () => void;
  updateCanvasZoomDisplay: () => void;
  saveViewState: () => void;
  rulersCallback?: () => void;
}

/**
 * Setup zoom/pan event listeners on the canvas container.
 * Mutates the state object directly for performance.
 */
export function setupZoomPanEvents(
  container: HTMLElement,
  state: ZoomPanState,
  callbacks: ZoomPanCallbacks,
): void {
  const DOUBLE_CLICK_THRESHOLD = 300; // ms

  let rightClickPanStartPoint: { x: number; y: number } | null = null;
  let lastRightClickTime = 0;

  // Mouse down - Check for panning or zoom dragging
  container.addEventListener("mousedown", (e: MouseEvent) => {
    if (e.button === 1 || (e as any).spaceKey) {
      if (e.ctrlKey || e.metaKey) {
        // Ctrl + middle mouse = zoom drag mode
        state.canvasIsZoomDragging = true;
        state.canvasZoomDragStartY = e.clientY;
        state.canvasZoomDragStartLevel = state.canvasZoomLevel;
        container.style.cursor = "ns-resize";
        e.preventDefault();
        console.log("[ZoomPanManager] Canvas zoom drag mode started");
      } else {
        // Middle mouse without Ctrl = pan mode
        state.canvasIsPanning = true;
        state.canvasPanStartPoint = { x: e.clientX, y: e.clientY };
        container.style.cursor = "grabbing";
        e.preventDefault();
        console.log("[ZoomPanManager] Canvas pan mode started");
      }
    } else if (e.button === 2) {
      // Right-click - check for double-click to reset canvas position
      const now = Date.now();
      if (now - lastRightClickTime < DOUBLE_CLICK_THRESHOLD) {
        // Double right-click - reset canvas position to origin
        console.log(
          "[ZoomPanManager] Double-right-click: resetting to origin. Current pan:",
          state.canvasPanOffset,
        );
        state.canvasPanOffset.x = 0;
        state.canvasPanOffset.y = 0;
        callbacks.updateCanvasTransform();
        if (callbacks.rulersCallback) {
          callbacks.rulersCallback();
        }
        callbacks.saveViewState();
        state.rightClickPanOccurred = true; // Suppress context menu
        console.log(
          "[ZoomPanManager] Canvas position reset to origin. New pan:",
          state.canvasPanOffset,
        );
        lastRightClickTime = 0; // Reset to prevent triple-click
      } else {
        // Single right-click - prepare for potential pan
        rightClickPanStartPoint = { x: e.clientX, y: e.clientY };
        state.rightClickPanOccurred = false;
        lastRightClickTime = now;
      }
    }
  });

  // Mouse move - Handle panning or zoom dragging
  container.addEventListener("mousemove", (e: MouseEvent) => {
    // Handle right-click pan initiation (detect movement threshold)
    if (rightClickPanStartPoint && !state.canvasIsPanning) {
      const dx = e.clientX - rightClickPanStartPoint.x;
      const dy = e.clientY - rightClickPanStartPoint.y;
      const distance = Math.sqrt(dx * dx + dy * dy);

      // Start panning if moved more than 3 pixels
      if (distance > 3) {
        state.rightClickPanOccurred = true;
        state.canvasIsPanning = true;
        state.canvasPanStartPoint = rightClickPanStartPoint;
        container.style.cursor = "grabbing";
        console.log("[ZoomPanManager] Canvas pan mode started (right-click)");
      }
    }

    if (state.canvasIsZoomDragging) {
      // Ctrl+drag zoom: vertical movement changes zoom
      const deltaY = e.clientY - state.canvasZoomDragStartY;
      const zoomFactor = 1 - deltaY * 0.005;
      let newZoom = state.canvasZoomDragStartLevel * zoomFactor;

      if (newZoom > 5) newZoom = 5;
      if (newZoom < 0.1) newZoom = 0.1;

      state.canvasZoomLevel = newZoom;

      if (!state.pendingDragUpdate) {
        state.pendingDragUpdate = true;
        state.canvasDragThrottleFrame = requestAnimationFrame(() => {
          callbacks.updateCanvasTransform();
          if (callbacks.rulersCallback) {
            callbacks.rulersCallback();
          }
          callbacks.updateCanvasZoomDisplay();
          state.pendingDragUpdate = false;
        });
      }
    } else if (state.canvasIsPanning && state.canvasPanStartPoint) {
      let deltaX = e.clientX - state.canvasPanStartPoint.x;
      let deltaY = e.clientY - state.canvasPanStartPoint.y;

      if (e.altKey) {
        deltaX *= 0.1;
        deltaY *= 0.1;
      }

      if (!state.pendingPanUpdate) {
        state.pendingPanUpdate = { x: deltaX, y: deltaY };
      } else {
        state.pendingPanUpdate.x += deltaX;
        state.pendingPanUpdate.y += deltaY;
      }

      if (!state.panThrottleFrame) {
        state.panThrottleFrame = requestAnimationFrame(() => {
          if (state.pendingPanUpdate) {
            state.canvasPanOffset.x += state.pendingPanUpdate.x;
            state.canvasPanOffset.y += state.pendingPanUpdate.y;

            callbacks.updateCanvasTransform();

            if (callbacks.rulersCallback) {
              callbacks.rulersCallback();
            }

            state.pendingPanUpdate = null;
          }
          state.panThrottleFrame = null;
        });
      }

      state.canvasPanStartPoint = { x: e.clientX, y: e.clientY };
    }
  });

  // Mouse up - Reset panning or zoom dragging
  container.addEventListener("mouseup", (e: MouseEvent) => {
    if (e.button === 2) {
      rightClickPanStartPoint = null;
    }

    if (state.canvasIsZoomDragging) {
      state.canvasIsZoomDragging = false;
      container.style.cursor = "default";
      callbacks.saveViewState();
      console.log("[ZoomPanManager] Canvas zoom drag mode ended");
    }
    if (state.canvasIsPanning) {
      state.canvasIsPanning = false;
      state.canvasPanStartPoint = null;
      container.style.cursor = "default";
      callbacks.saveViewState();
      console.log("[ZoomPanManager] Canvas pan mode ended");
    }

    if (state.canvasDragThrottleFrame !== null) {
      cancelAnimationFrame(state.canvasDragThrottleFrame);
      state.canvasDragThrottleFrame = null;
      state.pendingDragUpdate = false;
    }
    if (state.panThrottleFrame !== null) {
      cancelAnimationFrame(state.panThrottleFrame);
      state.panThrottleFrame = null;
      state.pendingPanUpdate = null;
    }
  });

  // Wheel event - Zoom with Ctrl, Pan without Ctrl
  container.addEventListener(
    "wheel",
    (e: WheelEvent) => {
      e.preventDefault();
      e.stopPropagation();

      if (e.ctrlKey || e.metaKey) {
        // Ctrl+Wheel = Zoom
        state.canvasAccumulatedZoomDelta += e.deltaY;

        const rect = container.getBoundingClientRect();
        state.canvasLastZoomMousePos.x = e.clientX - rect.left;
        state.canvasLastZoomMousePos.y = e.clientY - rect.top;

        if (!state.canvasWheelThrottleFrame) {
          state.canvasWheelThrottleFrame = requestAnimationFrame(() => {
            const oldZoom = state.canvasZoomLevel;
            let newZoom = oldZoom * 0.999 ** state.canvasAccumulatedZoomDelta;

            if (newZoom > 5) newZoom = 5;
            if (newZoom < 0.1) newZoom = 0.1;

            state.canvasZoomLevel = newZoom;

            const zoomRatio = newZoom / oldZoom;
            const mouseX = state.canvasLastZoomMousePos.x;
            const mouseY = state.canvasLastZoomMousePos.y;
            state.canvasPanOffset.x =
              mouseX - (mouseX - state.canvasPanOffset.x) * zoomRatio;
            state.canvasPanOffset.y =
              mouseY - (mouseY - state.canvasPanOffset.y) * zoomRatio;

            callbacks.updateCanvasTransform();
            if (callbacks.rulersCallback) {
              callbacks.rulersCallback();
            }
            callbacks.updateCanvasZoomDisplay();

            state.canvasAccumulatedZoomDelta = 0;
            state.canvasWheelThrottleFrame = null;
          });
        }
      } else {
        // Regular wheel = Pan
        state.canvasAccumulatedPanDelta.x += e.deltaX;
        state.canvasAccumulatedPanDelta.y += e.deltaY;

        if (!state.canvasWheelThrottleFrame) {
          state.canvasWheelThrottleFrame = requestAnimationFrame(() => {
            state.canvasPanOffset.x -= state.canvasAccumulatedPanDelta.x;
            state.canvasPanOffset.y -= state.canvasAccumulatedPanDelta.y;

            callbacks.updateCanvasTransform();
            if (callbacks.rulersCallback) {
              callbacks.rulersCallback();
            }

            state.canvasAccumulatedPanDelta.x = 0;
            state.canvasAccumulatedPanDelta.y = 0;
            state.canvasWheelThrottleFrame = null;
          });
        }
      }
    },
    { passive: false },
  );

  console.log("[ZoomPanManager] Events (zoom/pan) initialized");
}
