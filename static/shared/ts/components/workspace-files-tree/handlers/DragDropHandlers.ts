/**
 * Drag and Drop Handlers for WorkspaceFilesTree
 * Handles file/folder drag and drop operations including external file uploads
 * Supports multi-selection: when dragging a selected item, all selected items move together
 * Supports dragging files to external components (e.g., tools iframe)
 */

import type { TreeConfig } from "../types.ts";
import type { FileOperation } from "./UndoRedoHandler.ts";
import { FileOperations } from "./FileOperations.ts";
import { FileUpload } from "./FileUpload.ts";
import { DragState } from "./DragState.ts";

export class DragDropHandlers {
  private showMessage: (
    message: string,
    type: "success" | "error" | "info",
  ) => void;
  private getSelectedPaths: () => string[];
  private isItemSelected: (path: string) => boolean;
  private fileOps: FileOperations;
  private fileUpload: FileUpload;
  private dragState: DragState;

  constructor(
    private config: TreeConfig,
    private getCsrfToken: () => string,
    private refresh: () => Promise<void>,
    showMessage?: (message: string, type: "success" | "error" | "info") => void,
    getSelectedPaths?: () => string[],
    isItemSelected?: (path: string) => boolean,
  ) {
    this.showMessage =
      showMessage || ((msg, type) => console.log(`[DragDrop] ${type}: ${msg}`));
    this.getSelectedPaths = getSelectedPaths || (() => []);
    this.isItemSelected = isItemSelected || (() => false);

    // Initialize modules
    this.fileOps = new FileOperations(
      config,
      getCsrfToken,
      refresh,
      showMessage,
    );
    this.fileUpload = new FileUpload(
      config,
      getCsrfToken,
      refresh,
      showMessage,
    );
    this.dragState = new DragState();
  }

  /** Set callback to record operations for undo/redo */
  setRecordOperation(callback: (op: FileOperation) => void): void {
    this.fileOps.setRecordOperation(callback);
  }

  attachDragDropListeners(container: HTMLElement): void {
    const treeEl = container.querySelector(".wft-tree");
    if (!treeEl) return;

    // Make the entire tree container a drop zone for external files
    this.attachContainerDropZone(container);

    // Make items draggable (internal drag) - supports multi-selection
    treeEl.addEventListener("dragstart", (e) => {
      const dragEvent = e as DragEvent;
      const target = dragEvent.target as HTMLElement;
      const item = target.closest("[data-path]");
      if (item && dragEvent.dataTransfer) {
        const path = item.getAttribute("data-path")!;

        // Don't allow dragging root
        if (path === "") {
          console.log("[DragDrop] Cannot drag root item");
          dragEvent.preventDefault();
          return;
        }

        // Track modifier keys at drag start
        this.dragState.dragModifiers = {
          alt: dragEvent.altKey,
          ctrl: dragEvent.ctrlKey || dragEvent.metaKey,
        };

        // Check if this item is part of multi-selection
        if (this.isItemSelected(path)) {
          // Drag all selected items
          this.dragState.draggedPaths = this.getSelectedPaths().filter(
            (p) => p !== "",
          ); // Exclude root
        } else {
          // Drag only this item
          this.dragState.draggedPaths = [path];
        }

        const operation = this.dragState.dragModifiers.alt
          ? "symlink"
          : this.dragState.dragModifiers.ctrl
            ? "copy"
            : "move";
        console.log(
          "[DragDrop] dragstart - paths:",
          this.dragState.draggedPaths,
          "operation:",
          operation,
        );

        // Store all paths in dataTransfer (semicolon-separated for multiple)
        dragEvent.dataTransfer.setData(
          "text/plain",
          this.dragState.draggedPaths.join(";"),
        );
        dragEvent.dataTransfer.setData("application/x-wft-internal", "true");
        dragEvent.dataTransfer.setData(
          "application/x-wft-count",
          String(this.dragState.draggedPaths.length),
        );
        dragEvent.dataTransfer.setData(
          "application/x-wft-operation",
          operation,
        );
        dragEvent.dataTransfer.effectAllowed = "copy";

        // Add external drag metadata for cross-component drag (to tools iframe)
        // Store structured data for tools to consume
        const dragData = this.dragState.draggedPaths.map((p) => {
          const name = p.split("/").pop() || p;
          return { path: p, name, type: "file" };
        });
        dragEvent.dataTransfer.setData(
          "application/x-scitex-file",
          JSON.stringify(dragData),
        );

        // Mark all dragged items visually (source items)
        this.dragState.markDraggedItems(container, this.dragState.draggedPaths);

        // Show count badge if multiple items
        this.dragState.showDragCountBadge(this.dragState.draggedPaths.length);
      }
    });

    // Drag over folder or root (for internal moves)
    treeEl.addEventListener("dragover", (e) => {
      const dragEvent = e as DragEvent;
      dragEvent.preventDefault();
      const target = dragEvent.target as HTMLElement;
      // Allow drop on folders AND root item
      const dropTarget = target.closest(
        ".wft-folder[data-path], .wft-root[data-path]",
      );

      // Clear previous drop targets first
      treeEl.querySelectorAll(".wft-drop-target").forEach((el) => {
        if (el !== dropTarget) {
          el.classList.remove("wft-drop-target");
        }
      });

      if (dropTarget && dragEvent.dataTransfer) {
        // Don't allow dropping on itself or its children
        const targetPath = dropTarget.getAttribute("data-path") || "";
        const isValidTarget = !this.dragState.draggedPaths.some(
          (p) => targetPath === p || targetPath.startsWith(p + "/"),
        );

        if (isValidTarget) {
          dragEvent.dataTransfer.dropEffect = "move";
          dropTarget.classList.add("wft-drop-target");
        } else {
          dragEvent.dataTransfer.dropEffect = "none";
          dropTarget.classList.remove("wft-drop-target");
        }
      }
    });

    // Drag leave
    treeEl.addEventListener("dragleave", (e) => {
      const dragEvent = e as DragEvent;
      const target = dragEvent.target as HTMLElement;
      const dropTarget = target.closest(
        ".wft-folder[data-path], .wft-root[data-path]",
      );
      if (dropTarget) {
        // Small delay to prevent flicker when moving between elements
        setTimeout(() => {
          if (!dropTarget.matches(":hover")) {
            dropTarget.classList.remove("wft-drop-target");
          }
        }, 50);
      }
    });

    // Drop on folder or root (internal move or external file upload)
    treeEl.addEventListener("drop", async (e) => {
      const dragEvent = e as DragEvent;
      dragEvent.preventDefault();
      dragEvent.stopPropagation();

      const target = dragEvent.target as HTMLElement;
      // Allow drop on folders AND root item
      const dropTarget = target.closest(
        ".wft-folder[data-path], .wft-root[data-path]",
      );

      console.log(
        "[DragDrop] drop event - dropTarget:",
        dropTarget?.getAttribute("data-path"),
        "target element:",
        target.className,
      );

      if (dragEvent.dataTransfer) {
        // Check if this is an external file drop
        const files = dragEvent.dataTransfer.files;
        const isInternal = dragEvent.dataTransfer.types.includes(
          "application/x-wft-internal",
        );

        console.log(
          "[DragDrop] drop - isInternal:",
          isInternal,
          "files:",
          files.length,
          "types:",
          Array.from(dragEvent.dataTransfer.types),
        );

        if (files.length > 0 && !isInternal) {
          // External file upload to specific folder (or root if no folder)
          const targetPath = dropTarget?.getAttribute("data-path") || "";
          console.log("[DragDrop] External file upload to:", targetPath);
          await this.fileUpload.uploadFiles(files, targetPath);
        } else if (dropTarget && isInternal) {
          // Internal operation - supports multiple files
          const sourceData = dragEvent.dataTransfer.getData("text/plain");
          const targetPath = dropTarget.getAttribute("data-path") || "";
          const sourcePaths = sourceData
            .split(";")
            .filter((p) => p && p !== targetPath);
          const operation =
            dragEvent.dataTransfer.getData("application/x-wft-operation") ||
            "move";

          console.log(
            "[DragDrop] Internal",
            operation,
            "- sourcePaths:",
            sourcePaths,
            "to targetPath:",
            targetPath,
          );

          if (sourcePaths.length > 0) {
            if (operation === "symlink") {
              await this.fileOps.createSymlinks(sourcePaths, targetPath);
            } else if (operation === "copy") {
              await this.fileOps.copyFiles(sourcePaths, targetPath);
            } else {
              await this.fileOps.moveFiles(sourcePaths, targetPath);
            }
          } else {
            console.log("[DragDrop] No valid source paths for operation");
          }
        } else {
          console.log(
            "[DragDrop] Drop ignored - no valid drop target or not internal",
          );
        }
      }

      // Clean up
      this.dragState.reset();
      this.dragState.cleanupDragState(container);
    });

    // Drag end
    treeEl.addEventListener("dragend", () => {
      this.dragState.cleanupDragState(container);
    });
  }

  /** Attach drop zone to the entire container for external file uploads */
  private attachContainerDropZone(container: HTMLElement): void {
    let dragCounter = 0;

    // Prevent default drag behaviors on the whole container
    container.addEventListener("dragenter", (e) => {
      e.preventDefault();
      dragCounter++;
      const dragEvent = e as DragEvent;

      // Only show drop zone for external files
      if (dragEvent.dataTransfer?.types.includes("Files")) {
        container.classList.add("wft-drop-zone-active");
      }
    });

    container.addEventListener("dragover", (e) => {
      e.preventDefault();
      const dragEvent = e as DragEvent;
      if (dragEvent.dataTransfer) {
        dragEvent.dataTransfer.dropEffect = "copy";
      }
    });

    container.addEventListener("dragleave", (e) => {
      e.preventDefault();
      dragCounter--;
      if (dragCounter === 0) {
        container.classList.remove("wft-drop-zone-active");
      }
    });

    container.addEventListener("drop", async (e) => {
      e.preventDefault();
      dragCounter = 0;
      container.classList.remove("wft-drop-zone-active");

      const dragEvent = e as DragEvent;
      if (dragEvent.dataTransfer) {
        const files = dragEvent.dataTransfer.files;
        const isInternal = dragEvent.dataTransfer.types.includes(
          "application/x-wft-internal",
        );

        const target = dragEvent.target as HTMLElement;
        // Check for folder or root as drop target
        const dropTarget = target.closest(
          ".wft-folder[data-path], .wft-root[data-path]",
        );
        const targetPath = dropTarget?.getAttribute("data-path") || "";

        // Handle file drop
        if (files.length > 0 && !isInternal) {
          if (!dropTarget) {
            await this.fileUpload.uploadFiles(files, "");
          }
          return;
        }

        // Handle URL drop (from web pages, MS Office, etc.)
        const droppedUrl =
          dragEvent.dataTransfer.getData("text/uri-list") ||
          dragEvent.dataTransfer.getData("text/plain");
        if (
          droppedUrl &&
          !isInternal &&
          this.fileUpload.isDownloadableUrl(droppedUrl)
        ) {
          await this.fileUpload.downloadAndUploadFromUrl(
            droppedUrl,
            targetPath,
          );
        }
      }
    });
  }
}
