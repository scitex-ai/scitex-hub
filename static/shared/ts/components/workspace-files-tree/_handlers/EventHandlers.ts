/**
 * Event Handlers for WorkspaceFilesTree
 *
 * Click behavior (file-manager style):
 *   Single click         → select/highlight only
 *   Click on selected    → rename (after 400ms delay, cancelled by dblclick)
 *   Double click         → open in viewer/editor
 *   Triple click         → run (for .py, .sh, .js)
 */

import type { TreeItem, TreeConfig } from "../types";
import type { TreeStateManager } from "../_TreeState";

const RUNNABLE_EXTS = [".py", ".sh", ".js"];
const RENAME_DELAY_MS = 400;

export class EventHandlers {
  private renameTimer: number | null = null;
  private lastSelectedPath: string | null = null;

  constructor(
    private config: TreeConfig,
    private stateManager: TreeStateManager,
    private onToggleFolder: (path: string) => void,
    private onSelectFile: (path: string, event?: MouseEvent) => void,
    private onOpenFile: (path: string) => void,
    private onRunFile: (path: string) => void,
    private onRename: (path: string, el: HTMLElement) => void,
    private onDelete?: (path: string) => void,
    private onNewFile?: (folderPath: string) => void,
    private onNewFolder?: (folderPath: string) => void,
    private onCopy?: (path: string) => void,
    private onGitAction?: (action: string, path: string) => void,
  ) {}

  private cancelPendingRename(): void {
    if (this.renameTimer !== null) {
      clearTimeout(this.renameTimer);
      this.renameTimer = null;
    }
  }

  attachEventListeners(container: HTMLElement): void {
    const treeEl = container.querySelector(".wft-tree");
    if (!treeEl) return;

    // File/folder click (ignore right-clicks - context menu handles those)
    treeEl.addEventListener("click", (evt) => {
      const e = evt as MouseEvent;
      // Ignore right-click - context menu handles it
      if (e.button !== 0) return;
      const target = e.target as HTMLElement;

      // Action buttons (delete, new-file, new-folder)
      const actionBtn = target.closest(".wft-action-btn") as HTMLElement;
      if (actionBtn) {
        this.handleActionButton(actionBtn, e);
        return;
      }

      // Folder toggle (chevron icon)
      const chevron = target.closest(".wft-folder-chevron");
      if (chevron) {
        e.preventDefault();
        const folderItem = chevron.closest("[data-path]");
        if (folderItem) {
          this.onToggleFolder(folderItem.getAttribute("data-path")!);
        }
        return;
      }

      // File selection — single click = select only
      const fileItem = target.closest(".wft-file[data-path]");
      if (fileItem && !fileItem.classList.contains("disabled")) {
        e.preventDefault();
        const path = fileItem.getAttribute("data-path")!;
        this.handleFileClick(path, fileItem as HTMLElement, container);
        return;
      }

      // Root item selection (project root)
      const rootItem = target.closest('.wft-root[data-path=""]');
      if (rootItem) {
        e.preventDefault();
        this.cancelPendingRename();
        this.onSelectFile("", e);
        container.focus();
        return;
      }

      // Folder selection (click anywhere on folder row)
      const folderItem = target.closest(".wft-folder[data-path]");
      if (folderItem && !folderItem.classList.contains("disabled")) {
        const clickedOnAction = target.closest(".wft-action-btn");
        if (!clickedOnAction) {
          e.preventDefault();
          const path = folderItem.getAttribute("data-path")!;
          this.cancelPendingRename();
          this.onSelectFile(path, e);
          if (!e.ctrlKey && !e.metaKey && !e.shiftKey) {
            this.onToggleFolder(path);
          }
          container.focus();
        }
        return;
      }

      // Click on empty space — select root
      const treeArea = target.closest(".wft-tree");
      if (treeArea) {
        e.preventDefault();
        this.cancelPendingRename();
        this.stateManager.clearSelection();
        this.onSelectFile("", e);
        container.focus();
      }
    });

    // Double-click → open file in viewer/editor
    treeEl.addEventListener("dblclick", (e) => {
      this.cancelPendingRename();
      const target = e.target as HTMLElement;
      const fileItem = target.closest(".wft-file[data-path]");
      if (fileItem) {
        e.preventDefault();
        const path = fileItem.getAttribute("data-path")!;
        this.onOpenFile(path);
      }
    });

    // Triple-click → run (for executable files)
    treeEl.addEventListener("click", (evt) => {
      const e = evt as MouseEvent;
      if (e.detail === 3) {
        this.cancelPendingRename();
        const target = e.target as HTMLElement;
        const fileItem = target.closest(".wft-file[data-path]");
        if (fileItem) {
          const path = fileItem.getAttribute("data-path")!;
          const ext = path.substring(path.lastIndexOf("."));
          if (RUNNABLE_EXTS.includes(ext)) {
            e.preventDefault();
            this.onRunFile(path);
          }
        }
      }
    });

    // Context menu
    treeEl.addEventListener("contextmenu", (e) => {
      e.preventDefault();
    });
  }

  /** Handle single click on a file: select, or rename if already selected */
  private handleFileClick(
    path: string,
    el: HTMLElement,
    container: HTMLElement,
  ): void {
    this.cancelPendingRename();

    const wasAlreadySelected = this.lastSelectedPath === path;

    // Always select first
    this.onSelectFile(path);
    this.lastSelectedPath = path;
    container.focus();

    // If clicking an already-selected file, start rename after delay
    // (cancelled if dblclick fires within RENAME_DELAY_MS)
    if (wasAlreadySelected) {
      this.renameTimer = window.setTimeout(() => {
        this.renameTimer = null;
        this.onRename(path, el);
      }, RENAME_DELAY_MS);
    }
  }

  private handleActionButton(actionBtn: HTMLElement, e: MouseEvent): void {
    e.preventDefault();
    e.stopPropagation();
    const action = actionBtn.getAttribute("data-action");
    const path = actionBtn.getAttribute("data-path");

    if (action === "delete" && path && this.onDelete) {
      this.onDelete(path);
    } else if (action === "new-file" && path && this.onNewFile) {
      this.onNewFile(path);
    } else if (action === "new-folder" && path && this.onNewFolder) {
      this.onNewFolder(path);
    } else if (action === "rename" && path) {
      const item = actionBtn.closest("[data-path]") as HTMLElement;
      if (item) this.onRename(path, item);
    } else if (action === "copy" && path && this.onCopy) {
      this.onCopy(path);
    } else if (action?.startsWith("git-") && path && this.onGitAction) {
      this.onGitAction(action, path);
    }
  }
}
