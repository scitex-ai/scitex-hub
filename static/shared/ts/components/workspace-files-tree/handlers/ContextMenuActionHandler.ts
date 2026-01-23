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
    callbacks: ContextMenuActionCallbacks
  ) {
    this.config = config;
    this.selectionHandler = selectionHandler;
    this.clipboardHandler = clipboardHandler;
    this.undoRedoHandler = undoRedoHandler;
    this.fileActions = fileActions;
    this.gitActions = gitActions;
    this.callbacks = callbacks;
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

      case "new-file":
        await this.fileActions.createNewFile(path);
        break;

      case "new-folder":
        await this.fileActions.createNewFolder(path);
        break;

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
   * Handle delete action with undo recording
   */
  private async handleDelete(path: string): Promise<void> {
    const pathsToDelete = this.getPathsForOperation(path);
    console.log("[ContextMenuAction] Delete:", pathsToDelete);

    // Confirm if multiple files
    if (pathsToDelete.length > 1) {
      if (
        !confirm(`Delete ${pathsToDelete.length} items? (Ctrl+Z to undo)`)
      ) {
        return;
      }
    }

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
    const el = container?.querySelector(
      `[data-path="${path}"]`
    ) as HTMLElement;

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
