/**
 * Workspace Keyboard Handler
 *
 * Handles keyboard shortcuts for the workspace files tree:
 * - Cut/Copy/Paste (Ctrl+X/C/V)
 * - Delete (Delete/Backspace)
 * - Rename (F2)
 * - New File/Folder (Ctrl+N, Ctrl+Shift+N)
 * - Undo/Redo (Ctrl+Z/Y)
 * - Search (Ctrl+K)
 * - Navigation (Arrow keys with Alt)
 */

import type { TreeConfig } from "../types";
import type { TreeStateManager } from "../_TreeState";
import type { SelectionHandler } from "./SelectionHandler";
import type { ClipboardHandler } from "./ClipboardHandler";
import type { UndoRedoHandler } from "./UndoRedoHandler";
import type { ContextMenuHandler } from "./ContextMenuHandler";
import type { FileActions } from "./FileActions";
import { TreeUtils } from "./TreeUtils";
import type { TreeItem } from "../types";

export interface KeyboardHandlerCallbacks {
  isItemDirectory: (path: string) => boolean;
  getParentPath: (path: string) => string;
  showSearchInput: () => void;
  showMessage: (message: string, type: "success" | "error" | "info") => void;
  handleContextMenuAction: (action: string, path: string) => Promise<void>;
  refresh: () => Promise<void>;
  getTreeData: () => TreeItem[];
}

export class WorkspaceKeyboardHandler {
  private config: TreeConfig;
  private container: HTMLElement;
  private stateManager: TreeStateManager;
  private selectionHandler: SelectionHandler;
  private clipboardHandler: ClipboardHandler;
  private undoRedoHandler: UndoRedoHandler;
  private contextMenuHandler: ContextMenuHandler;
  private fileActions: FileActions;
  private callbacks: KeyboardHandlerCallbacks;
  private boundHandler: ((e: KeyboardEvent) => void) | null = null;

  constructor(
    config: TreeConfig,
    container: HTMLElement,
    stateManager: TreeStateManager,
    selectionHandler: SelectionHandler,
    clipboardHandler: ClipboardHandler,
    undoRedoHandler: UndoRedoHandler,
    contextMenuHandler: ContextMenuHandler,
    fileActions: FileActions,
    callbacks: KeyboardHandlerCallbacks,
  ) {
    this.config = config;
    this.container = container;
    this.stateManager = stateManager;
    this.selectionHandler = selectionHandler;
    this.clipboardHandler = clipboardHandler;
    this.undoRedoHandler = undoRedoHandler;
    this.contextMenuHandler = contextMenuHandler;
    this.fileActions = fileActions;
    this.callbacks = callbacks;
  }

  initialize(): void {
    // Make container focusable
    this.container.setAttribute("tabindex", "0");

    // Focus container on click, but not when clicking on input/button elements
    this.container.addEventListener("click", (e) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "BUTTON" ||
        target.closest("button") ||
        target.isContentEditable
      ) {
        return;
      }
      this.container.focus();
    });

    // Use document-level listener to catch shortcuts
    this.boundHandler = (e: KeyboardEvent) => this.handleKeydown(e);
    document.addEventListener("keydown", this.boundHandler);
  }

  destroy(): void {
    if (this.boundHandler) {
      document.removeEventListener("keydown", this.boundHandler);
      this.boundHandler = null;
    }
  }

  private handleKeydown(e: KeyboardEvent): void {
    // Skip if user is typing in an input/textarea
    const target = e.target as HTMLElement;
    if (
      target.tagName === "INPUT" ||
      target.tagName === "TEXTAREA" ||
      target.isContentEditable
    ) {
      return;
    }

    // Skip if focus is in Monaco editor or Terminal
    const activeElement = document.activeElement as HTMLElement;
    const inMonacoOrTerminal = activeElement?.closest(
      ".monaco-editor, .xterm, .terminal-container, #editor-container",
    );
    if (inMonacoOrTerminal) {
      return;
    }

    const ctrlOrMeta = e.ctrlKey || e.metaKey;

    // Ctrl+K: Context-aware search shortcut
    // - Focus in sidebar (left) → file tree filtering
    // - Focus elsewhere (center/right) → tools search input
    if (ctrlOrMeta && e.key === "k") {
      e.preventDefault();
      e.stopPropagation();

      const sidebar = this.container.closest(
        ".stx-shell-sidebar, .stx-shell-sidebar__content",
      );
      const focusInSidebar =
        sidebar &&
        (sidebar.contains(activeElement) || sidebar.contains(e.target as Node));

      if (focusInSidebar) {
        // Focus is in the sidebar → file tree filtering
        this.callbacks.showSearchInput();
      } else {
        // Focus is in center/right → tools search bar
        const toolsSearchInput = document.getElementById(
          "searchInput",
        ) as HTMLInputElement | null;
        if (toolsSearchInput) {
          toolsSearchInput.focus();
          toolsSearchInput.select();
        } else {
          // Fallback to file tree filter if no tools search exists
          const isVisible =
            this.container.offsetParent !== null ||
            this.container.offsetWidth > 0;
          if (isVisible) {
            this.callbacks.showSearchInput();
          }
        }
      }
      return;
    }

    // For all other shortcuts, require focus inside the tree/sidebar
    const sidebar = this.container.closest(
      ".stx-shell-sidebar, .stx-shell-sidebar__content",
    );
    const isOurTree =
      this.container.contains(e.target as Node) ||
      document.activeElement === this.container ||
      this.container.contains(document.activeElement) ||
      (sidebar &&
        (sidebar.contains(e.target as Node) ||
          sidebar.contains(document.activeElement)));
    if (!isOurTree) {
      return;
    }

    // --- Dired-style bare-key shortcuts (no modifier) ---
    if (!ctrlOrMeta && !e.altKey && !e.shiftKey) {
      if (e.key === "g") {
        e.preventDefault();
        this.callbacks.refresh();
        return;
      }
      if (e.key === "+" || e.key === "=") {
        e.preventDefault();
        const sel = this.stateManager.getSelected();
        const targetPath =
          sel && this.callbacks.isItemDirectory(sel)
            ? sel
            : sel
              ? this.callbacks.getParentPath(sel)
              : "";
        this.fileActions.createNewFolder(targetPath);
        return;
      }
      if (e.key === "/") {
        e.preventDefault();
        this.callbacks.showSearchInput();
        return;
      }
    }

    const selectedPaths = this.selectionHandler.getSelectedPaths();
    const selected = this.stateManager.getSelected();

    // Ctrl+Z: Undo
    if (ctrlOrMeta && e.key === "z" && !e.shiftKey) {
      e.preventDefault();
      e.stopPropagation();
      this.undoRedoHandler.undo();
      return;
    }

    // Ctrl+Y or Ctrl+Shift+Z: Redo
    if (
      (ctrlOrMeta && e.key === "y") ||
      (ctrlOrMeta && e.shiftKey && e.key === "Z")
    ) {
      e.preventDefault();
      e.stopPropagation();
      this.undoRedoHandler.redo();
      return;
    }

    // Escape: Clear selection and cancel cut operation
    if (e.key === "Escape") {
      e.preventDefault();
      this.selectionHandler.clearSelection();
      this.contextMenuHandler.hide();
      if (this.clipboardHandler.hasClipboard()) {
        this.clipboardHandler.clearClipboard();
        this.callbacks.showMessage("Cut cancelled", "info");
      }
      return;
    }

    // Ctrl+Shift+N: New Folder
    if (ctrlOrMeta && e.shiftKey && (e.key === "N" || e.key === "n")) {
      e.preventDefault();
      e.stopPropagation();
      const targetPath =
        selected && this.callbacks.isItemDirectory(selected)
          ? selected
          : selected
            ? this.callbacks.getParentPath(selected)
            : "";
      this.fileActions.createNewFolder(targetPath);
      return;
    }

    // Ctrl+N: New File
    if (ctrlOrMeta && !e.shiftKey && (e.key === "N" || e.key === "n")) {
      e.preventDefault();
      e.stopPropagation();
      const targetPath =
        selected && this.callbacks.isItemDirectory(selected)
          ? selected
          : selected
            ? this.callbacks.getParentPath(selected)
            : "";
      this.fileActions.createNewFile(targetPath);
      return;
    }

    // === Selection-required shortcuts ===
    if (selectedPaths.length === 0 && !selected) {
      return;
    }

    // Ctrl+C: Copy
    if (ctrlOrMeta && e.key === "c") {
      e.preventDefault();
      e.stopPropagation();
      this.clipboardHandler.copy();
    }
    // Ctrl+X: Cut
    else if (ctrlOrMeta && e.key === "x") {
      e.preventDefault();
      e.stopPropagation();
      this.clipboardHandler.cut();
    }
    // Ctrl+V: Paste
    else if (ctrlOrMeta && e.key === "v") {
      e.preventDefault();
      e.stopPropagation();
      if (selected) {
        const targetPath = this.callbacks.isItemDirectory(selected)
          ? selected
          : this.callbacks.getParentPath(selected);
        this.clipboardHandler.paste(targetPath);
      } else {
        this.clipboardHandler.paste("");
      }
    }
    // Delete or Backspace: Delete selected files
    else if (e.key === "Delete" || e.key === "Backspace") {
      e.preventDefault();
      e.stopPropagation();
      const pathsToDelete =
        selectedPaths.length > 0
          ? selectedPaths
          : selected && selected !== ""
            ? [selected]
            : [];

      if (pathsToDelete.length > 0) {
        this.callbacks.handleContextMenuAction("delete", pathsToDelete[0]);
      }
    }
    // F2: Rename
    else if (e.key === "F2") {
      e.preventDefault();
      e.stopPropagation();
      const pathToRename =
        selectedPaths.length > 0 ? selectedPaths[0] : selected;
      if (pathToRename && pathToRename !== "") {
        const el = this.container.querySelector(
          `[data-path="${pathToRename}"]`,
        ) as HTMLElement;
        if (el) this.fileActions.startRename(pathToRename, el);
      }
    }
    // Ctrl+A: Select all
    else if (ctrlOrMeta && e.key === "a") {
      e.preventDefault();
      this.selectionHandler.selectAll();
    }
    // F5: Refresh tree
    else if (e.key === "F5") {
      e.preventDefault();
      e.stopPropagation();
      this.callbacks.refresh();
    }
    // Alt+ArrowUp: Navigate to parent folder
    else if (e.altKey && e.key === "ArrowUp") {
      e.preventDefault();
      e.stopPropagation();
      if (selected) {
        const parentPath = this.callbacks.getParentPath(selected);
        if (parentPath !== selected) {
          this.selectionHandler.select(parentPath, false);
        }
      }
    }
    // Alt+ArrowRight: Navigate to first child (if folder)
    else if (e.altKey && e.key === "ArrowRight") {
      e.preventDefault();
      e.stopPropagation();
      if (selected && this.callbacks.isItemDirectory(selected)) {
        if (!this.stateManager.isExpanded(selected)) {
          this.fileActions.toggleFolder(selected);
        }
        const item = TreeUtils.findItem(selected, this.callbacks.getTreeData());
        if (item?.children && item.children.length > 0) {
          this.selectionHandler.select(item.children[0].path, false);
        }
      }
    }
  }
}
