/**
 * Selection Manager for Element Inspector
 * Handles rectangle selection mode and element selection
 */

import type { SelectionRect } from "./types";
import { DebugInfoCollector } from "./debug-info-collector";
import { NotificationManager } from "./notification-manager";

export class SelectionManager {
  private selectionMode: boolean = false;
  private selectionStart: { x: number; y: number } | null = null;
  private selectionRect: HTMLDivElement | null = null;
  private selectionOverlay: HTMLDivElement | null = null;
  private currentlySelectedElements: Set<Element> = new Set();
  private elementBoxMap: Map<HTMLDivElement, Element>;
  private debugCollector: DebugInfoCollector;
  private notificationManager: NotificationManager;

  constructor(
    elementBoxMap: Map<HTMLDivElement, Element>,
    debugCollector: DebugInfoCollector,
    notificationManager: NotificationManager,
  ) {
    this.elementBoxMap = elementBoxMap;
    this.debugCollector = debugCollector;
    this.notificationManager = notificationManager;
  }

  public isActive(): boolean {
    return this.selectionMode;
  }

  public startSelectionMode(): void {
    this.selectionMode = true;

    document.body.classList.add("element-inspector-selection-mode");

    this.selectionOverlay = document.createElement("div");
    this.selectionOverlay.className = "selection-overlay";
    document.body.appendChild(this.selectionOverlay);

    this.notificationManager.showNotification(
      "Drag to select area",
      "success",
    );

    document.addEventListener("mousedown", this.onSelectionMouseDown);
    document.addEventListener("mousemove", this.onSelectionMouseMove);
    document.addEventListener("mouseup", this.onSelectionMouseUp);
  }

  public cancelSelectionMode(): void {
    this.selectionMode = false;

    document.body.classList.remove("element-inspector-selection-mode");

    this.clearSelectionHighlights();

    if (this.selectionOverlay) {
      this.selectionOverlay.remove();
      this.selectionOverlay = null;
    }

    if (this.selectionRect) {
      this.selectionRect.remove();
      this.selectionRect = null;
    }

    document.removeEventListener("mousedown", this.onSelectionMouseDown);
    document.removeEventListener("mousemove", this.onSelectionMouseMove);
    document.removeEventListener("mouseup", this.onSelectionMouseUp);

    this.selectionStart = null;
  }

  private onSelectionMouseDown = (e: MouseEvent): void => {
    if (!this.selectionMode) return;

    e.preventDefault();
    this.selectionStart = {
      x: e.clientX,
      y: e.clientY,
    };

    this.selectionRect = document.createElement("div");
    this.selectionRect.className = "selection-rectangle";
    this.selectionRect.style.left = `${e.clientX}px`;
    this.selectionRect.style.top = `${e.clientY}px`;
    this.selectionRect.style.width = "0px";
    this.selectionRect.style.height = "0px";

    document.body.appendChild(this.selectionRect);
  };

  private onSelectionMouseMove = (e: MouseEvent): void => {
    if (!this.selectionMode || !this.selectionStart || !this.selectionRect) {
      return;
    }

    e.preventDefault();

    const currentX = e.clientX;
    const currentY = e.clientY;

    const left = Math.min(this.selectionStart.x, currentX);
    const top = Math.min(this.selectionStart.y, currentY);
    const width = Math.abs(currentX - this.selectionStart.x);
    const height = Math.abs(currentY - this.selectionStart.y);

    this.selectionRect.style.left = `${left}px`;
    this.selectionRect.style.top = `${top}px`;
    this.selectionRect.style.width = `${width}px`;
    this.selectionRect.style.height = `${height}px`;

    this.updateSelectionHighlights({ left, top, width, height });
  };

  private onSelectionMouseUp = async (e: MouseEvent): Promise<void> => {
    if (!this.selectionMode || !this.selectionStart || !this.selectionRect)
      return;

    e.preventDefault();

    const currentX = e.clientX;
    const currentY = e.clientY;

    const left = Math.min(this.selectionStart.x, currentX);
    const top = Math.min(this.selectionStart.y, currentY);
    const width = Math.abs(currentX - this.selectionStart.x);
    const height = Math.abs(currentY - this.selectionStart.y);

    if (width < 5 || height < 5) {
      this.cancelSelectionMode();
      this.notificationManager.showNotification(
        "Selection too small",
        "error",
      );
      return;
    }

    const selectedElements = this.findElementsInRect({
      left,
      top,
      width,
      height,
    });

    console.log(
      `[ElementInspector] Found ${selectedElements.length} elements in selection`,
    );

    const selectionInfo = this.gatherSelectionInfo(selectedElements, {
      left,
      top,
      width,
      height,
    });

    try {
      await navigator.clipboard.writeText(selectionInfo);
      this.notificationManager.showNotification(
        `✓ ${selectedElements.length} elements copied!`,
        "success",
      );
      console.log("[ElementInspector] Selection info copied to clipboard");

      // Trigger auto-dismiss (ESC) after copy
      this.notificationManager.triggerCopyCallback();
    } catch (err) {
      console.error("[ElementInspector] Failed to copy:", err);
      this.notificationManager.showNotification("✗ Copy Failed", "error");
    }

    this.cancelSelectionMode();
  };

  private updateSelectionHighlights(rect: SelectionRect): void {
    const selectedElements = this.findElementsInRect(rect);
    const newSelection = new Set(selectedElements);

    const selectedBoxes = new Set<HTMLDivElement>();

    this.elementBoxMap.forEach((element, box) => {
      if (newSelection.has(element)) {
        selectedBoxes.add(box);
      }
    });

    this.elementBoxMap.forEach((element, box) => {
      if (
        this.currentlySelectedElements.has(element) &&
        !newSelection.has(element)
      ) {
        box.style.borderWidth = "2px";
        box.style.background = "rgba(255, 255, 255, 0.01)";
        box.style.transform = "";
        box.style.zIndex = "";

        if (element instanceof HTMLElement) {
          element.classList.remove("element-inspector-selected");
        }
      }
    });

    selectedBoxes.forEach((box) => {
      const element = this.elementBoxMap.get(box);
      if (element && !this.currentlySelectedElements.has(element)) {
        const depth = this.getDepth(element);
        const color = this.getColorForDepth(depth);

        box.style.borderWidth = "4px";
        box.style.background = this.hexToRgba(color, 0.25);
        box.style.transform = "scale(1.02)";
        box.style.zIndex = "1000000";

        if (element instanceof HTMLElement) {
          element.classList.add("element-inspector-selected");
        }
      }
    });

    this.currentlySelectedElements = newSelection;
  }

  private clearSelectionHighlights(): void {
    this.elementBoxMap.forEach((element, box) => {
      if (this.currentlySelectedElements.has(element)) {
        box.style.borderWidth = "2px";
        box.style.background = "rgba(255, 255, 255, 0.01)";
        box.style.transform = "";
        box.style.zIndex = "";
      }
    });

    this.currentlySelectedElements.forEach((element) => {
      if (element instanceof HTMLElement) {
        element.classList.remove("element-inspector-selected");
      }
    });
    this.currentlySelectedElements.clear();
  }

  private hexToRgba(hex: string, alpha: number): string {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!result) return `rgba(59, 130, 246, ${alpha})`;

    const r = parseInt(result[1], 16);
    const g = parseInt(result[2], 16);
    const b = parseInt(result[3], 16);

    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  private findElementsInRect(rect: SelectionRect): Element[] {
    const selectedElements: Element[] = [];
    const allElements = document.querySelectorAll("*");

    const selectionRect = {
      left: rect.left,
      top: rect.top,
      right: rect.left + rect.width,
      bottom: rect.top + rect.height,
    };

    allElements.forEach((element: Element) => {
      if (
        element.closest("#element-inspector-overlay") ||
        element.classList.contains("selection-rectangle") ||
        element.classList.contains("selection-overlay")
      ) {
        return;
      }

      if (element instanceof HTMLElement) {
        const computed = window.getComputedStyle(element);
        if (computed.display === "none" || computed.visibility === "hidden") {
          return;
        }
      }

      const elementRect = element.getBoundingClientRect();
      const elementBounds = {
        left: elementRect.left,
        top: elementRect.top,
        right: elementRect.right,
        bottom: elementRect.bottom,
      };

      const intersects = !(
        elementBounds.right < selectionRect.left ||
        elementBounds.left > selectionRect.right ||
        elementBounds.bottom < selectionRect.top ||
        elementBounds.top > selectionRect.bottom
      );

      if (intersects) {
        selectedElements.push(element);
      }
    });

    return selectedElements;
  }

  private gatherSelectionInfo(
    elements: Element[],
    rect: SelectionRect,
  ): string {
    let info = `# Rectangle Selection Debug Information

## Selection Area
- Position: (${Math.round(rect.left)}, ${Math.round(rect.top)})
- Size: ${Math.round(rect.width)}×${Math.round(rect.height)}px
- URL: ${window.location.href}
- Timestamp: ${new Date().toISOString()}
- Elements Found: ${elements.length}

---

`;

    const elementTypes: { [key: string]: number } = {};
    elements.forEach((el) => {
      const tag = el.tagName.toLowerCase();
      elementTypes[tag] = (elementTypes[tag] || 0) + 1;
    });

    info += `## Element Type Summary\n`;
    Object.entries(elementTypes)
      .sort((a, b) => b[1] - a[1])
      .forEach(([tag, count]) => {
        info += `- ${tag}: ${count}\n`;
      });

    info += `\n---\n\n`;

    const maxDetailedElements = 20;
    const detailedCount = Math.min(elements.length, maxDetailedElements);

    info += `## Detailed Element Information (${detailedCount} of ${elements.length} elements)\n\n`;
    info += `> **Note**: Showing comprehensive debug info for the first ${detailedCount} elements.\n`;
    info += `> Each element includes: attributes, computed styles, dimensions, matching CSS rules, etc.\n\n`;
    info += `---\n\n`;

    elements.slice(0, maxDetailedElements).forEach((element, index) => {
      info += `# Element ${index + 1}/${elements.length}\n\n`;
      const elementDebugInfo = this.debugCollector.gatherElementDebugInfo(
        element,
      );
      info += elementDebugInfo;
      info += `\n${"=".repeat(80)}\n\n`;
    });

    if (elements.length > maxDetailedElements) {
      info += `## Remaining Elements (${elements.length - maxDetailedElements} elements - basic info)\n\n`;

      elements.slice(maxDetailedElements).forEach((element, index) => {
        const actualIndex = maxDetailedElements + index + 1;
        const selector = this.debugCollector.buildCSSSelector(element);
        const rect = element.getBoundingClientRect();
        const text = element.textContent?.trim().substring(0, 50);

        info += `### ${actualIndex}. ${selector}\n`;
        info += `- Position: (${Math.round(rect.left)}, ${Math.round(rect.top)}) | Size: ${Math.round(rect.width)}×${Math.round(rect.height)}px\n`;
        if (text) info += `- Text: "${text}${text.length > 50 ? "..." : ""}"\n`;
        info += `\n`;
      });
    }

    info += `\n---\nGenerated by Element Inspector - Rectangle Selection Mode (Enhanced)\n`;
    info += `Press Ctrl+Alt+I to start selection mode again.\n`;

    return info;
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
      "#3B82F6",
      "#10B981",
      "#F59E0B",
      "#EF4444",
      "#EC4899",
    ];

    const index = Math.min(Math.floor(depth / 3), colors.length - 1);
    return colors[index];
  }
}
