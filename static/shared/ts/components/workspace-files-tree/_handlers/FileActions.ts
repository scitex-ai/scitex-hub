/**
 * File Actions for WorkspaceFilesTree
 * Handles file/folder operations (toggle, select, rename, etc.)
 */

import type { TreeItem, TreeConfig } from "../types";
import type { TreeStateManager } from "../_TreeState";
import { attachInlineInput } from "./_InlineInputHelper";

export class FileActions {
  constructor(
    private config: TreeConfig,
    private stateManager: TreeStateManager,
    private getTreeData: () => TreeItem[],
    private getCsrfToken: () => string,
    private rerender: () => void,
    private emitEvent: (type: string, detail: any) => void,
    private refreshTree?: () => Promise<void>,
  ) {}

  toggleFolder(path: string): void {
    const wasExpanded = this.stateManager.isExpanded(path);
    this.stateManager.toggle(path);

    // Auto-select folder when expanding
    if (!wasExpanded) {
      this.stateManager.setSelected(path);
    }
  }

  /** Select (highlight) without opening */
  selectFile(path: string): void {
    this.stateManager.setSelected(path);
    this.emitEvent("file-select", { path });
  }

  /** Open file in viewer/editor (double-click) */
  openFile(path: string): void {
    this.stateManager.setSelected(path);
    this.emitEvent("file-open", { path });
  }

  /** Run file in terminal (triple-click) */
  runFile(path: string): void {
    document.dispatchEvent(new CustomEvent("run-file", { detail: { path } }));
  }

  findItem(path: string): TreeItem | null {
    const search = (items: TreeItem[]): TreeItem | null => {
      for (const item of items) {
        if (item.path === path) return item;
        if (item.children) {
          const found = search(item.children);
          if (found) return found;
        }
      }
      return null;
    };
    return search(this.getTreeData());
  }

  async startRename(
    path: string,
    itemEl: HTMLElement,
  ): Promise<{ newPath: string } | null> {
    const item = this.findItem(path);
    if (!item) {
      console.error(
        "[FileActions] startRename: item not found for path:",
        path,
      );
      return null;
    }

    // Find the name element within the item
    const nameEl = itemEl.querySelector(
      ".wft-name, .wft-file-name, .wft-folder-name",
    ) as HTMLElement;
    if (!nameEl) {
      console.error(
        "[FileActions] startRename: name element not found in:",
        itemEl,
      );
      return null;
    }

    const originalName = item.name;
    const isDirectory = item.type === "directory";

    // Create input to replace the name text only (keep icon as is)
    const input = document.createElement("input");
    input.type = "text";
    input.value = originalName;
    input.className = "wft-inline-input";

    // Replace name element with input
    nameEl.replaceWith(input);

    input.focus();
    // Select filename without extension for files
    if (!isDirectory && originalName.includes(".")) {
      const extIndex = originalName.lastIndexOf(".");
      input.setSelectionRange(0, extIndex);
    } else {
      input.select();
    }

    // Return a promise that resolves when rename completes
    return new Promise((resolve) => {
      let resolved = false;

      const cleanup = () => {
        input.replaceWith(nameEl);
      };

      const finishRename = async (save: boolean) => {
        if (resolved) return;
        resolved = true;

        const newName = input.value.trim();
        cleanup();

        if (save && newName && newName !== originalName) {
          const newPath = await this.performRename(path, newName);
          resolve(newPath ? { newPath } : null);
        } else {
          resolve(null);
        }
      };

      input.addEventListener("blur", () => {
        // Small delay to allow click events to fire first
        setTimeout(() => finishRename(true), 100);
      });
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          finishRename(true);
        } else if (e.key === "Escape") {
          e.preventDefault();
          finishRename(false);
        }
      });
    });
  }

  private async performRename(
    oldPath: string,
    newName: string,
  ): Promise<string | null> {
    try {
      const response = await fetch(
        `/${this.config.ownerUsername}/${this.config.projectSlug}/api/files/rename/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": this.getCsrfToken(),
          },
          body: JSON.stringify({ old_path: oldPath, new_name: newName }),
        },
      );

      const data = await response.json();
      if (data.success) {
        this.emitEvent("file-rename", { oldPath, newPath: data.new_path });
        // Trigger full tree reload to reflect changes from server
        if (this.refreshTree) {
          await this.refreshTree();
        } else {
          this.rerender();
        }
        return data.new_path;
      } else {
        console.error("[FileActions] Rename failed:", data.error);
        return null;
      }
    } catch (error) {
      console.error("[FileActions] Error renaming file:", error);
      return null;
    }
  }

  async deleteFile(path: string): Promise<void> {
    // No confirmation - delete directly (files can be recovered via git)
    try {
      const response = await fetch(
        `/${this.config.ownerUsername}/${this.config.projectSlug}/api/files/delete/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": this.getCsrfToken(),
          },
          body: JSON.stringify({ path }),
        },
      );

      const data = await response.json();
      if (data.success) {
        console.log("[FileActions] File deleted:", path);
        this.emitEvent("file-delete", { path });
        // Trigger full tree reload to reflect changes from server
        if (this.refreshTree) {
          await this.refreshTree();
        } else {
          this.rerender();
        }
      } else {
        console.error("[FileActions] Delete failed:", data.error);
        alert(`Failed to delete file: ${data.error}`);
      }
    } catch (error) {
      console.error("[FileActions] Error deleting file:", error);
      alert("Error deleting file. Please try again.");
    }
  }

  async createNewFile(folderPath: string): Promise<void> {
    // Expand the folder first to show inline input (not needed for root)
    if (folderPath) {
      this.stateManager.expand(folderPath);
    }
    this.rerender();

    // Wait for DOM update then insert inline input
    requestAnimationFrame(() => {
      this.insertInlineInput(folderPath, "file");
    });
  }

  private insertInlineInput(
    folderPath: string,
    type: "file" | "directory",
  ): void {
    const onSubmit = async (name: string): Promise<void> => {
      await this.performCreate(folderPath, name, type);
    };

    // Handle root (empty path) — insert after root item in .wft-tree
    if (folderPath === "") {
      const treeEl = document.querySelector(".wft-tree") as HTMLElement | null;
      const rootItem = treeEl?.querySelector(".wft-root") as HTMLElement | null;
      if (treeEl && rootItem) {
        attachInlineInput({
          container: treeEl,
          insertMode: "after-sibling",
          sibling: rootItem,
          type,
          onSubmit,
        });
      }
      return;
    }

    // Find the folder's children container
    const folderEl = document.querySelector(
      `.wft-folder[data-path="${folderPath}"]`,
    );
    if (!folderEl) return;

    const childrenContainer = folderEl.nextElementSibling as HTMLElement;
    if (
      !childrenContainer ||
      !childrenContainer.classList.contains("wft-children")
    ) {
      // Folder has no children container — create one
      const newContainer = document.createElement("div");
      newContainer.className = "wft-children expanded";
      folderEl.after(newContainer);
      attachInlineInput({
        container: newContainer,
        insertMode: "prepend",
        type,
        onSubmit,
      });
      return;
    }

    // Make sure children container is visible
    childrenContainer.style.display = "";
    childrenContainer.classList.add("expanded");

    attachInlineInput({
      container: childrenContainer,
      insertMode: "prepend",
      type,
      onSubmit,
    });
  }

  private async performCreate(
    folderPath: string,
    name: string,
    type: "file" | "directory",
  ): Promise<void> {
    const url = `/${this.config.ownerUsername}/${this.config.projectSlug}/api/files/create/`;
    const csrfToken = this.getCsrfToken();

    // Try to create, handling duplicates with suffix
    let finalName = name;
    let attempt = 0;
    const maxAttempts = 100;

    while (attempt < maxAttempts) {
      const newPath = folderPath ? `${folderPath}/${finalName}` : finalName;

      console.log(
        `[FileActions] Creating ${type} at:`,
        newPath,
        attempt > 0 ? `(attempt ${attempt + 1})` : "",
      );

      try {
        const response = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({
            path: newPath,
            type: type === "file" ? "file" : "directory",
          }),
        });

        const data = await response.json();
        if (data.success) {
          console.log(`[FileActions] ${type} created:`, newPath);
          this.emitEvent(type === "file" ? "file-create" : "folder-create", {
            path: newPath,
            type,
          });
          this.stateManager.expand(folderPath);
          // Trigger full tree reload to reflect changes from server
          if (this.refreshTree) {
            await this.refreshTree();
          } else {
            this.rerender();
          }
          return;
        } else if (data.error && data.error.includes("already exists")) {
          // File exists, try with suffix
          attempt++;
          finalName = this.getNameWithSuffix(name, attempt);
          continue;
        } else {
          console.error(`[FileActions] Create ${type} failed:`, data.error);
          alert(`Failed to create ${type}: ${data.error}`);
          return;
        }
      } catch (error) {
        console.error(`[FileActions] Error creating ${type}:`, error);
        alert(`Error creating ${type}. Please try again.`);
        return;
      }
    }

    alert(`Failed to create ${type}: too many files with similar names`);
  }

  private getNameWithSuffix(name: string, suffix: number): string {
    // For files: test.txt -> test (1).txt, test (2).txt, etc.
    // For folders/no extension: folder -> folder (1), folder (2), etc.
    const dotIndex = name.lastIndexOf(".");
    if (dotIndex > 0) {
      const baseName = name.substring(0, dotIndex);
      const ext = name.substring(dotIndex);
      return `${baseName} (${suffix})${ext}`;
    }
    return `${name} (${suffix})`;
  }

  async createNewFolder(folderPath: string): Promise<void> {
    // Expand the folder first to show inline input (not needed for root)
    if (folderPath) {
      this.stateManager.expand(folderPath);
    }
    this.rerender();

    // Wait for DOM update then insert inline input
    requestAnimationFrame(() => {
      this.insertInlineInput(folderPath, "directory");
    });
  }

  async copyFile(
    path: string,
  ): Promise<{ sourcePath: string; destPath: string } | null> {
    const item = this.findItem(path);
    if (!item) return null;

    // Generate copy name: file.txt -> file_copy.txt or folder -> folder_copy
    const parts = item.name.split(".");
    let copyName: string;
    if (parts.length > 1 && item.type === "file") {
      const ext = parts.pop();
      copyName = `${parts.join(".")}_copy.${ext}`;
    } else {
      copyName = `${item.name}_copy`;
    }

    const newName = prompt("Enter name for copy:", copyName);
    if (!newName || !newName.trim()) {
      return null;
    }

    // Get parent directory
    const pathParts = path.split("/");
    pathParts.pop();
    const parentPath = pathParts.join("/");
    const newPath = parentPath
      ? `${parentPath}/${newName.trim()}`
      : newName.trim();

    try {
      const response = await fetch(
        `/${this.config.ownerUsername}/${this.config.projectSlug}/api/files/copy/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": this.getCsrfToken(),
          },
          body: JSON.stringify({ source_path: path, dest_path: newPath }),
        },
      );

      const data = await response.json();
      if (data.success) {
        console.log("[FileActions] File copied:", path, "->", newPath);
        this.emitEvent("file-copy", { sourcePath: path, destPath: newPath });
        // Trigger full tree reload to reflect changes from server
        if (this.refreshTree) {
          await this.refreshTree();
        } else {
          this.rerender();
        }
        return { sourcePath: path, destPath: newPath };
      } else {
        console.error("[FileActions] Copy failed:", data.error);
        alert(`Failed to copy: ${data.error}`);
        return null;
      }
    } catch (error) {
      console.error("[FileActions] Error copying file:", error);
      alert("Error copying file. Please try again.");
      return null;
    }
  }
}
