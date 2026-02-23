/**
 * UI Action Executor — browser-side handler for the AI's `ui_action` tool.
 * The server skips MCP execution; the browser intercepts and drives the DOM.
 *
 * Supported actions:
 *   navigate | highlight | scroll | fill | click | clear |
 *   open-file | flash-file | write-scratch | append-scratch
 */

import { clearHighlights, highlightElement } from "../product-tour/ui";

export interface UIStep {
  action:
    | "navigate"
    | "highlight"
    | "scroll"
    | "fill"
    | "click"
    | "clear"
    | "open-file"
    | "flash-file"
    | "write-scratch"
    | "append-scratch";
  url?: string;
  selector?: string;
  message?: string;
  value?: string;
  position?: "top" | "bottom" | "left" | "right";
  path?: string; // File path for open-file and flash-file actions
  flashType?: "create" | "edit" | "delete"; // Flash type for flash-file action
  content?: string; // Content for write-scratch / append-scratch actions
}

export interface UIActionArgs {
  steps: UIStep[];
  delay_ms?: number;
}

// Active tooltip so we can clean up between steps
let activeTooltip: HTMLElement | null = null;

function removeTooltip(): void {
  if (activeTooltip) {
    activeTooltip.remove();
    activeTooltip = null;
  }
}

function showTooltip(
  element: Element,
  message: string,
  position: "top" | "bottom" | "left" | "right" = "bottom",
): void {
  removeTooltip();

  activeTooltip = document.createElement("div");
  activeTooltip.className = "product-tour-tooltip visible";
  activeTooltip.style.zIndex = "10002";
  activeTooltip.innerHTML = `
    <div class="product-tour-tooltip-content">
      <p class="product-tour-description" style="margin:0">${message}</p>
    </div>
    <div class="product-tour-arrow"></div>
  `;
  document.body.appendChild(activeTooltip);

  // Position relative to element
  requestAnimationFrame(() => {
    if (!activeTooltip) return;
    const rect = element.getBoundingClientRect();
    const tRect = activeTooltip.getBoundingClientRect();
    const gap = 12;
    const padding = 16;
    const arrow = activeTooltip.querySelector(
      ".product-tour-arrow",
    ) as HTMLElement;

    let top = 0;
    let left = 0;
    arrow.className = "product-tour-arrow";

    switch (position) {
      case "bottom":
        top = rect.bottom + gap;
        left = rect.left + rect.width / 2 - tRect.width / 2;
        arrow.classList.add("arrow-top");
        break;
      case "top":
        top = rect.top - tRect.height - gap;
        left = rect.left + rect.width / 2 - tRect.width / 2;
        arrow.classList.add("arrow-bottom");
        break;
      case "left":
        top = rect.top + rect.height / 2 - tRect.height / 2;
        left = rect.left - tRect.width - gap;
        arrow.classList.add("arrow-right");
        break;
      case "right":
        top = rect.top + rect.height / 2 - tRect.height / 2;
        left = rect.right + gap;
        arrow.classList.add("arrow-left");
        break;
    }

    left = Math.max(
      padding,
      Math.min(left, window.innerWidth - tRect.width - padding),
    );
    top = Math.max(
      padding,
      Math.min(top, window.innerHeight - tRect.height - padding),
    );

    activeTooltip.style.top = `${top}px`;
    activeTooltip.style.left = `${left}px`;

    const arrowLeft = rect.left + rect.width / 2 - left;
    arrow.style.left = `${Math.max(20, Math.min(arrowLeft, tRect.width - 20))}px`;
  });
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function executeStep(step: UIStep): Promise<void> {
  switch (step.action) {
    case "navigate":
      if (step.url) window.location.href = step.url;
      break;

    case "highlight": {
      if (!step.selector) break;
      const el = document.querySelector(step.selector);
      if (!el) break;
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      await sleep(300);
      highlightElement(el);
      if (step.message)
        showTooltip(el, step.message, step.position ?? "bottom");
      break;
    }

    case "scroll": {
      if (!step.selector) break;
      const el = document.querySelector(step.selector);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      break;
    }

    case "fill": {
      if (!step.selector) break;
      const el = document.querySelector(step.selector) as
        | HTMLInputElement
        | HTMLTextAreaElement
        | null;
      if (!el) break;
      el.focus();
      el.value = step.value ?? "";
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      break;
    }

    case "click": {
      if (!step.selector) break;
      const el = document.querySelector(step.selector) as HTMLElement | null;
      if (el) el.click();
      break;
    }

    case "clear":
      clearHighlights();
      removeTooltip();
      break;

    case "open-file": {
      const viewer = (window as any).workspaceViewer;
      if (step.path && viewer) {
        // Auto-expand viewer pane if collapsed
        const sidebar = document.getElementById("ws-viewer-sidebar");
        if (sidebar?.classList.contains("collapsed")) {
          sidebar.classList.remove("collapsed");
          const savedWidth = localStorage.getItem("ws-viewer-width");
          sidebar.style.width = savedWidth ? `${savedWidth}px` : "480px";
        }
        await viewer.openFile(step.path);
      }
      break;
    }

    case "flash-file": {
      if (step.path) {
        flashFileTreeNode(step.path, step.flashType ?? "edit");
      }
      break;
    }

    case "write-scratch": {
      const viewer = (window as any).workspaceViewer;
      if (viewer && step.content !== undefined) {
        viewer.writeScratch(step.content);
        // Switch to scratch tab
        await viewer.openFile("*scratch*");
      }
      break;
    }

    case "append-scratch": {
      const viewer = (window as any).workspaceViewer;
      if (viewer && step.content !== undefined) {
        viewer.appendScratch(step.content);
      }
      break;
    }
  }
}

export async function runUIActions(args: UIActionArgs): Promise<void> {
  const steps = args.steps ?? [];
  const delay = args.delay_ms ?? 900;

  for (const step of steps) {
    await executeStep(step);
    if (step.action !== "navigate") await sleep(delay);
  }
}

/* ============================================================
   File tree flash feedback
   ============================================================ */

/** Apply a brief color flash to an element */
function flashElement(
  el: HTMLElement,
  type: "create" | "edit" | "delete",
): void {
  const className = `wft-flash-${type}`;
  // Remove any existing flash classes
  el.classList.remove("wft-flash-create", "wft-flash-edit", "wft-flash-delete");
  // Force reflow to restart animation if re-triggered
  void el.offsetWidth;
  el.classList.add(className);
  el.addEventListener(
    "animationend",
    () => {
      el.classList.remove(className);
    },
    { once: true },
  );
}

/** Flash a file tree node to indicate create/edit/delete */
export function flashFileTreeNode(
  filePath: string,
  type: "create" | "edit" | "delete" = "edit",
): void {
  // Try exact data-path match first
  const node = document.querySelector(
    `.wft-item[data-path="${CSS.escape(filePath)}"]`,
  ) as HTMLElement | null;

  if (node) {
    flashElement(node, type);
    return;
  }

  // Fallback: match by path suffix (handles relative vs absolute differences)
  const candidates = document.querySelectorAll(".wft-item[data-path]");
  for (const el of candidates) {
    const elPath = (el as HTMLElement).dataset.path;
    if (elPath && (elPath.endsWith(filePath) || filePath.endsWith(elPath))) {
      flashElement(el as HTMLElement, type);
      return;
    }
  }
}

// Expose globally so agents and WebSocket handlers can call it
(window as any).flashFileTreeNode = flashFileTreeNode;
