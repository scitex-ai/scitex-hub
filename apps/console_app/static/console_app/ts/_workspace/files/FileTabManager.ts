/**
 * File Tab Manager
 * Handles tab display, switching, and closing for open files
 */

import type { OpenFile } from "../core/types";
import { modalManager } from "../ui/ModalManager";
import { FileCreationHelper } from "./FileCreationHelper";

export class FileTabManager {
  private openFiles: Map<string, OpenFile>;
  private currentFile: string | null = null;
  private onTabSwitch: (filePath: string) => void;
  private onTabClose: (filePath: string) => void;
  private draggedTabPath: string | null = null;
  private projectId: string | null = null;
  private fileCreation: FileCreationHelper;

  constructor(
    openFiles: Map<string, OpenFile>,
    onTabSwitch: (filePath: string) => void,
    onTabClose: (filePath: string) => void,
  ) {
    this.openFiles = openFiles;
    this.onTabSwitch = onTabSwitch;
    this.onTabClose = onTabClose;
    this.fileCreation = new FileCreationHelper(openFiles);
  }

  initializeProjectId(): void {
    const projectDataEl = document.getElementById("project-data");
    if (projectDataEl) {
      this.projectId = projectDataEl.getAttribute("data-project-id");
      console.log("[FileTabManager] Project ID:", this.projectId);
    } else {
      const urlMatch = window.location.pathname.match(
        /\/visitor-\d+\/([^\/]+)/,
      );
      this.projectId = urlMatch ? urlMatch[1] : "default";
      console.log("[FileTabManager] Project ID (fallback):", this.projectId);
    }
  }

  private getStorageKey(): string {
    return `scitex_code_tabs_${this.projectId || "default"}`;
  }

  saveTabState(): void {
    if (!this.projectId) return;

    const tabState = {
      openFiles: Array.from(this.openFiles.keys()).filter(
        (p) => p !== "*scratch*",
      ),
      currentFile: this.currentFile,
      timestamp: Date.now(),
    };

    try {
      localStorage.setItem(this.getStorageKey(), JSON.stringify(tabState));
    } catch (e) {
      console.warn("[FileTabManager] Failed to save tab state:", e);
    }
  }

  getSavedTabState(): {
    openFiles: string[];
    currentFile: string | null;
  } | null {
    if (!this.projectId) return null;

    try {
      const saved = localStorage.getItem(this.getStorageKey());
      if (saved) {
        const state = JSON.parse(saved);
        const maxAge = 7 * 24 * 60 * 60 * 1000;
        if (state.timestamp && Date.now() - state.timestamp < maxAge) {
          return {
            openFiles: state.openFiles || [],
            currentFile: state.currentFile || null,
          };
        }
      }
    } catch (e) {
      console.warn("[FileTabManager] Failed to load tab state:", e);
    }
    return null;
  }

  clearSavedTabState(): void {
    if (!this.projectId) return;
    try {
      localStorage.removeItem(this.getStorageKey());
    } catch {
      // Ignore
    }
  }

  setNewFileCallback(callback: (fileName: string) => Promise<void>): void {
    this.fileCreation.setNewFileCallback(callback);
  }

  setExistingFiles(files: string[]): void {
    this.fileCreation.setExistingFiles(files);
  }

  setCallbacks(
    onTabSwitch: (filePath: string) => void,
    onTabClose: (filePath: string) => void,
  ): void {
    this.onTabSwitch = onTabSwitch;
    this.onTabClose = onTabClose;
  }

  setCurrentFile(filePath: string | null): void {
    this.currentFile = filePath;
    this.updateTabs();
    this.saveTabState();
  }

  getCurrentFile(): string | null {
    return this.currentFile;
  }

  updateTabs(): void {
    const tabsContainer = document.getElementById("file-tabs");
    if (!tabsContainer) return;

    tabsContainer.innerHTML = "";

    this.openFiles.forEach((file, path) => {
      const tab = document.createElement("button");
      tab.className = `file-tab ${path === this.currentFile ? "active" : ""}`;
      tab.dataset.filePath = path;

      const fileName = path.split("/").pop() || path;
      const isScratch = path === "*scratch*";
      tab.title = isScratch
        ? "Scratch buffer - temporary workspace (not saved to disk)"
        : path;

      const label = document.createElement("span");
      label.className = "file-tab-name";
      label.textContent = isScratch ? "*scratch*" : fileName;
      tab.appendChild(label);

      if (!isScratch) {
        const closeBtn = document.createElement("span");
        closeBtn.className = "file-tab-close";
        closeBtn.innerHTML = "×";
        closeBtn.title = "Close file";
        closeBtn.onclick = async (e) => {
          e.stopPropagation();
          const confirmed = await modalManager.confirmClose(fileName);
          if (confirmed) this.onTabClose(path);
        };
        tab.appendChild(closeBtn);
      }

      tab.onclick = () => this.onTabSwitch(path);

      if (!isScratch) {
        tab.ondblclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.startInlineRename(path, label);
        };
      }

      this.setupDragDrop(tab, path, tabsContainer);
      tabsContainer.appendChild(tab);
    });

    // Add new file button at the end
    const newTabBtn = document.createElement("button");
    newTabBtn.id = "btn-new-file-tab";
    newTabBtn.className = "file-tabs-plus-btn";
    newTabBtn.innerHTML = "+";
    newTabBtn.title = "New file (Ctrl+N)";
    newTabBtn.onclick = () => {
      this.fileCreation.showInlineNewFileInput(tabsContainer, newTabBtn);
    };
    tabsContainer.appendChild(newTabBtn);
  }

  private setupDragDrop(
    tab: HTMLElement,
    path: string,
    container: HTMLElement,
  ): void {
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
      container.querySelectorAll(".file-tab").forEach((t) => {
        t.classList.remove("drag-over");
      });
    };
    tab.ondragover = (e) => {
      e.preventDefault();
      if (this.draggedTabPath && this.draggedTabPath !== path) {
        tab.classList.add("drag-over");
      }
    };
    tab.ondragleave = () => tab.classList.remove("drag-over");
    tab.ondrop = (e) => {
      e.preventDefault();
      tab.classList.remove("drag-over");
      if (this.draggedTabPath && this.draggedTabPath !== path) {
        this.reorderTabs(this.draggedTabPath, path);
      }
    };
  }

  switchToNextTab(): void {
    const tabs = Array.from(this.openFiles.keys());
    if (tabs.length === 0) return;
    const currentIndex = tabs.indexOf(this.currentFile || "");
    this.onTabSwitch(tabs[(currentIndex + 1) % tabs.length]);
  }

  switchToPreviousTab(): void {
    const tabs = Array.from(this.openFiles.keys());
    if (tabs.length === 0) return;
    const currentIndex = tabs.indexOf(this.currentFile || "");
    this.onTabSwitch(tabs[(currentIndex - 1 + tabs.length) % tabs.length]);
  }

  switchToTabByIndex(index: number): void {
    const tabs = Array.from(this.openFiles.keys());
    if (index >= 0 && index < tabs.length) {
      this.onTabSwitch(tabs[index]);
    }
  }

  closeTab(filePath: string): void {
    if (!this.openFiles.has(filePath)) return;
    this.openFiles.delete(filePath);

    if (filePath === this.currentFile) {
      const remainingTabs = Array.from(this.openFiles.keys());
      this.onTabSwitch(
        remainingTabs.length > 0 ? remainingTabs[0] : "*scratch*",
      );
    }

    this.updateTabs();
    this.saveTabState();
  }

  hasOpenFiles(): boolean {
    return this.openFiles.size > 0;
  }

  private reorderTabs(draggedPath: string, targetPath: string): void {
    const entries = Array.from(this.openFiles.entries());
    const draggedIndex = entries.findIndex(([path]) => path === draggedPath);
    const targetIndex = entries.findIndex(([path]) => path === targetPath);

    if (draggedIndex === -1 || targetIndex === -1) return;

    const [draggedEntry] = entries.splice(draggedIndex, 1);
    const newTargetIndex =
      draggedIndex < targetIndex ? targetIndex - 1 : targetIndex;
    entries.splice(newTargetIndex, 0, draggedEntry);

    this.openFiles.clear();
    entries.forEach(([path, file]) => {
      this.openFiles.set(path, file);
    });

    this.updateTabs();
  }

  getOpenFilePaths(): string[] {
    return Array.from(this.openFiles.keys());
  }

  private startInlineRename(
    filePath: string,
    labelElement: HTMLSpanElement,
  ): void {
    const fileName = filePath.split("/").pop() || filePath;

    const input = document.createElement("input");
    input.type = "text";
    input.value = fileName;
    input.className = "file-tab-rename-input";
    input.style.cssText = `
      width: 120px; padding: 2px 4px; font-size: 13px;
      border: 1px solid var(--workspace-icon-primary);
      border-radius: 3px; background: var(--workspace-bg-primary);
      color: var(--text-primary); outline: none;
    `;

    labelElement.style.display = "none";
    labelElement.parentElement?.insertBefore(input, labelElement);
    input.focus();
    input.select();

    const finishRename = async () => {
      const newName = input.value.trim();
      if (newName && newName !== fileName) {
        const dirPath = filePath.includes("/")
          ? filePath.substring(0, filePath.lastIndexOf("/"))
          : "";
        const newPath = dirPath ? `${dirPath}/${newName}` : newName;
        if (this.onRenameFile) await this.onRenameFile(filePath, newPath);
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

  private onRenameFile:
    | ((oldPath: string, newPath: string) => Promise<void>)
    | null = null;

  setRenameCallback(
    callback: (oldPath: string, newPath: string) => Promise<void>,
  ): void {
    this.onRenameFile = callback;
  }

  public triggerNewFileInput(): void {
    this.fileCreation.triggerNewFileInput();
  }
}
