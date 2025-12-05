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

  public clearElementBoxMap(): void {
    this.elementBoxMap.clear();
    this.currentlyHoveredBox = null;
    this.currentlyHoveredElement = null;
  }

  public scanElements(overlayContainer: HTMLDivElement): void {
    // Get all elements
    const allElements = document.querySelectorAll("*");
    let count = 0;
    const occupiedPositions: OccupiedPosition[] = [];

    allElements.forEach((element: Element) => {
      // Skip our own overlay elements
      if (element.closest("#element-inspector-overlay")) return;

      // Skip invisible elements
      if (element instanceof HTMLElement) {
        const computed = window.getComputedStyle(element);
        if (computed.display === "none" || computed.visibility === "hidden")
          return;
      }

      // Get nesting depth for color gradation
      const depth = this.getDepth(element);
      const color = this.getColorForDepth(depth);

      // Create rectangle overlay
      const rect = element.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return;

      const box = document.createElement("div");
      box.className = "element-inspector-box";
      box.style.cssText = `
                top: ${rect.top + window.scrollY}px;
                left: ${rect.left + window.scrollX}px;
                width: ${rect.width}px;
                height: ${rect.height}px;
                border-color: ${color};
            `;

      // Set tooltip showing element info
      const tag = element.tagName.toLowerCase();
      const id = element.id ? `#${element.id}` : "";
      box.title = `Click to copy debug info: ${tag}${id}`;

      // Store element reference for layer picking
      this.elementBoxMap.set(box, element);

      // Track hover on box itself (not just label)
      box.addEventListener("mouseenter", () => {
        this.currentlyHoveredBox = box;
        this.currentlyHoveredElement = element;
      });

      box.addEventListener("mouseleave", () => {
        // Only clear if this is the currently hovered box
        if (this.currentlyHoveredBox === box) {
          this.currentlyHoveredBox = null;
          this.currentlyHoveredElement = null;
        }
      });

      // Make entire box area clickable - use hovered element if available
      box.addEventListener("click", async (e: MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();

        let selectedBox: HTMLDivElement;
        let selectedElement: Element;

        // If we have a currently hovered element, use that
        if (this.currentlyHoveredBox && this.currentlyHoveredElement) {
          selectedBox = this.currentlyHoveredBox;
          selectedElement = this.currentlyHoveredElement;
        } else {
          // Otherwise, use the box that was clicked
          selectedBox = box;
          selectedElement = element;
        }

        // Highlight the selected element
        selectedBox.classList.add("highlighted");

        const debugInfo = this.debugCollector.gatherElementDebugInfo(
          selectedElement,
        );
        try {
          await navigator.clipboard.writeText(debugInfo);
          this.notificationManager.showNotification(
            "✓ Copied!",
            "success",
          );
          console.log("[ElementInspector] Copied:", debugInfo);

          // Trigger auto-dismiss (ESC) after copy
          this.notificationManager.triggerCopyCallback();
        } catch (err) {
          console.error("[ElementInspector] Copy failed:", err);
          this.notificationManager.showNotification("✗ Copy Failed", "error");
          selectedBox.classList.remove("highlighted");
        }
      });

      // Create label only for important/large elements (sparse mode)
      const shouldShowLabel = this.shouldShowLabel(element, rect, depth);

      if (shouldShowLabel) {
        const label = this.createLabel(element, depth);
        if (label) {
          // Find non-overlapping position for label
          const labelPos = this.findLabelPosition(rect, occupiedPositions);

          // Only add label if we found a good position (not overlapping)
          if (labelPos.isValid) {
            label.style.top = `${labelPos.top}px`;
            label.style.left = `${labelPos.left}px`;

            // Add click-to-copy functionality
            this.addCopyToClipboard(label, element);

            // Add hover highlighting
            this.addHoverHighlight(label, box, element);

            // Track occupied space with extra padding to prevent crowding
            const labelPadding = 8;
            occupiedPositions.push({
              top: labelPos.top - labelPadding,
              left: labelPos.left - labelPadding,
              bottom: labelPos.top + 20 + labelPadding,
              right: labelPos.left + 250 + labelPadding,
            });

            overlayContainer.appendChild(label);
          }
        }
      }

      overlayContainer.appendChild(box);
      count++;
    });

    console.log(`[ElementInspector] Visualized ${count} elements`);
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
    label.addEventListener("click", async (e: MouseEvent) => {
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
