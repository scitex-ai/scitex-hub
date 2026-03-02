/**
 * File Operations Handler
 * Handles move, copy, and symlink operations for file tree items
 */

import type { TreeConfig } from "../types";
import type { FileOperation } from "./UndoRedoHandler";

export class FileOperations {
  private config: TreeConfig;
  private getCsrfToken: () => string;
  private refresh: () => Promise<void>;
  private showMessage: (
    message: string,
    type: "success" | "error" | "info",
  ) => void;
  private recordOperation: ((op: FileOperation) => void) | null = null;

  constructor(
    config: TreeConfig,
    getCsrfToken: () => string,
    refresh: () => Promise<void>,
    showMessage?: (message: string, type: "success" | "error" | "info") => void,
  ) {
    this.config = config;
    this.getCsrfToken = getCsrfToken;
    this.refresh = refresh;
    this.showMessage =
      showMessage || ((msg, type) => console.log(`[FileOps] ${type}: ${msg}`));
  }

  /** Set callback to record operations for undo/redo */
  setRecordOperation(callback: (op: FileOperation) => void): void {
    this.recordOperation = callback;
  }

  /** Move multiple files/folders to a new location (inside target folder) */
  async moveFiles(
    sourcePaths: string[],
    targetFolderPath: string,
  ): Promise<void> {
    if (sourcePaths.length === 0) return;

    // Filter out paths that would be moved into themselves or their children
    const validPaths = sourcePaths.filter((src) => {
      // Don't move a folder into itself or its children
      if (targetFolderPath.startsWith(src + "/") || targetFolderPath === src) {
        return false;
      }
      return true;
    });

    if (validPaths.length === 0) {
      this.showMessage("Cannot move folder into itself", "error");
      return;
    }

    const count = validPaths.length;
    this.showMessage(`Moving ${count} item${count > 1 ? "s" : ""}...`, "info");

    let successCount = 0;
    let errorCount = 0;

    for (const sourcePath of validPaths) {
      try {
        const fileName = sourcePath.split("/").pop() || sourcePath;
        const destPath = targetFolderPath
          ? `${targetFolderPath}/${fileName}`
          : fileName;

        const response = await fetch(
          `/${this.config.username}/${this.config.slug}/api/files/move/`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": this.getCsrfToken(),
            },
            body: JSON.stringify({
              source_path: sourcePath,
              dest_path: destPath,
            }),
          },
        );

        const data = await response.json();
        if (data.success) {
          successCount++;
          // Record for undo
          if (this.recordOperation) {
            this.recordOperation({
              type: "move",
              timestamp: Date.now(),
              originalPath: sourcePath,
              newPath: destPath,
              isDirectory:
                sourcePath.endsWith("/") || !sourcePath.includes("."),
            });
          }
        } else {
          console.error(`[FileOps] Failed to move ${sourcePath}:`, data.error);
          errorCount++;
        }
      } catch (error) {
        console.error(`[FileOps] Error moving ${sourcePath}:`, error);
        errorCount++;
      }
    }

    if (successCount > 0) {
      await this.refresh();
      if (errorCount > 0) {
        this.showMessage(
          `Moved ${successCount} item${successCount > 1 ? "s" : ""} (${errorCount} failed)`,
          "info",
        );
      } else {
        this.showMessage(
          `Moved ${successCount} item${successCount > 1 ? "s" : ""} (Ctrl+Z to undo)`,
          "success",
        );
      }
    } else {
      this.showMessage("Failed to move items", "error");
    }
  }

  /** Move single file/folder to a new location (inside target folder) - legacy single-file method */
  async moveFile(sourcePath: string, targetFolderPath: string): Promise<void> {
    await this.moveFiles([sourcePath], targetFolderPath);
  }

  /** Copy multiple files/folders to a new location (Ctrl+drag) */
  async copyFiles(
    sourcePaths: string[],
    targetFolderPath: string,
  ): Promise<void> {
    if (sourcePaths.length === 0) return;

    const count = sourcePaths.length;
    this.showMessage(`Copying ${count} item${count > 1 ? "s" : ""}...`, "info");

    let successCount = 0;
    let errorCount = 0;

    for (const sourcePath of sourcePaths) {
      try {
        const fileName = sourcePath.split("/").pop() || sourcePath;
        const destPath = targetFolderPath
          ? `${targetFolderPath}/${fileName}`
          : fileName;

        const response = await fetch(
          `/${this.config.username}/${this.config.slug}/api/files/copy/`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": this.getCsrfToken(),
            },
            body: JSON.stringify({
              source_path: sourcePath,
              dest_path: destPath,
            }),
          },
        );

        const data = await response.json();
        if (data.success) {
          successCount++;
          if (this.recordOperation) {
            this.recordOperation({
              type: "copy",
              timestamp: Date.now(),
              originalPath: sourcePath,
              newPath: destPath,
              isDirectory:
                sourcePath.endsWith("/") || !sourcePath.includes("."),
            });
          }
        } else {
          console.error(`[FileOps] Failed to copy ${sourcePath}:`, data.error);
          errorCount++;
        }
      } catch (error) {
        console.error(`[FileOps] Error copying ${sourcePath}:`, error);
        errorCount++;
      }
    }

    if (successCount > 0) {
      await this.refresh();
      this.showMessage(
        `Copied ${successCount} item${successCount > 1 ? "s" : ""} (Ctrl+Z to undo)`,
        "success",
      );
    } else {
      this.showMessage("Failed to copy items", "error");
    }
  }

  /** Create symlinks for multiple files/folders (Alt+drag) */
  async createSymlinks(
    sourcePaths: string[],
    targetFolderPath: string,
  ): Promise<void> {
    if (sourcePaths.length === 0) return;

    const count = sourcePaths.length;
    this.showMessage(
      `Creating ${count} symlink${count > 1 ? "s" : ""}...`,
      "info",
    );

    let successCount = 0;
    let errorCount = 0;

    for (const sourcePath of sourcePaths) {
      try {
        const fileName = sourcePath.split("/").pop() || sourcePath;
        const linkPath = targetFolderPath
          ? `${targetFolderPath}/${fileName}`
          : fileName;

        const response = await fetch(
          `/${this.config.username}/${this.config.slug}/api/files/symlink/`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": this.getCsrfToken(),
            },
            body: JSON.stringify({ source: sourcePath, target: linkPath }),
          },
        );

        const data = await response.json();
        if (data.success) {
          successCount++;
        } else {
          console.error(
            `[FileOps] Failed to create symlink for ${sourcePath}:`,
            data.error,
          );
          errorCount++;
        }
      } catch (error) {
        console.error(
          `[FileOps] Error creating symlink for ${sourcePath}:`,
          error,
        );
        errorCount++;
      }
    }

    if (successCount > 0) {
      await this.refresh();
      this.showMessage(
        `Created ${successCount} symlink${successCount > 1 ? "s" : ""}`,
        "success",
      );
    } else {
      this.showMessage("Failed to create symlinks", "error");
    }
  }

  /** Create single symlink (legacy single-file method) */
  async createSymlink(sourcePath: string, targetPath: string): Promise<void> {
    try {
      const response = await fetch(
        `/${this.config.username}/${this.config.slug}/api/files/symlink/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": this.getCsrfToken(),
          },
          body: JSON.stringify({ source: sourcePath, target: targetPath }),
        },
      );

      const data = await response.json();
      if (data.success) {
        this.showMessage("Symlink created", "success");
        await this.refresh();
      } else {
        this.showMessage(`Failed: ${data.error}`, "error");
      }
    } catch (error) {
      this.showMessage("Failed to create symlink", "error");
    }
  }
}
