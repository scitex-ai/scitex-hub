/**
 * Event Handlers for WorkspaceFilesTree
 *
 * Click behavior (Finder-on-touch / Google Drive style):
 *   Single click / tap   → select AND open in the viewer (folders toggle)
 *   Ctrl/Cmd/Shift click → select only (multi-select), never opens
 *   Double click         → no second open (the first click already opened)
 *   Triple click         → run (for .py, .sh, .js)
 *   Enter (keyboard)     → open (KeyboardHandlers)
 *
 * Opening used to need a double-click, which touch screens cannot do
 * reliably, and a second click on a selected file started a rename, so a
 * second tap renamed instead of opening (site audit 2026-09-14, D12). Rename
 * stays on F2, the row's rename button and the context menu.
 */

import type { TreeItem, TreeConfig } from "../types";
import type { TreeStateManager } from "../_TreeState";

const RUNNABLE_EXTS = [".py", ".sh", ".js"];

export class EventHandlers {
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

      // File — single click/tap selects and opens
      const fileItem = target.closest(".wft-file[data-path]");
      if (fileItem && !fileItem.classList.contains("disabled")) {
        e.preventDefault();
        const path = fileItem.getAttribute("data-path")!;
        this.handleFileClick(path, e, container);
        return;
      }

      // Root item selection (project root)
      const rootItem = target.closest('.wft-root[data-path=""]');
      if (rootItem) {
        e.preventDefault();
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
        this.stateManager.clearSelection();
        this.onSelectFile("", e);
        container.focus();
      }
    });

    // Double-click: the first click already opened the file; only stop the
    // browser from selecting the row's text.
    treeEl.addEventListener("dblclick", (e) => {
      const target = e.target as HTMLElement;
      if (target.closest(".wft-file[data-path]")) e.preventDefault();
    });

    // Triple-click → run (for executable files)
    treeEl.addEventListener("click", (evt) => {
      const e = evt as MouseEvent;
      if (e.detail === 3) {
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

  /**
   * Single click/tap on a file: select it and open it in the viewer.
   * A modifier click only extends the selection, and the repeat clicks of a
   * double/triple click do not open it again.
   */
  private handleFileClick(
    path: string,
    e: MouseEvent,
    container: HTMLElement,
  ): void {
    this.onSelectFile(path, e);
    container.focus();
    if (e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (e.detail > 1) return;
    this.onOpenFile(path);
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
