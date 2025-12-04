/**
 * UI Components Manager
 * Handles modals, context menus, resizers, and other UI interactions
 */

import type { EditorConfig } from "../core/types.js";

export class UIComponents {
  private config: EditorConfig;
  private onContextMenuAction: (action: string, target: string | null) => void;

  constructor(
    config: EditorConfig,
    onContextMenuAction: (action: string, target: string | null) => void
  ) {
    this.config = config;
    this.onContextMenuAction = onContextMenuAction;
  }

  initializeAll(): void {
    this.initContextMenu();
    this.initResizers();
  }

  private initContextMenu(): void {
    const fileTree = document.getElementById("file-tree");
    const contextMenu = document.getElementById("context-menu");

    if (!fileTree || !contextMenu) return;

    let contextTarget: string | null = null;

    fileTree.addEventListener("contextmenu", (e) => {
      e.preventDefault();

      const target = (e.target as HTMLElement).closest(".file-tree-item, .file-tree-file");
      if (!target) return;

      const fileElement = target.querySelector(".file-tree-file");
      contextTarget = fileElement?.getAttribute("data-file-path") || null;

      contextMenu.style.display = "block";
      contextMenu.style.left = `${e.pageX}px`;
      contextMenu.style.top = `${e.pageY}px`;
    });

    contextMenu.addEventListener("click", async (e) => {
      const item = (e.target as HTMLElement).closest(".context-menu-item");
      if (!item) return;

      const action = item.getAttribute("data-action");
      contextMenu.style.display = "none";

      if (action) {
        this.onContextMenuAction(action, contextTarget);
      }
    });

    document.addEventListener("click", () => {
      contextMenu.style.display = "none";
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        contextMenu.style.display = "none";
      }
    });
  }

  private initResizers(): void {
    this.setupResizer("sidebar-resizer", "code-sidebar", "horizontal");
    this.setupResizer("editor-resizer", "code-terminal-panel", "horizontal");
  }

  private setupResizer(
    resizerId: string,
    targetId: string,
    direction: "horizontal" | "vertical"
  ): void {
    const resizer = document.getElementById(resizerId);
    const target = document.getElementById(targetId);

    if (!resizer || !target) {
      console.warn(`[UIComponents] Resizer setup failed: resizer=${resizerId}, target=${targetId}`);
      return;
    }

    let isResizing = false;
    let startPos = 0;
    let startSize = 0;

    // Set minimum sizes based on target
    const MIN_SIDEBAR_WIDTH = 200;
    const MIN_TERMINAL_WIDTH = 300;
    const minSize = targetId === "code-sidebar" ? MIN_SIDEBAR_WIDTH :
                    targetId === "code-terminal-panel" ? MIN_TERMINAL_WIDTH : 100;

    resizer.addEventListener("mousedown", (e) => {
      isResizing = true;
      startPos = direction === "horizontal" ? e.clientX : e.clientY;
      startSize =
        direction === "horizontal" ? target.offsetWidth : target.offsetHeight;
      document.body.style.cursor =
        direction === "horizontal" ? "ew-resize" : "ns-resize";
      e.preventDefault();
    });

    document.addEventListener("mousemove", (e) => {
      if (!isResizing) return;

      const currentPos = direction === "horizontal" ? e.clientX : e.clientY;
      const delta = currentPos - startPos;

      // For terminal panel on the right, invert delta (dragging left = wider)
      // For sidebar on the left, use normal delta (dragging right = wider)
      const isTerminal = targetId === "code-terminal-panel";
      const adjustedDelta = isTerminal ? -delta : delta;
      const newSize = Math.max(minSize, startSize + adjustedDelta);

      if (direction === "horizontal") {
        target.style.width = `${newSize}px`;
      } else {
        target.style.height = `${newSize}px`;
      }
    });

    document.addEventListener("mouseup", () => {
      if (isResizing) {
        isResizing = false;
        document.body.style.cursor = "";
      }
    });
  }

  showFileModal(
    title: string,
    label: string,
    placeholder: string
  ): Promise<string | null> {
    return new Promise((resolve) => {
      const overlay = document.getElementById("file-modal-overlay");
      const modalTitle = document.getElementById("file-modal-title");
      const modalLabel = document.getElementById("file-modal-label");
      const input = document.getElementById("file-modal-input") as HTMLInputElement;
      const submitBtn = document.getElementById("file-modal-submit");

      if (!overlay || !modalTitle || !modalLabel || !input || !submitBtn) {
        console.error("[UIComponents] Modal elements not found");
        resolve(null);
        return;
      }

      modalTitle.textContent = title;
      modalLabel.textContent = label;
      input.placeholder = placeholder;
      input.value = "";

      overlay.classList.add("active");

      setTimeout(() => {
        input.focus();
      }, 200);

      const handleSubmit = () => {
        const value = input.value.trim();
        overlay.classList.remove("active");
        cleanup();
        resolve(value || null);
      };

      const handleCancel = () => {
        overlay.classList.remove("active");
        cleanup();
        resolve(null);
      };

      const handleKeyPress = (e: KeyboardEvent) => {
        if (e.key === "Enter") {
          e.preventDefault();
          handleSubmit();
        } else if (e.key === "Escape") {
          e.preventDefault();
          handleCancel();
        }
      };

      const cleanup = () => {
        submitBtn.removeEventListener("click", handleSubmit);
        overlay.removeEventListener("click", handleOverlayClick);
        input.removeEventListener("keydown", handleKeyPress);
      };

      const handleOverlayClick = (e: MouseEvent) => {
        if (e.target === overlay) {
          handleCancel();
        }
      };

      submitBtn.addEventListener("click", handleSubmit);
      overlay.addEventListener("click", handleOverlayClick);
      input.addEventListener("keydown", handleKeyPress);
    });
  }

  showNoProjectMessage(): void {
    const editor = document.getElementById("monaco-editor");
    if (editor) {
      editor.innerHTML = `
        <div class="welcome-screen" style="padding: 2rem;">
          <h2>No Project Selected</h2>
          <p>Please create or select a project to use the code editor.</p>
        </div>
      `;
    }
  }
}
