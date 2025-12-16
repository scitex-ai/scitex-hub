/**
 * Element Scanner for Element Inspector
 * Scans and visualizes all elements on the page
 */

import type { LabelPosition, OccupiedPosition } from "./types";
import { DebugInfoCollector } from "./debug-info-collector";
import { NotificationManager } from "./notification-manager";

export class ElementScanner {
  private elementBoxMap: Map<HTMLDivElement, Element> = new Map();
  private currentlyHoveredBox: HTMLDivElement | null = null;
  private currentlyHoveredElement: Element | null = null;
  private debugCollector: DebugInfoCollector;
  private notificationManager: NotificationManager;

  // Performance: limit max elements per batch (512 = 2^9)
  private static readonly BATCH_SIZE = 512;
  private static readonly MIN_SIZE = 10; // Skip elements smaller than 10px

  // Pagination state
  private currentBatchStart: number = 0;
  private allVisibleElements: Element[] = [];
  private overlayContainerRef: HTMLDivElement | null = null;

  // Overlapped element selection
  private elementsAtCursor: Element[] = [];
  private currentDepthIndex: number = 0;
  private lastCursorX: number = 0;
  private lastCursorY: number = 0;
  private wheelHandler: ((e: WheelEvent) => void) | null = null;
  private layerPickerPanel: HTMLDivElement | null = null;
  private directHighlightElement: Element | null = null; // For elements not in batch

  constructor(
    debugCollector: DebugInfoCollector,
    notificationManager: NotificationManager,
  ) {
    this.debugCollector = debugCollector;
    this.notificationManager = notificationManager;
  }

  public getElementBoxMap(): Map<HTMLDivElement, Element> {
    return this.elementBoxMap;
  }

  /**
   * Get currently selected depth index (from scroll wheel selection)
   */
  public getCurrentDepthIndex(): number {
    return this.currentDepthIndex;
  }

  /**
   * Get elements at the current cursor position (sorted by depth)
   */
  public getElementsAtCursor(): Element[] {
    return this.elementsAtCursor;
  }

  /**
   * Get the currently selected element (via scroll wheel depth selection)
   */
  public getDepthSelectedElement(): Element | null {
    if (this.elementsAtCursor.length > 0 && this.currentDepthIndex < this.elementsAtCursor.length) {
      return this.elementsAtCursor[this.currentDepthIndex];
    }
    return this.currentlyHoveredElement;
  }

  public clearElementBoxMap(): void {
    this.elementBoxMap.clear();
    this.currentlyHoveredBox = null;
    this.currentlyHoveredElement = null;
    this.elementsAtCursor = [];
    this.currentDepthIndex = 0;

    // Reset pagination
    this.currentBatchStart = 0;
    this.allVisibleElements = [];
    this.overlayContainerRef = null;

    // Remove wheel handler
    if (this.wheelHandler) {
      document.removeEventListener("wheel", this.wheelHandler);
      this.wheelHandler = null;
    }

    // Remove layer picker panel
    this.removeLayerPickerPanel();

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
      // Skip our own overlay elements
      if (element.closest("#element-inspector-overlay")) continue;

      // Skip script, style, and other non-visual elements
      const tagName = element.tagName.toLowerCase();
      if (["script", "style", "link", "meta", "head", "noscript", "br"].includes(tagName)) {
        continue;
      }

      // Get bounding rect
      const rect = element.getBoundingClientRect();

      // Skip zero-size and very small elements
      if (rect.width < ElementScanner.MIN_SIZE || rect.height < ElementScanner.MIN_SIZE) {
        continue;
      }

      // Quick visibility check
      if (element instanceof HTMLElement) {
        if (element.offsetParent === null && tagName !== "body" && tagName !== "html") {
          if (element.style.display === "none") continue;
        }
      }

      this.allVisibleElements.push(element);
    }

    const elapsed = (performance.now() - startTime).toFixed(1);
    console.log(`[ElementInspector] Found ${this.allVisibleElements.length} visible elements in ${elapsed}ms`);
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
      this.allVisibleElements.length
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

      const depth = this.getDepth(element);
      const color = this.getColorForDepth(depth);
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
        const underlyingElement = document.elementFromPoint(e.clientX, e.clientY);
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

        const debugInfo = this.debugCollector.gatherElementDebugInfo(selectedElement);
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

      const shouldShowLabel = this.shouldShowLabel(element, rect, depth);

      if (shouldShowLabel) {
        const label = this.createLabel(element, depth);
        if (label) {
          const labelPos = this.findLabelPosition(rect, occupiedPositions);

          if (labelPos.isValid) {
            label.style.top = `${labelPos.top}px`;
            label.style.left = `${labelPos.left}px`;

            this.addCopyToClipboard(label, element);
            this.addHoverHighlight(label, box, element);

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
      (remaining > 0 ? ` | Ctrl+I for next ${Math.min(remaining, ElementScanner.BATCH_SIZE)}` : "")
    );

    if (remaining > 0) {
      this.notificationManager.showNotification(
        `${batchEnd}/${total} elements | Ctrl+I for more`,
        "success",
        2000
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
      this.notificationManager.showNotification("All elements loaded", "success");
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
    return this.currentBatchStart + ElementScanner.BATCH_SIZE < this.allVisibleElements.length;
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
        this.elementsAtCursor = this.getElementsAtPoint(e.clientX, e.clientY);
        this.currentDepthIndex = 0;
        // Show layer picker panel at new position
        this.showLayerPickerPanel(e.clientX, e.clientY);
      }

      if (this.elementsAtCursor.length <= 1) {
        this.removeLayerPickerPanel();
        return;
      }

      e.preventDefault();
      e.stopPropagation();

      // Scroll up = shallower (parent), scroll down = deeper (child)
      if (e.deltaY > 0) {
        this.currentDepthIndex = Math.min(
          this.currentDepthIndex + 1,
          this.elementsAtCursor.length - 1
        );
      } else {
        this.currentDepthIndex = Math.max(this.currentDepthIndex - 1, 0);
      }

      const selectedElement = this.elementsAtCursor[this.currentDepthIndex];
      this.highlightElement(selectedElement, overlayContainer);
      this.updateLayerPickerSelection();
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
      if (el.closest("#element-inspector-overlay")) continue;
      if (el.closest(".element-inspector-layer-picker")) continue;
      const tag = el.tagName.toLowerCase();
      if (["html", "body", "script", "style", "head"].includes(tag)) continue;
      elements.push(el);
    }

    return elements;
  }

  /**
   * Show layer picker panel with stacked element list
   */
  private showLayerPickerPanel(x: number, y: number): void {
    this.removeLayerPickerPanel();

    if (this.elementsAtCursor.length <= 1) return;

    const panel = document.createElement("div");
    panel.className = "element-inspector-layer-picker";
    panel.tabIndex = 0; // Make focusable for keyboard navigation
    panel.style.cssText = `
      position: fixed;
      top: ${Math.min(y + 10, window.innerHeight - 300)}px;
      left: ${Math.min(x + 15, window.innerWidth - 220)}px;
      background: rgba(30, 30, 30, 0.95);
      border: 1px solid rgba(100, 100, 100, 0.5);
      border-radius: 6px;
      padding: 6px 0;
      min-width: 200px;
      max-height: 280px;
      overflow-y: auto;
      z-index: 10000001;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace;
      font-size: 11px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
      outline: none;
    `;

    // Header
    const header = document.createElement("div");
    header.style.cssText = `
      padding: 4px 10px 6px;
      color: #888;
      border-bottom: 1px solid rgba(100, 100, 100, 0.3);
      margin-bottom: 4px;
      font-size: 10px;
    `;
    header.textContent = `${this.elementsAtCursor.length} layers (↑↓/Tab + Enter)`;
    panel.appendChild(header);

    // Add keyboard navigation handler
    this.setupLayerPickerKeyboard(panel);

    // Element list
    this.elementsAtCursor.forEach((el, index) => {
      const item = document.createElement("div");
      item.dataset.index = String(index);
      item.style.cssText = `
        padding: 5px 10px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 6px;
        transition: background 0.1s;
      `;

      // Depth indicator (visual bar)
      const depthBar = document.createElement("span");
      const depth = this.getDepth(el);
      depthBar.style.cssText = `
        width: ${Math.min(depth * 3, 30)}px;
        height: 3px;
        background: ${this.getColorForDepth(depth)};
        border-radius: 2px;
        flex-shrink: 0;
      `;

      // Index number
      const indexNum = document.createElement("span");
      indexNum.style.cssText = `color: #666; width: 18px; text-align: right;`;
      indexNum.textContent = `${index + 1}`;

      // Element info
      const info = document.createElement("span");
      const tag = el.tagName.toLowerCase();
      const id = el.id ? `#${el.id}` : "";
      const cls = el.className && typeof el.className === "string"
        ? `.${el.className.split(" ")[0].substring(0, 15)}`
        : "";
      info.innerHTML = `<span style="color:#61afef">${tag}</span><span style="color:#e5c07b">${id}</span><span style="color:#98c379">${cls}</span>`;
      info.style.cssText = `overflow: hidden; text-overflow: ellipsis; white-space: nowrap;`;

      item.appendChild(depthBar);
      item.appendChild(indexNum);
      item.appendChild(info);

      item.addEventListener("mouseenter", () => {
        item.style.background = "rgba(100, 100, 100, 0.3)";
      });
      item.addEventListener("mouseleave", () => {
        if (this.currentDepthIndex !== index) {
          item.style.background = "";
        }
      });
      item.addEventListener("click", () => {
        this.currentDepthIndex = index;
        this.highlightElement(el, this.overlayContainerRef!);
        this.updateLayerPickerSelection();
      });

      panel.appendChild(item);
    });

    document.body.appendChild(panel);
    this.layerPickerPanel = panel;
    this.updateLayerPickerSelection();

    // Auto-focus panel for keyboard navigation
    setTimeout(() => panel.focus(), 10);
  }

  /**
   * Setup keyboard navigation for layer picker panel
   */
  private setupLayerPickerKeyboard(panel: HTMLDivElement): void {
    panel.addEventListener("keydown", async (e: KeyboardEvent) => {
      const maxIndex = this.elementsAtCursor.length - 1;

      switch (e.key) {
        case "ArrowDown":
        case "Tab":
          if (!e.shiftKey) {
            e.preventDefault();
            e.stopPropagation();
            this.currentDepthIndex = Math.min(this.currentDepthIndex + 1, maxIndex);
            this.highlightElement(this.elementsAtCursor[this.currentDepthIndex], this.overlayContainerRef!);
            this.updateLayerPickerSelection();
          } else if (e.key === "Tab") {
            // Shift+Tab = go up
            e.preventDefault();
            e.stopPropagation();
            this.currentDepthIndex = Math.max(this.currentDepthIndex - 1, 0);
            this.highlightElement(this.elementsAtCursor[this.currentDepthIndex], this.overlayContainerRef!);
            this.updateLayerPickerSelection();
          }
          break;

        case "ArrowUp":
          e.preventDefault();
          e.stopPropagation();
          this.currentDepthIndex = Math.max(this.currentDepthIndex - 1, 0);
          this.highlightElement(this.elementsAtCursor[this.currentDepthIndex], this.overlayContainerRef!);
          this.updateLayerPickerSelection();
          break;

        case "Enter":
          e.preventDefault();
          e.stopPropagation();
          await this.confirmLayerSelection();
          break;

        case "Escape":
          e.preventDefault();
          e.stopPropagation();
          this.removeLayerPickerPanel();
          break;
      }
    });
  }

  /**
   * Confirm current layer selection (copy debug info)
   */
  private async confirmLayerSelection(): Promise<void> {
    if (this.elementsAtCursor.length === 0) return;

    const selectedElement = this.elementsAtCursor[this.currentDepthIndex];
    if (!selectedElement) return;

    const debugInfo = this.debugCollector.gatherElementDebugInfo(selectedElement);

    try {
      await navigator.clipboard.writeText(debugInfo);
      this.notificationManager.showNotification("✓ Copied!", "success");
      console.log("[ElementInspector] Copied debug info to clipboard");

      // Trigger auto-dismiss (ESC) after copy
      this.notificationManager.triggerCopyCallback();
    } catch (err) {
      console.error("[ElementInspector] Failed to copy:", err);
      this.notificationManager.showNotification("✗ Copy Failed", "error");
    }
  }

  /**
   * Update layer picker panel selection highlight
   */
  private updateLayerPickerSelection(): void {
    if (!this.layerPickerPanel) return;

    const items = this.layerPickerPanel.querySelectorAll("[data-index]");
    items.forEach((item, index) => {
      const el = item as HTMLElement;
      if (index === this.currentDepthIndex) {
        el.style.background = "rgba(59, 130, 246, 0.4)";
        el.style.borderLeft = "2px solid #3b82f6";
        el.scrollIntoView({ block: "nearest" });
      } else {
        el.style.background = "";
        el.style.borderLeft = "";
      }
    });
  }

  /**
   * Remove layer picker panel
   */
  private removeLayerPickerPanel(): void {
    if (this.layerPickerPanel) {
      this.layerPickerPanel.remove();
      this.layerPickerPanel = null;
    }
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
  private highlightElement(element: Element, overlayContainer: HTMLDivElement): void {
    // Clear previous highlights
    overlayContainer.querySelectorAll(".element-inspector-box.highlighted").forEach((box) => {
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

  private shouldShowLabel(
    element: Element,
    rect: DOMRect,
    depth: number,
  ): boolean {
    // Criteria for showing labels (SPARSE mode):

    // 1. Element has an ID - always show
    if (element.id) {
      return rect.width > 20 && rect.height > 20;
    }

    // 2. Large elements (100px+) - show
    if (rect.width > 100 || rect.height > 100) {
      return true;
    }

    // 3. Important semantic elements - show if medium sized
    const importantTags = [
      "header",
      "nav",
      "main",
      "section",
      "article",
      "aside",
      "footer",
      "form",
      "table",
    ];
    if (
      importantTags.includes(element.tagName.toLowerCase()) &&
      (rect.width > 50 || rect.height > 50)
    ) {
      return true;
    }

    // 4. Interactive elements with decent size
    const interactiveTags = ["button", "a", "input", "select", "textarea"];
    if (
      interactiveTags.includes(element.tagName.toLowerCase()) &&
      (rect.width > 30 || rect.height > 30)
    ) {
      return true;
    }

    // 5. Skip deeply nested small elements
    if (depth > 8 && rect.width < 100 && rect.height < 100) {
      return false;
    }

    // Default: don't show for small elements
    return false;
  }

  private findLabelPosition(
    rect: DOMRect,
    occupiedPositions: OccupiedPosition[],
  ): LabelPosition {
    const scrollY = window.scrollY;
    const scrollX = window.scrollX;

    // Try different positions in order of preference
    const positions = [
      { top: rect.top + scrollY - 24, left: rect.left + scrollX },
      { top: rect.top + scrollY - 24, left: rect.right + scrollX - 200 },
      { top: rect.top + scrollY + 4, left: rect.left + scrollX + 4 },
      { top: rect.top + scrollY + 4, left: rect.right + scrollX - 204 },
      { top: rect.bottom + scrollY + 4, left: rect.left + scrollX },
      { top: rect.bottom + scrollY + 4, left: rect.right + scrollX - 200 },
      {
        top: rect.top + scrollY + rect.height / 2 - 10,
        left: rect.left + scrollX - 210,
      },
      {
        top: rect.top + scrollY + rect.height / 2 - 10,
        left: rect.right + scrollX + 10,
      },
      { top: rect.top + scrollY - 48, left: rect.left + scrollX },
      { top: rect.bottom + scrollY + 28, left: rect.left + scrollX },
    ];

    // Find first non-overlapping position
    for (const pos of positions) {
      if (!this.isPositionOccupied(pos, occupiedPositions)) {
        return { ...pos, isValid: true };
      }
    }

    // If all positions are occupied, don't show this label
    return { top: 0, left: 0, isValid: false };
  }

  private isPositionOccupied(
    pos: { top: number; left: number },
    occupiedPositions: OccupiedPosition[],
  ): boolean {
    const labelWidth = 250;
    const labelHeight = 20;

    for (const occupied of occupiedPositions) {
      // Check if rectangles overlap
      if (
        !(
          pos.left + labelWidth < occupied.left ||
          pos.left > occupied.right ||
          pos.top + labelHeight < occupied.top ||
          pos.top > occupied.bottom
        )
      ) {
        return true;
      }
    }
    return false;
  }

  private getDepth(element: Element): number {
    let depth = 0;
    let current: Element | null = element;

    while (current && current !== document.body) {
      depth++;
      current = current.parentElement;
    }

    return depth;
  }

  private getColorForDepth(depth: number): string {
    const colors = [
      "#3B82F6", // Blue (depth 0-2)
      "#10B981", // Green (depth 3-5)
      "#F59E0B", // Yellow (depth 6-8)
      "#EF4444", // Red (depth 9-11)
      "#EC4899", // Pink (depth 12+)
    ];

    const index = Math.min(Math.floor(depth / 3), colors.length - 1);
    return colors[index];
  }

  private createLabel(
    element: Element,
    depth: number,
  ): HTMLDivElement | null {
    const tag = element.tagName.toLowerCase();
    const id = element.id;
    const classes = element.className;

    // Build compact label text
    let labelText = `<span class="element-inspector-label-tag">${tag}</span>`;

    if (id) {
      labelText += ` <span class="element-inspector-label-id">#${id}</span>`;
    }

    if (classes && typeof classes === "string") {
      const classList = classes.split(/\s+/).filter((c) => c.length > 0);
      if (classList.length > 0) {
        const classPreview = classList.slice(0, 2).join(".");
        labelText += ` <span class="element-inspector-label-class">.${classPreview}</span>`;
        if (classList.length > 2) {
          labelText += `<span class="element-inspector-label-class">+${classList.length - 2}</span>`;
        }
      }
    }

    if (depth > 5) {
      labelText += ` <span style="color: #999; font-size: 9px;">d${depth}</span>`;
    }

    const label = document.createElement("div");
    label.className = "element-inspector-label";
    label.innerHTML = labelText;
    label.title = "Click to copy comprehensive debug info for AI";

    return label;
  }

  private addHoverHighlight(
    label: HTMLDivElement,
    box: HTMLDivElement,
    element: Element,
  ): void {
    label.addEventListener("mouseenter", () => {
      this.currentlyHoveredBox = box;
      this.currentlyHoveredElement = element;

      box.classList.add("highlighted");
      if (element instanceof HTMLElement) {
        element.style.outline = "3px solid rgba(59, 130, 246, 0.8)";
        element.style.outlineOffset = "2px";
      }
    });

    label.addEventListener("mouseleave", () => {
      this.currentlyHoveredBox = null;
      this.currentlyHoveredElement = null;

      box.classList.remove("highlighted");
      if (element instanceof HTMLElement) {
        element.style.outline = "";
        element.style.outlineOffset = "";
      }
    });
  }

  private addCopyToClipboard(
    label: HTMLDivElement,
    element: Element,
  ): void {
    // Right-click to copy
    label.addEventListener("contextmenu", async (e: MouseEvent) => {
      e.stopPropagation();
      e.preventDefault();

      const debugInfo = this.debugCollector.gatherElementDebugInfo(element);

      try {
        await navigator.clipboard.writeText(debugInfo);
        this.notificationManager.showNotification("✓ Copied!", "success");
        console.log("[ElementInspector] Copied debug info to clipboard");

        // Trigger auto-dismiss (ESC) after copy
        this.notificationManager.triggerCopyCallback();
      } catch (err) {
        console.error("[ElementInspector] Failed to copy:", err);
        this.notificationManager.showNotification("✗ Copy Failed", "error");
      }
    });
  }
}
