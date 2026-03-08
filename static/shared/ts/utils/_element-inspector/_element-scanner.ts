/**
 * Element Scanner for Element Inspector
 * Scans and visualizes all elements on the page
 *
 * Refactored: Extracted LayerPickerPanel and LabelRenderer for maintainability.
 */

import type { OccupiedPosition } from "./types";
import { DebugInfoCollector } from "./_debug-info-collector";
import { NotificationManager } from "./_notification-manager";
import { LayerPickerPanel } from "./_LayerPickerPanel";
import { LabelRenderer } from "./_LabelRenderer";
import { getDepth, getColorForDepth } from "./_depth-utils";

export class ElementScanner {
  private elementBoxMap: Map<HTMLDivElement, Element> = new Map();
  private currentlyHoveredBox: HTMLDivElement | null = null;
  private currentlyHoveredElement: Element | null = null;
  private debugCollector: DebugInfoCollector;
  private notificationManager: NotificationManager;

  // Extracted managers
  private layerPicker: LayerPickerPanel;
  private labelRenderer: LabelRenderer;

  // Performance: limit max elements per batch (512 = 2^9)
  private static readonly BATCH_SIZE = 512;
  private static readonly MIN_SIZE = 10; // Skip elements smaller than 10px

  // Pagination state
  private currentBatchStart: number = 0;
  private allVisibleElements: Element[] = [];
  private overlayContainerRef: HTMLDivElement | null = null;

  // Overlapped element selection
  private lastCursorX: number = 0;
  private lastCursorY: number = 0;
  private wheelHandler: ((e: WheelEvent) => void) | null = null;
  private directHighlightElement: Element | null = null;

  constructor(
    debugCollector: DebugInfoCollector,
    notificationManager: NotificationManager,
  ) {
    this.debugCollector = debugCollector;
    this.notificationManager = notificationManager;

    // Initialize extracted managers
    this.layerPicker = new LayerPickerPanel(
      debugCollector,
      notificationManager,
      (el) => getDepth(el),
      (depth) => getColorForDepth(depth),
    );
    this.layerPicker.setHighlightCallback((el) => {
      if (this.overlayContainerRef) {
        this.highlightElement(el, this.overlayContainerRef);
      }
    });

    this.labelRenderer = new LabelRenderer(debugCollector, notificationManager);
  }

  public getElementBoxMap(): Map<HTMLDivElement, Element> {
    return this.elementBoxMap;
  }

  /**
   * Get currently selected depth index (from scroll wheel selection)
   */
  public getCurrentDepthIndex(): number {
    return this.layerPicker.getCurrentDepthIndex();
  }

  /**
   * Get elements at the current cursor position (sorted by depth)
   */
  public getElementsAtCursor(): Element[] {
    return this.layerPicker.getElementsAtCursor();
  }

  /**
   * Get the currently selected element (via scroll wheel depth selection)
   */
  public getDepthSelectedElement(): Element | null {
    return (
      this.layerPicker.getSelectedElement() || this.currentlyHoveredElement
    );
  }

  public clearElementBoxMap(): void {
    this.elementBoxMap.clear();
    this.currentlyHoveredBox = null;
    this.currentlyHoveredElement = null;

    // Reset pagination
    this.currentBatchStart = 0;
    this.allVisibleElements = [];
    this.overlayContainerRef = null;

    // Remove wheel handler
    if (this.wheelHandler) {
      document.removeEventListener("wheel", this.wheelHandler);
      this.wheelHandler = null;
    }

    // Reset layer picker
    this.layerPicker.reset();

    // Clear direct highlight
    this.clearDirectHighlight();
  }

  public scanElements(overlayContainer: HTMLDivElement): void {
    this.overlayContainerRef = overlayContainer;

    // First call: collect all visible elements
    if (this.allVisibleElements.length === 0) {
      this.collectVisibleElements();
    }

    // Render first batch
    this.renderBatch(overlayContainer);

    // Setup scroll wheel handler for depth cycling
    this.setupWheelHandler(overlayContainer);
  }

  /**
   * Collect all visible elements (run once on activation)
   */
  private collectVisibleElements(): void {
    const startTime = performance.now();
    const allElements = document.querySelectorAll("*");

    for (const element of allElements) {
      if (!element || !element.tagName) continue;

      // Skip our own overlay elements
      if (element.closest("#element-inspector-overlay")) continue;

      // Skip script, style, and other non-visual elements
      const tagName = element.tagName.toLowerCase();
      if (
        ["script", "style", "link", "meta", "head", "noscript", "br"].includes(
          tagName,
        )
      ) {
        continue;
      }

      // Get bounding rect
      const rect = element.getBoundingClientRect();

      // Skip zero-size and very small elements
      if (
        rect.width < ElementScanner.MIN_SIZE ||
        rect.height < ElementScanner.MIN_SIZE
      ) {
        continue;
      }

      // Quick visibility check
      if (element instanceof HTMLElement) {
        if (
          element.offsetParent === null &&
          tagName !== "body" &&
          tagName !== "html"
        ) {
          if (element.style.display === "none") continue;
        }
      }

      this.allVisibleElements.push(element);
    }

    const elapsed = (performance.now() - startTime).toFixed(1);
    console.log(
      `[ElementInspector] Found ${this.allVisibleElements.length} visible elements in ${elapsed}ms`,
    );
  }

  /**
   * Render current batch of elements
   */
  private renderBatch(overlayContainer: HTMLDivElement): void {
    const startTime = performance.now();
    const fragment = document.createDocumentFragment();
    const occupiedPositions: OccupiedPosition[] = [];

    const scrollY = window.scrollY;
    const scrollX = window.scrollX;

    const batchEnd = Math.min(
      this.currentBatchStart + ElementScanner.BATCH_SIZE,
      this.allVisibleElements.length,
    );

    let count = 0;
    for (let i = this.currentBatchStart; i < batchEnd; i++) {
      const element = this.allVisibleElements[i];
      const rect = element.getBoundingClientRect();

      // Skip elements outside viewport (with margin) for current batch
      const margin = 100;
      if (
        rect.bottom < -margin ||
        rect.top > window.innerHeight + margin ||
        rect.right < -margin ||
        rect.left > window.innerWidth + margin
      ) {
        continue;
      }

      const depth = getDepth(element);
      const color = getColorForDepth(depth);
      const tagName = element.tagName.toLowerCase();

      // Scale border width: thinner for larger elements
      const area = rect.width * rect.height;
      const borderWidth = area > 100000 ? 1 : area > 10000 ? 1.5 : 2;

      const box = document.createElement("div");
      box.className = "element-inspector-box";
      box.style.cssText = `
                top: ${rect.top + scrollY}px;
                left: ${rect.left + scrollX}px;
                width: ${rect.width}px;
                height: ${rect.height}px;
                border-color: ${color};
                border-width: ${borderWidth}px;
            `;

      const id = element.id ? `#${element.id}` : "";
      box.title = `Right-click to copy | Scroll to cycle depth: ${tagName}${id}`;

      this.elementBoxMap.set(box, element);

      box.addEventListener("mouseenter", () => {
        this.currentlyHoveredBox = box;
        this.currentlyHoveredElement = element;
      });

      box.addEventListener("mouseleave", () => {
        if (this.currentlyHoveredBox === box) {
          this.currentlyHoveredBox = null;
          this.currentlyHoveredElement = null;
        }
      });

      // Left click: pass through to underlying element
      box.addEventListener("click", (e: MouseEvent) => {
        // Allow left clicks to pass through by temporarily disabling pointer events
        box.style.pointerEvents = "none";
        const underlyingElement = document.elementFromPoint(
          e.clientX,
          e.clientY,
        );
        box.style.pointerEvents = "";

        if (underlyingElement && underlyingElement !== box) {
          // Create and dispatch a click event to the underlying element
          const clickEvent = new MouseEvent("click", {
            bubbles: true,
            cancelable: true,
            view: window,
            clientX: e.clientX,
            clientY: e.clientY,
          });
          underlyingElement.dispatchEvent(clickEvent);
        }
      });

      // Right-click: copy debug info
      box.addEventListener("contextmenu", async (e: MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();

        const selectedElement = this.currentlyHoveredElement || element;
        const selectedBox = this.currentlyHoveredBox || box;

        selectedBox.classList.add("highlighted");

        const debugInfo =
          this.debugCollector.gatherElementDebugInfo(selectedElement);
        try {
          await navigator.clipboard.writeText(debugInfo);
          this.notificationManager.showNotification("✓ Copied!", "success");
          console.log("[ElementInspector] Copied:", debugInfo);
          this.notificationManager.triggerCopyCallback();
        } catch (err) {
          console.error("[ElementInspector] Copy failed:", err);
          this.notificationManager.showNotification("✗ Copy Failed", "error");
          selectedBox.classList.remove("highlighted");
        }
      });

      const shouldShowLabel = this.labelRenderer.shouldShowLabel(
        element,
        rect,
        depth,
      );

      if (shouldShowLabel) {
        const label = this.labelRenderer.createLabel(element, depth);
        if (label) {
          const labelPos = this.labelRenderer.findLabelPosition(
            rect,
            occupiedPositions,
          );

          if (labelPos.isValid) {
            label.style.top = `${labelPos.top}px`;
            label.style.left = `${labelPos.left}px`;

            this.labelRenderer.addCopyToClipboard(label, element);
            this.labelRenderer.addHoverHighlight(
              label,
              box,
              element,
              (b, e) => {
                this.currentlyHoveredBox = b;
                this.currentlyHoveredElement = e;
              },
            );

            const labelPadding = 8;
            occupiedPositions.push({
              top: labelPos.top - labelPadding,
              left: labelPos.left - labelPadding,
              bottom: labelPos.top + 20 + labelPadding,
              right: labelPos.left + 250 + labelPadding,
            });

            fragment.appendChild(label);
          }
        }
      }

      fragment.appendChild(box);
      count++;
    }

    overlayContainer.appendChild(fragment);

    const elapsed = (performance.now() - startTime).toFixed(1);
    const total = this.allVisibleElements.length;
    const remaining = total - batchEnd;
    console.log(
      `[ElementInspector] Rendered ${count} elements (${this.currentBatchStart + 1}-${batchEnd}/${total}) in ${elapsed}ms` +
        (remaining > 0
          ? ` | Ctrl+I for next ${Math.min(remaining, ElementScanner.BATCH_SIZE)}`
          : ""),
    );

    if (remaining > 0) {
      this.notificationManager.showNotification(
        `${batchEnd}/${total} elements | Ctrl+I for more`,
        "success",
        2000,
      );
    }
  }

  /**
   * Load next batch of elements (called by Ctrl+I)
   */
  public loadNextBatch(): boolean {
    if (!this.overlayContainerRef) return false;

    const total = this.allVisibleElements.length;
    const nextStart = this.currentBatchStart + ElementScanner.BATCH_SIZE;

    if (nextStart >= total) {
      this.notificationManager.showNotification(
        "All elements loaded",
        "success",
      );
      return false;
    }

    this.currentBatchStart = nextStart;
    this.renderBatch(this.overlayContainerRef);
    return true;
  }

  /**
   * Check if more batches are available
   */
  public hasMoreBatches(): boolean {
    return (
      this.currentBatchStart + ElementScanner.BATCH_SIZE <
      this.allVisibleElements.length
    );
  }

  /**
   * Setup scroll wheel handler for cycling through overlapped elements
   */
  private setupWheelHandler(overlayContainer: HTMLDivElement): void {
    this.wheelHandler = (e: WheelEvent) => {
      // Only handle wheel events over the overlay
      if (!overlayContainer.contains(e.target as Node)) return;

      // Check if cursor moved significantly - reset depth index
      const cursorMoved =
        Math.abs(e.clientX - this.lastCursorX) > 5 ||
        Math.abs(e.clientY - this.lastCursorY) > 5;

      if (cursorMoved) {
        this.lastCursorX = e.clientX;
        this.lastCursorY = e.clientY;
        const elements = this.getElementsAtPoint(e.clientX, e.clientY);
        this.layerPicker.show(e.clientX, e.clientY, elements);
      }

      const elements = this.layerPicker.getElementsAtCursor();
      if (elements.length <= 1) {
        this.layerPicker.remove();
        return;
      }

      e.preventDefault();
      e.stopPropagation();

      // Scroll up = shallower (parent), scroll down = deeper (child)
      this.layerPicker.navigate(e.deltaY > 0 ? "down" : "up");
    };

    document.addEventListener("wheel", this.wheelHandler, { passive: false });
  }

  /**
   * Get all elements at a specific point, sorted from deepest to shallowest
   */
  private getElementsAtPoint(x: number, y: number): Element[] {
    const elements: Element[] = [];
    const allAtPoint = document.elementsFromPoint(x, y);

    for (const el of allAtPoint) {
      if (!el || !el.tagName) continue;
      if (el.closest("#element-inspector-overlay")) continue;
      if (el.closest(".element-inspector-layer-picker")) continue;
      const tag = el.tagName.toLowerCase();
      if (["html", "body", "script", "style", "head"].includes(tag)) continue;
      elements.push(el);
    }

    return elements;
  }

  /**
   * Clear direct highlight on element (for elements not in batch)
   */
  private clearDirectHighlight(): void {
    if (this.directHighlightElement instanceof HTMLElement) {
      this.directHighlightElement.style.outline = "";
      this.directHighlightElement.style.outlineOffset = "";
    }
    this.directHighlightElement = null;
  }

  /**
   * Highlight a specific element and update hover state
   */
  private highlightElement(
    element: Element,
    overlayContainer: HTMLDivElement,
  ): void {
    // Clear previous highlights
    overlayContainer
      .querySelectorAll(".element-inspector-box.highlighted")
      .forEach((box) => {
        box.classList.remove("highlighted");
      });
    this.clearDirectHighlight();

    // Try to find the box for this element in rendered batch
    let found = false;
    for (const [box, el] of this.elementBoxMap) {
      if (el === element) {
        box.classList.add("highlighted");
        this.currentlyHoveredBox = box;
        this.currentlyHoveredElement = element;
        found = true;
        break;
      }
    }

    // If element not in batch, highlight it directly on the DOM
    if (!found && element instanceof HTMLElement) {
      element.style.outline = "3px solid #3b82f6";
      element.style.outlineOffset = "2px";
      this.directHighlightElement = element;
      this.currentlyHoveredElement = element;
    }
  }
}
