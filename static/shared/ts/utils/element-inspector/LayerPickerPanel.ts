/**
 * LayerPickerPanel - Layer selection UI for Element Inspector
 *
 * Displays a floating panel with stacked elements at cursor position.
 * Supports scroll wheel and keyboard navigation (↑↓/Tab + Enter).
 * Extracted from ElementScanner.ts for single responsibility.
 */

import type { DebugInfoCollector } from "./debug-info-collector";
import type { NotificationManager } from "./notification-manager";

export type HighlightCallback = (element: Element) => void;

export class LayerPickerPanel {
  private panel: HTMLDivElement | null = null;
  private elementsAtCursor: Element[] = [];
  private currentDepthIndex: number = 0;
  private debugCollector: DebugInfoCollector;
  private notificationManager: NotificationManager;
  private highlightCallback: HighlightCallback | null = null;
  private getDepthFn: (element: Element) => number;
  private getColorFn: (depth: number) => string;

  constructor(
    debugCollector: DebugInfoCollector,
    notificationManager: NotificationManager,
    getDepthFn: (element: Element) => number,
    getColorFn: (depth: number) => string
  ) {
    this.debugCollector = debugCollector;
    this.notificationManager = notificationManager;
    this.getDepthFn = getDepthFn;
    this.getColorFn = getColorFn;
  }

  /**
   * Set callback for highlighting selected element
   */
  public setHighlightCallback(callback: HighlightCallback): void {
    this.highlightCallback = callback;
  }

  /**
   * Get current depth index
   */
  public getCurrentDepthIndex(): number {
    return this.currentDepthIndex;
  }

  /**
   * Get elements at cursor
   */
  public getElementsAtCursor(): Element[] {
    return this.elementsAtCursor;
  }

  /**
   * Get the currently selected element
   */
  public getSelectedElement(): Element | null {
    if (this.elementsAtCursor.length > 0 && this.currentDepthIndex < this.elementsAtCursor.length) {
      return this.elementsAtCursor[this.currentDepthIndex];
    }
    return null;
  }

  /**
   * Show layer picker panel at position with given elements
   */
  public show(x: number, y: number, elements: Element[]): void {
    this.remove();
    this.elementsAtCursor = elements;
    this.currentDepthIndex = 0;

    if (elements.length <= 1) return;

    const panel = document.createElement("div");
    panel.className = "element-inspector-layer-picker";
    panel.tabIndex = 0;
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
    header.textContent = `${elements.length} layers (↑↓/Tab + Enter)`;
    panel.appendChild(header);

    this.setupKeyboardHandler(panel);
    this.renderElementList(panel, elements);

    document.body.appendChild(panel);
    this.panel = panel;
    this.updateSelection();

    setTimeout(() => panel.focus(), 10);
  }

  /**
   * Render the element list in the panel
   */
  private renderElementList(panel: HTMLDivElement, elements: Element[]): void {
    elements.forEach((el, index) => {
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

      // Depth indicator
      const depthBar = document.createElement("span");
      const depth = this.getDepthFn(el);
      depthBar.style.cssText = `
        width: ${Math.min(depth * 3, 30)}px;
        height: 3px;
        background: ${this.getColorFn(depth)};
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
        this.highlightCallback?.(el);
        this.updateSelection();
      });

      panel.appendChild(item);
    });
  }

  /**
   * Setup keyboard navigation
   */
  private setupKeyboardHandler(panel: HTMLDivElement): void {
    panel.addEventListener("keydown", async (e: KeyboardEvent) => {
      const maxIndex = this.elementsAtCursor.length - 1;

      switch (e.key) {
        case "ArrowDown":
        case "Tab":
          if (!e.shiftKey) {
            e.preventDefault();
            e.stopPropagation();
            this.currentDepthIndex = Math.min(this.currentDepthIndex + 1, maxIndex);
            this.highlightCallback?.(this.elementsAtCursor[this.currentDepthIndex]);
            this.updateSelection();
          } else if (e.key === "Tab") {
            e.preventDefault();
            e.stopPropagation();
            this.currentDepthIndex = Math.max(this.currentDepthIndex - 1, 0);
            this.highlightCallback?.(this.elementsAtCursor[this.currentDepthIndex]);
            this.updateSelection();
          }
          break;

        case "ArrowUp":
          e.preventDefault();
          e.stopPropagation();
          this.currentDepthIndex = Math.max(this.currentDepthIndex - 1, 0);
          this.highlightCallback?.(this.elementsAtCursor[this.currentDepthIndex]);
          this.updateSelection();
          break;

        case "Enter":
          e.preventDefault();
          e.stopPropagation();
          await this.confirmSelection();
          break;

        case "Escape":
          e.preventDefault();
          e.stopPropagation();
          this.remove();
          break;
      }
    });
  }

  /**
   * Confirm current selection (copy debug info)
   */
  private async confirmSelection(): Promise<void> {
    if (this.elementsAtCursor.length === 0) return;

    const selectedElement = this.elementsAtCursor[this.currentDepthIndex];
    if (!selectedElement) return;

    const debugInfo = this.debugCollector.gatherElementDebugInfo(selectedElement);

    try {
      await navigator.clipboard.writeText(debugInfo);
      this.notificationManager.showNotification("✓ Copied!", "success");
      console.log("[ElementInspector] Copied debug info to clipboard");
      this.notificationManager.triggerCopyCallback();
    } catch (err) {
      console.error("[ElementInspector] Failed to copy:", err);
      this.notificationManager.showNotification("✗ Copy Failed", "error");
    }
  }

  /**
   * Update selection highlight in panel
   */
  public updateSelection(): void {
    if (!this.panel) return;

    const items = this.panel.querySelectorAll("[data-index]");
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
   * Navigate to next/previous element via scroll
   */
  public navigate(direction: 'up' | 'down'): void {
    if (this.elementsAtCursor.length <= 1) return;

    if (direction === 'down') {
      this.currentDepthIndex = Math.min(
        this.currentDepthIndex + 1,
        this.elementsAtCursor.length - 1
      );
    } else {
      this.currentDepthIndex = Math.max(this.currentDepthIndex - 1, 0);
    }

    this.highlightCallback?.(this.elementsAtCursor[this.currentDepthIndex]);
    this.updateSelection();
  }

  /**
   * Remove the panel
   */
  public remove(): void {
    if (this.panel) {
      this.panel.remove();
      this.panel = null;
    }
  }

  /**
   * Reset state
   */
  public reset(): void {
    this.remove();
    this.elementsAtCursor = [];
    this.currentDepthIndex = 0;
  }

  /**
   * Check if panel is visible
   */
  public isVisible(): boolean {
    return this.panel !== null;
  }
}
