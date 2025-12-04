/**
 * Shared File Tab Manager
 * Handles tab display, switching, closing, and reordering for open files
 * Used by Code and Writer apps
 */

import type { OpenFile, FileTabsOptions, TabInfo } from "./types.js";

export class FileTabManager {
  private container: HTMLElement | null = null;
  private openFiles: Map<string, OpenFile> = new Map();
  private currentFile: string | null = null;
  private options: FileTabsOptions;
  private draggedTabPath: string | null = null;
  private existingFiles: string[] = [];

  constructor(options: FileTabsOptions) {
    this.options = {
      showNewFileButton: true,
      allowReorder: true,
      allowRename: true,
      ...options,
    };
    this.container = document.getElementById(options.containerId);
  }

  /**
   * Initialize with existing open files
   */
  initialize(openFiles: Map<string, OpenFile>, currentFile: string | null): void {
    this.openFiles = openFiles;
    this.currentFile = currentFile;
    this.render();
  }

  /**
   * Set the list of existing files (for new file name validation)
   */
  setExistingFiles(files: string[]): void {
    this.existingFiles = files;
  }

  /**
   * Get current file path
   */
  getCurrentFile(): string | null {
    return this.currentFile;
  }

  /**
   * Set current file and update UI
   */
  setCurrentFile(filePath: string | null): void {
    this.currentFile = filePath;
    this.render();
  }

  /**
   * Add a new tab
   */
  addTab(file: OpenFile): void {
    this.openFiles.set(file.path, file);
    this.render();
  }

  /**
   * Remove a tab
   */
  removeTab(filePath: string): void {
    this.openFiles.delete(filePath);
    this.render();
  }

  /**
   * Update tab dirty state
   */
  setTabDirty(filePath: string, isDirty: boolean): void {
    const file = this.openFiles.get(filePath);
    if (file) {
      file.isDirty = isDirty;
      this.render();
    }
  }

  /**
   * Get all open file paths
   */
  getOpenFilePaths(): string[] {
    return Array.from(this.openFiles.keys());
  }

  /**
   * Check if a file is open
   */
  hasFile(filePath: string): boolean {
    return this.openFiles.has(filePath);
  }

  /**
   * Switch to next tab
   */
  switchToNextTab(): void {
    const tabs = Array.from(this.openFiles.keys());
    if (tabs.length === 0) return;

    const currentIndex = tabs.indexOf(this.currentFile || "");
    const nextIndex = (currentIndex + 1) % tabs.length;
    this.options.onTabSwitch(tabs[nextIndex]);
  }

  /**
   * Switch to previous tab
   */
  switchToPreviousTab(): void {
    const tabs = Array.from(this.openFiles.keys());
    if (tabs.length === 0) return;

    const currentIndex = tabs.indexOf(this.currentFile || "");
    const prevIndex = (currentIndex - 1 + tabs.length) % tabs.length;
    this.options.onTabSwitch(tabs[prevIndex]);
  }

  /**
   * Switch to tab by index (1-based for keyboard shortcuts)
   */
  switchToTabByIndex(index: number): void {
    const tabs = Array.from(this.openFiles.keys());
    if (index >= 0 && index < tabs.length) {
      this.options.onTabSwitch(tabs[index]);
    }
  }

  /**
   * Trigger new file input programmatically
   */
  triggerNewFileInput(): void {
    if (!this.container || !this.options.showNewFileButton) return;
    const plusBtn = this.container.querySelector(".file-tabs-plus-btn");
    if (plusBtn) {
      this.showInlineNewFileInput(plusBtn as HTMLElement);
    }
  }

  /**
   * Render all tabs
   */
  render(): void {
    if (!this.container) return;

    this.container.innerHTML = "";

    this.openFiles.forEach((file, path) => {
      const tab = this.createTabElement(path, file);
      this.container!.appendChild(tab);
    });

    if (this.options.showNewFileButton) {
      const newTabBtn = this.createNewTabButton();
      this.container.appendChild(newTabBtn);
    }
  }

  /**
   * Create a tab element
   */
  private createTabElement(path: string, file: OpenFile): HTMLButtonElement {
    const isPermanent = path === this.options.permanentTab;
    const isActive = path === this.currentFile;
    const fileName = path.split("/").pop() || path;

    const tab = document.createElement("button");
    tab.className = `file-tab ${isActive ? "active" : ""} ${file.isDirty ? "dirty" : ""}`;
    tab.dataset.filePath = path;
    tab.title = isPermanent
      ? `${path} - temporary workspace (not saved to disk)`
      : path;

    // Tab label
    const label = document.createElement("span");
    label.className = "file-tab-name";
    label.textContent = fileName;
    tab.appendChild(label);

    // Dirty indicator
    if (file.isDirty) {
      const dirtyDot = document.createElement("span");
      dirtyDot.className = "file-tab-dirty";
      dirtyDot.textContent = "●";
      tab.appendChild(dirtyDot);
    }

    // Close button (not for permanent tabs)
    if (!isPermanent) {
      const closeBtn = document.createElement("span");
      closeBtn.className = "file-tab-close";
      closeBtn.innerHTML = "×";
      closeBtn.title = "Close file";
      closeBtn.onclick = (e) => {
        e.stopPropagation();
        this.options.onTabClose(path);
      };
      tab.appendChild(closeBtn);
    }

    // Tab click handler
    tab.onclick = () => {
      this.options.onTabSwitch(path);
    };

    // Double-click to rename (for regular files only)
    if (!isPermanent && this.options.allowRename && this.options.onRenameFile) {
      tab.ondblclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.startInlineRename(path, label);
      };
    }

    // Drag and drop reordering
    if (this.options.allowReorder) {
      this.setupDragAndDrop(tab, path);
    }

    return tab;
  }

  /**
   * Setup drag and drop for tab reordering
   */
  private setupDragAndDrop(tab: HTMLButtonElement, path: string): void {
    tab.draggable = true;

    tab.ondragstart = (e) => {
      this.draggedTabPath = path;
      tab.classList.add("dragging");
      if (e.dataTransfer) {
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", path);
      }
    };

    tab.ondragend = () => {
      this.draggedTabPath = null;
      tab.classList.remove("dragging");
      this.container?.querySelectorAll(".file-tab").forEach((t) => {
        t.classList.remove("drag-over");
      });
    };

    tab.ondragover = (e) => {
      e.preventDefault();
      if (this.draggedTabPath && this.draggedTabPath !== path) {
        tab.classList.add("drag-over");
      }
    };

    tab.ondragleave = () => {
      tab.classList.remove("drag-over");
    };

    tab.ondrop = (e) => {
      e.preventDefault();
      tab.classList.remove("drag-over");
      if (this.draggedTabPath && this.draggedTabPath !== path) {
        this.reorderTabs(this.draggedTabPath, path);
      }
    };
  }

  /**
   * Reorder tabs by moving draggedPath before targetPath
   */
  private reorderTabs(draggedPath: string, targetPath: string): void {
    const entries = Array.from(this.openFiles.entries());
    const draggedIndex = entries.findIndex(([p]) => p === draggedPath);
    const targetIndex = entries.findIndex(([p]) => p === targetPath);

    if (draggedIndex === -1 || targetIndex === -1) return;

    const [draggedEntry] = entries.splice(draggedIndex, 1);
    const newTargetIndex = draggedIndex < targetIndex ? targetIndex - 1 : targetIndex;
    entries.splice(newTargetIndex, 0, draggedEntry);

    this.openFiles.clear();
    entries.forEach(([p, file]) => {
      this.openFiles.set(p, file);
    });

    this.render();
  }

  /**
   * Create the new tab button
   */
  private createNewTabButton(): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.className = "file-tabs-plus-btn";
    btn.innerHTML = "+";
    btn.title = "New file (Ctrl+N)";
    btn.onclick = () => {
      this.showInlineNewFileInput(btn);
    };
    return btn;
  }

  /**
   * Show inline input for creating a new file
   */
  private showInlineNewFileInput(plusBtn: HTMLElement): void {
    if (!this.container || !this.options.onNewFile) return;

    const existingInput = this.container.querySelector(".inline-new-file-input");
    if (existingInput) {
      (existingInput as HTMLInputElement).focus();
      return;
    }

    const inputWrapper = document.createElement("div");
    inputWrapper.className = "file-tab inline-new-file-wrapper";

    const input = document.createElement("input");
    input.type = "text";
    input.className = "inline-new-file-input";
    input.placeholder = "filename.tex";
    input.value = this.getNextAvailableFilename("untitled.tex");

    inputWrapper.appendChild(input);
    this.container.insertBefore(inputWrapper, plusBtn);

    input.focus();
    input.select();

    const finishCreate = async () => {
      const fileName = input.value.trim();
      inputWrapper.remove();
      if (fileName && this.options.onNewFile) {
        await this.options.onNewFile(fileName);
      }
    };

    const cancelCreate = () => {
      inputWrapper.remove();
    };

    input.onblur = () => {
      setTimeout(() => {
        if (document.activeElement !== input) {
          finishCreate();
        }
      }, 100);
    };

    input.onkeydown = (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        finishCreate();
      } else if (e.key === "Escape") {
        e.preventDefault();
        cancelCreate();
      }
    };
  }

  /**
   * Start inline rename for a file tab
   */
  private startInlineRename(filePath: string, labelElement: HTMLSpanElement): void {
    if (!this.options.onRenameFile) return;

    const fileName = filePath.split("/").pop() || filePath;

    const input = document.createElement("input");
    input.type = "text";
    input.value = fileName;
    input.className = "file-tab-rename-input";

    labelElement.style.display = "none";
    labelElement.parentElement?.insertBefore(input, labelElement);
    input.focus();
    input.select();

    const finishRename = async () => {
      const newName = input.value.trim();
      if (newName && newName !== fileName && this.options.onRenameFile) {
        const dirPath = filePath.includes("/")
          ? filePath.substring(0, filePath.lastIndexOf("/"))
          : "";
        const newPath = dirPath ? `${dirPath}/${newName}` : newName;
        await this.options.onRenameFile(filePath, newPath);
      }
      labelElement.style.display = "";
      input.remove();
    };

    input.onblur = () => finishRename();
    input.onkeydown = (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        finishRename();
      } else if (e.key === "Escape") {
        e.preventDefault();
        labelElement.style.display = "";
        input.remove();
      }
    };
  }

  /**
   * Generate next available filename with numbering
   */
  private getNextAvailableFilename(baseName: string): string {
    const lastDotIndex = baseName.lastIndexOf(".");
    const extension = lastDotIndex > 0 ? baseName.substring(lastDotIndex) : "";
    const nameWithoutExt = lastDotIndex > 0 ? baseName.substring(0, lastDotIndex) : baseName;

    if (!this.existingFiles.includes(baseName) && !this.openFiles.has(baseName)) {
      return baseName;
    }

    const numberPattern = /^(.+?)_(\d+)$/;
    const match = nameWithoutExt.match(numberPattern);
    const basePrefix = match ? match[1] : nameWithoutExt;
    let maxNumber = 0;

    const allFiles = [...this.existingFiles, ...Array.from(this.openFiles.keys())];
    allFiles.forEach((file) => {
      const fileWithoutExt = file.lastIndexOf(".") > 0
        ? file.substring(0, file.lastIndexOf("."))
        : file;

      if (fileWithoutExt === basePrefix) {
        maxNumber = Math.max(maxNumber, 0);
      }

      const fileMatch = fileWithoutExt.match(numberPattern);
      if (fileMatch && fileMatch[1] === basePrefix) {
        const num = parseInt(fileMatch[2], 10);
        maxNumber = Math.max(maxNumber, num);
      }
    });

    const nextNumber = maxNumber + 1;
    const paddedNumber = nextNumber.toString().padStart(2, "0");
    return `${basePrefix}_${paddedNumber}${extension}`;
  }
}
