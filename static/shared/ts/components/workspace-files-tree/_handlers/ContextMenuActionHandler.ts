/**
 * Context Menu Action Handler
 *
 * Handles all context menu actions for the workspace files tree:
 * - Cut, Copy, Paste, Delete, Rename, Duplicate
 * - New File, New Folder
 * - Create Symlink, Download, Extract Bundle
 * - Git operations (stage, unstage, discard, history, diff)
 * - Tree operations (refresh, undo, redo)
 */

import type { TreeConfig } from "../types";
import type { SelectionHandler } from "./SelectionHandler";
import type { ClipboardHandler } from "./ClipboardHandler";
import type { UndoRedoHandler } from "./UndoRedoHandler";
import type { FileActions } from "./FileActions";
import type { GitActions } from "./GitActions";

export interface ContextMenuActionCallbacks {
  isItemDirectory: (path: string) => boolean;
  getContainer: () => HTMLElement | null;
  refresh: () => Promise<void>;
  getCsrfToken: () => string;
  showMessage: (message: string, type: "success" | "error" | "info") => void;
  downloadFile: (path: string) => void;
  extractBundle: (path: string) => Promise<void>;
  promptCreateSymlink: (path: string) => Promise<void>;
  showFilter: () => void;
}

export class ContextMenuActionHandler {
  private config: TreeConfig;
  private selectionHandler: SelectionHandler;
  private clipboardHandler: ClipboardHandler;
  private undoRedoHandler: UndoRedoHandler;
  private fileActions: FileActions;
  private gitActions: GitActions;
  private callbacks: ContextMenuActionCallbacks;

  constructor(
    config: TreeConfig,
    selectionHandler: SelectionHandler,
    clipboardHandler: ClipboardHandler,
    undoRedoHandler: UndoRedoHandler,
    fileActions: FileActions,
    gitActions: GitActions,
    callbacks: ContextMenuActionCallbacks,
  ) {
    this.config = config;
    this.selectionHandler = selectionHandler;
    this.clipboardHandler = clipboardHandler;
    this.undoRedoHandler = undoRedoHandler;
    this.fileActions = fileActions;
    this.gitActions = gitActions;
    this.callbacks = callbacks;
  }

  private getParentPath(path: string): string {
    const parts = path.split("/");
    parts.pop();
    return parts.join("/");
  }

  /**
   * Get paths for operation - uses selection if path is in it, otherwise just the path
   */
  private getPathsForOperation(path: string): string[] {
    const selectedPaths = this.selectionHandler.getSelectedPaths();
    if (selectedPaths.includes(path)) {
      return selectedPaths;
    }
    return [path];
  }

  /**
   * Handle a context menu action
   */
  async handle(action: string, path: string): Promise<void> {
    switch (action) {
      case "cut":
        console.log("[ContextMenuAction] Cut:", path);
        this.clipboardHandler.cut(this.getPathsForOperation(path));
        break;

      case "copy":
        console.log("[ContextMenuAction] Copy:", path);
        this.clipboardHandler.copy(this.getPathsForOperation(path));
        break;

      case "paste":
        console.log("[ContextMenuAction] Paste to:", path);
        await this.clipboardHandler.paste(path);
        break;

      case "delete":
        await this.handleDelete(path);
        break;

      case "rename":
        await this.handleRename(path);
        break;

      case "duplicate":
        await this.handleDuplicate(path);
        break;

      case "new-file": {
        const fileDir = this.callbacks.isItemDirectory(path)
          ? path
          : this.getParentPath(path);
        await this.fileActions.createNewFile(fileDir);
        break;
      }

      case "new-folder": {
        const folderDir = this.callbacks.isItemDirectory(path)
          ? path
          : this.getParentPath(path);
        await this.fileActions.createNewFolder(folderDir);
        break;
      }

      case "create-symlink": {
        const pathsForSymlink = this.getPathsForOperation(path);
        for (const p of pathsForSymlink) {
          await this.callbacks.promptCreateSymlink(p);
        }
        break;
      }

      case "download": {
        const pathsToDownload = this.getPathsForOperation(path);
        for (const p of pathsToDownload) {
          this.callbacks.downloadFile(p);
        }
        break;
      }

      case "extract-bundle":
        console.log("[ContextMenuAction] Extract bundle:", path);
        await this.callbacks.extractBundle(path);
        break;

      // Git actions - support multi-selection
      case "git-stage":
        await this.gitActions.stage(this.getPathsForOperation(path));
        break;

      case "git-unstage":
        await this.gitActions.unstage(this.getPathsForOperation(path));
        break;

      case "git-discard":
        await this.gitActions.discard(this.getPathsForOperation(path));
        break;

      case "git-history":
        await this.gitActions.showHistory(path);
        break;

      case "git-diff":
        await this.gitActions.showDiff(path);
        break;

      // Git bulk operations (from root context menu)
      case "git-stage-all":
        await this.gitActions.stageAll();
        break;

      case "git-unstage-all":
        await this.gitActions.unstageAll();
        break;

      case "git-commit":
        await this.handleGitCommit(false);
        break;

      case "git-commit-push":
        await this.handleGitCommit(true);
        break;

      case "git-push":
        await this.gitActions.push();
        break;

      case "git-pull":
        await this.gitActions.pull();
        break;

      case "run-file":
        // Dispatch run-file event so the workspace terminal picks it up
        document.dispatchEvent(
          new CustomEvent("run-file", { detail: { path } }),
        );
        break;

      case "clew":
        // Dispatch fileSelected so the Clew pane picks it up
        document.dispatchEvent(
          new CustomEvent("fileSelected", { detail: { path } }),
        );
        break;

      case "filter":
        this.callbacks.showFilter();
        break;

      // Tree operations
      case "refresh":
        await this.callbacks.refresh();
        break;

      case "undo":
        await this.undoRedoHandler.undo();
        break;

      case "redo":
        await this.undoRedoHandler.redo();
        break;

      default:
        console.warn("[ContextMenuAction] Unknown action:", action);
    }
  }

  /**
   * Handle git commit with prompt dialog
   */
  private async handleGitCommit(push: boolean): Promise<void> {
    const label = push ? "Commit & Push" : "Commit";
    const message = window.prompt(`${label} — Enter commit message:`);
    if (!message || !message.trim()) return;
    await this.gitActions.commit(message.trim(), push);
  }

  /**
   * Handle delete action with undo recording
   */
  private async handleDelete(path: string): Promise<void> {
    const pathsToDelete = this.getPathsForOperation(path);
    console.log("[ContextMenuAction] Delete:", pathsToDelete);

    // Record for undo before deleting
    for (const p of pathsToDelete) {
      this.undoRedoHandler.recordOperation({
        type: "delete",
        timestamp: Date.now(),
        originalPath: p,
        isDirectory: this.callbacks.isItemDirectory(p),
      });
      await this.fileActions.deleteFile(p);
    }
  }

  /**
   * Handle rename action with undo recording
   */
  private async handleRename(path: string): Promise<void> {
    console.log("[ContextMenuAction] Rename:", path);
    const container = this.callbacks.getContainer();
    const el = container?.querySelector(`[data-path="${path}"]`) as HTMLElement;

    if (el) {
      console.log("[ContextMenuAction] Found element for rename:", el);
      const result = await this.fileActions.startRename(path, el);
      // Record rename for undo if successful
      if (result && result.newPath) {
        this.undoRedoHandler.recordOperation({
          type: "rename",
          timestamp: Date.now(),
          originalPath: path,
          newPath: result.newPath,
          isDirectory: this.callbacks.isItemDirectory(path),
        });
      }
    } else {
      console.error("[ContextMenuAction] Element not found for path:", path);
    }
  }

  /**
   * Handle duplicate action with undo recording
   */
  private async handleDuplicate(path: string): Promise<void> {
    const copyResult = await this.fileActions.copyFile(path);
    // Record copy for undo if successful
    if (copyResult) {
      this.undoRedoHandler.recordOperation({
        type: "copy",
        timestamp: Date.now(),
        originalPath: copyResult.sourcePath,
        newPath: copyResult.destPath,
        isDirectory: this.callbacks.isItemDirectory(path),
      });
    }
  }
}
