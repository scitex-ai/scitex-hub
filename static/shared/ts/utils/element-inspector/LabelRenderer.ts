/**
 * LabelRenderer - Label creation and positioning for Element Inspector
 *
 * Handles label visibility logic, positioning to avoid overlaps,
 * and copy/hover interactions.
 * Extracted from ElementScanner.ts for single responsibility.
 */

import type { LabelPosition, OccupiedPosition } from "./types";
import type { DebugInfoCollector } from "./debug-info-collector";
import type { NotificationManager } from "./notification-manager";

export class LabelRenderer {
  private debugCollector: DebugInfoCollector;
  private notificationManager: NotificationManager;

  constructor(
    debugCollector: DebugInfoCollector,
    notificationManager: NotificationManager
  ) {
    this.debugCollector = debugCollector;
    this.notificationManager = notificationManager;
  }

  /**
   * Determine if a label should be shown for this element
   */
  public shouldShowLabel(element: Element, rect: DOMRect, depth: number): boolean {
    // 1. Element has an ID - always show
    if (element.id) {
      return rect.width > 20 && rect.height > 20;
    }

    // 2. Large elements (100px+) - show
    if (rect.width > 100 || rect.height > 100) {
      return true;
    }

    // 3. Important semantic elements
    const importantTags = [
      "header", "nav", "main", "section", "article",
      "aside", "footer", "form", "table",
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

    return false;
  }

  /**
   * Find non-overlapping position for a label
   */
  public findLabelPosition(rect: DOMRect, occupiedPositions: OccupiedPosition[]): LabelPosition {
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

    for (const pos of positions) {
      if (!this.isPositionOccupied(pos, occupiedPositions)) {
        return { ...pos, isValid: true };
      }
    }

    return { top: 0, left: 0, isValid: false };
  }

  /**
   * Check if a position overlaps with occupied positions
   */
  private isPositionOccupied(
    pos: { top: number; left: number },
    occupiedPositions: OccupiedPosition[]
  ): boolean {
    const labelWidth = 250;
    const labelHeight = 20;

    for (const occupied of occupiedPositions) {
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

  /**
   * Create a label element for the given DOM element
   */
  public createLabel(element: Element, depth: number): HTMLDivElement | null {
    const tag = element.tagName.toLowerCase();
    const id = element.id;
    const classes = element.className;

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

  /**
   * Add hover highlight behavior to label
   */
  public addHoverHighlight(
    label: HTMLDivElement,
    box: HTMLDivElement,
    element: Element,
    onHover: (box: HTMLDivElement | null, element: Element | null) => void
  ): void {
    label.addEventListener("mouseenter", () => {
      onHover(box, element);
      box.classList.add("highlighted");
      if (element instanceof HTMLElement) {
        element.style.outline = "3px solid rgba(59, 130, 246, 0.8)";
        element.style.outlineOffset = "2px";
      }
    });

    label.addEventListener("mouseleave", () => {
      onHover(null, null);
      box.classList.remove("highlighted");
      if (element instanceof HTMLElement) {
        element.style.outline = "";
        element.style.outlineOffset = "";
      }
    });
  }

  /**
   * Add copy-to-clipboard behavior on right-click
   */
  public addCopyToClipboard(label: HTMLDivElement, element: Element): void {
    label.addEventListener("contextmenu", async (e: MouseEvent) => {
      e.stopPropagation();
      e.preventDefault();

      const debugInfo = this.debugCollector.gatherElementDebugInfo(element);

      try {
        await navigator.clipboard.writeText(debugInfo);
        this.notificationManager.showNotification("✓ Copied!", "success");
        console.log("[ElementInspector] Copied debug info to clipboard");
        this.notificationManager.triggerCopyCallback();
      } catch (err) {
        console.error("[ElementInspector] Failed to copy:", err);
        this.notificationManager.showNotification("✗ Copy Failed", "error");
      }
    });
  }
}
