/**
 * Tests for apps/code_app/static/code_app/ts/workspace/files/FileTabManager.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/apps/code_app/static/code_app/ts/workspace/files/FileTabManager';

describe('FileTabManager', () => {
    beforeEach(() => {
        // Setup before each test
    });

    afterEach(() => {
        // Cleanup after each test
    });

    it.todo('should be implemented');
});

// =============================================================================
// Source Code Reference (auto-generated, do not edit below this line)
// =============================================================================
// Source: apps/code_app/static/code_app/ts/workspace/files/FileTabManager.ts
// =============================================================================

// /**
//  * File Tab Manager
//  * Handles tab display, switching, and closing for open files
//  */
// 
// import type { OpenFile } from "../core/types";
// 
// export class FileTabManager {
//   private openFiles: Map<string, OpenFile>;
//   private currentFile: string | null = null;
//   private onTabSwitch: (filePath: string) => void;
//   private onTabClose: (filePath: string) => void;
//   private onNewFile: ((fileName: string) => Promise<void>) | null = null;
//   private existingFiles: string[] = [];
//   private draggedTabPath: string | null = null;
//   private projectId: string | null = null;
// 
//   constructor(
//     openFiles: Map<string, OpenFile>,
//     onTabSwitch: (filePath: string) => void,
//     onTabClose: (filePath: string) => void
//   ) {
//     this.openFiles = openFiles;
//     this.onTabSwitch = onTabSwitch;
//     this.onTabClose = onTabClose;
//   }
// 
//   /**
//    * Initialize project ID for storage (call after DOM is ready)
//    */
//   initializeProjectId(): void {
//     const projectDataEl = document.getElementById("project-data");
//     if (projectDataEl) {
//       this.projectId = projectDataEl.getAttribute("data-project-id");
//       console.log("[FileTabManager] Project ID:", this.projectId);
//     } else {
//       // Fallback: try to get from URL or use default
//       const urlMatch = window.location.pathname.match(/\/visitor-\d+\/([^\/]+)/);
//       if (urlMatch) {
//         this.projectId = urlMatch[1];
//       } else {
//         this.projectId = "default";
//       }
//       console.log("[FileTabManager] Project ID (fallback):", this.projectId);
//     }
//   }
// 
//   /**
//    * Get localStorage key for this project's tabs
//    */
//   private getStorageKey(): string {
//     return `scitex_code_tabs_${this.projectId || "default"}`;
//   }
// 
//   /**
//    * Save current tab state to localStorage
//    */
//   saveTabState(): void {
//     console.log("[FileTabManager] saveTabState called, projectId:", this.projectId);
//     if (!this.projectId) {
//       console.log("[FileTabManager] No projectId, skipping save");
//       return;
//     }
// 
//     const tabState = {
//       openFiles: Array.from(this.openFiles.keys()).filter(p => p !== "*scratch*"),
//       currentFile: this.currentFile,
//       timestamp: Date.now()
//     };
// 
//     try {
//       const key = this.getStorageKey();
//       console.log("[FileTabManager] Saving to key:", key, "files:", tabState.openFiles);
//       localStorage.setItem(key, JSON.stringify(tabState));
//       console.log("[FileTabManager] Saved tab state:", tabState.openFiles.length, "files");
//     } catch (e) {
//       console.warn("[FileTabManager] Failed to save tab state:", e);
//     }
//   }
// 
//   /**
//    * Get saved tab state from localStorage
//    */
//   getSavedTabState(): { openFiles: string[]; currentFile: string | null } | null {
//     if (!this.projectId) return null;
// 
//     try {
//       const saved = localStorage.getItem(this.getStorageKey());
//       if (saved) {
//         const state = JSON.parse(saved);
//         // Only restore if saved within the last 7 days
//         const maxAge = 7 * 24 * 60 * 60 * 1000;
//         if (state.timestamp && Date.now() - state.timestamp < maxAge) {
//           console.log("[FileTabManager] Found saved tab state:", state.openFiles?.length || 0, "files");
//           return {
//             openFiles: state.openFiles || [],
//             currentFile: state.currentFile || null
//           };
//         }
//       }
//     } catch (e) {
//       console.warn("[FileTabManager] Failed to load tab state:", e);
//     }
//     return null;
//   }
// 
//   /**
//    * Clear saved tab state
//    */
//   clearSavedTabState(): void {
//     if (!this.projectId) return;
//     try {
//       localStorage.removeItem(this.getStorageKey());
//     } catch (e) {
//       // Ignore
//     }
//   }
// 
//   /**
//    * Set callback for new file creation
//    */
//   setNewFileCallback(callback: (fileName: string) => Promise<void>): void {
//     this.onNewFile = callback;
//   }
// 
//   /**
//    * Set existing files for autocomplete
//    */
//   setExistingFiles(files: string[]): void {
//     this.existingFiles = files;
//   }
// 
//   /**
//    * Update callbacks after construction
//    * Used when FileStateManager needs to be initialized first
//    */
//   setCallbacks(
//     onTabSwitch: (filePath: string) => void,
//     onTabClose: (filePath: string) => void
//   ): void {
//     this.onTabSwitch = onTabSwitch;
//     this.onTabClose = onTabClose;
//   }
// 
//   setCurrentFile(filePath: string | null): void {
//     this.currentFile = filePath;
//     this.updateTabs();
//     this.saveTabState();
//   }
// 
//   getCurrentFile(): string | null {
//     return this.currentFile;
//   }
// 
//   updateTabs(): void {
//     const tabsContainer = document.getElementById("file-tabs");
//     if (!tabsContainer) return;
// 
//     // Clear tabs
//     tabsContainer.innerHTML = "";
// 
//     this.openFiles.forEach((file, path) => {
//       const tab = document.createElement("button");
//       tab.className = `file-tab ${path === this.currentFile ? "active" : ""}`;
//       tab.dataset.filePath = path;
// 
//       // File name and tooltip
//       const fileName = path.split("/").pop() || path;
//       const isScratch = path === "*scratch*";
//       tab.title = isScratch
//         ? "Scratch buffer - temporary workspace (not saved to disk)"
//         : path;
// 
//       // Tab label
//       const label = document.createElement("span");
//       label.className = "file-tab-name";
//       label.textContent = isScratch ? "*scratch*" : fileName;
//       tab.appendChild(label);
// 
//       // Close button (don't show for scratch)
//       if (!isScratch) {
//         const closeBtn = document.createElement("span");
//         closeBtn.className = "file-tab-close";
//         closeBtn.innerHTML = "×";
//         closeBtn.title = "Close file";
//         closeBtn.onclick = (e) => {
//           e.stopPropagation();
//           this.onTabClose(path);
//         };
//         tab.appendChild(closeBtn);
//       }
// 
//       // Tab click handler
//       tab.onclick = () => {
//         this.onTabSwitch(path);
//       };
// 
//       // Double-click to rename (for regular files only, not scratch)
//       if (!isScratch) {
//         tab.ondblclick = (e) => {
//           e.preventDefault();
//           e.stopPropagation();
//           this.startInlineRename(path, label);
//         };
//       }
// 
//       // Drag and drop reordering
//       tab.draggable = true;
//       tab.ondragstart = (e) => {
//         this.draggedTabPath = path;
//         tab.classList.add("dragging");
//         if (e.dataTransfer) {
//           e.dataTransfer.effectAllowed = "move";
//           e.dataTransfer.setData("text/plain", path);
//         }
//       };
//       tab.ondragend = () => {
//         this.draggedTabPath = null;
//         tab.classList.remove("dragging");
//         // Remove all drag-over classes
//         tabsContainer.querySelectorAll(".file-tab").forEach((t) => {
//           t.classList.remove("drag-over");
//         });
//       };
//       tab.ondragover = (e) => {
//         e.preventDefault();
//         if (this.draggedTabPath && this.draggedTabPath !== path) {
//           tab.classList.add("drag-over");
//         }
//       };
//       tab.ondragleave = () => {
//         tab.classList.remove("drag-over");
//       };
//       tab.ondrop = (e) => {
//         e.preventDefault();
//         tab.classList.remove("drag-over");
//         if (this.draggedTabPath && this.draggedTabPath !== path) {
//           this.reorderTabs(this.draggedTabPath, path);
//         }
//       };
// 
//       tabsContainer.appendChild(tab);
//     });
// 
//     // Add new file button at the end
//     const newTabBtn = document.createElement("button");
//     newTabBtn.id = "btn-new-file-tab";
//     newTabBtn.className = "file-tabs-plus-btn";
//     newTabBtn.innerHTML = "+";
//     newTabBtn.title = "New file (Ctrl+N)";
//     newTabBtn.onclick = () => {
//       this.showInlineNewFileInput(tabsContainer, newTabBtn);
//     };
//     tabsContainer.appendChild(newTabBtn);
//   }
// 
//   switchToNextTab(): void {
//     const tabs = Array.from(this.openFiles.keys());
//     if (tabs.length === 0) return;
// 
//     const currentIndex = tabs.indexOf(this.currentFile || "");
//     const nextIndex = (currentIndex + 1) % tabs.length;
//     this.onTabSwitch(tabs[nextIndex]);
//   }
// 
//   switchToPreviousTab(): void {
//     const tabs = Array.from(this.openFiles.keys());
//     if (tabs.length === 0) return;
// 
//     const currentIndex = tabs.indexOf(this.currentFile || "");
//     const prevIndex = (currentIndex - 1 + tabs.length) % tabs.length;
//     this.onTabSwitch(tabs[prevIndex]);
//   }
// 
//   switchToTabByIndex(index: number): void {
//     const tabs = Array.from(this.openFiles.keys());
//     if (index >= 0 && index < tabs.length) {
//       this.onTabSwitch(tabs[index]);
//     }
//   }
// 
//   closeTab(filePath: string): void {
//     if (!this.openFiles.has(filePath)) return;
// 
//     this.openFiles.delete(filePath);
// 
//     // If closing the current file, switch to another tab or scratch
//     if (filePath === this.currentFile) {
//       const remainingTabs = Array.from(this.openFiles.keys());
//       if (remainingTabs.length > 0) {
//         // Switch to the first tab
//         this.onTabSwitch(remainingTabs[0]);
//       } else {
//         // No tabs left, switch to scratch
//         this.onTabSwitch("*scratch*");
//       }
//     }
// 
//     this.updateTabs();
//     this.saveTabState();
//   }
// 
//   hasOpenFiles(): boolean {
//     return this.openFiles.size > 0;
//   }
// 
//   /**
//    * Reorder tabs by moving draggedPath before targetPath
//    */
//   private reorderTabs(draggedPath: string, targetPath: string): void {
//     const entries = Array.from(this.openFiles.entries());
//     const draggedIndex = entries.findIndex(([path]) => path === draggedPath);
//     const targetIndex = entries.findIndex(([path]) => path === targetPath);
// 
//     if (draggedIndex === -1 || targetIndex === -1) return;
// 
//     // Remove dragged entry
//     const [draggedEntry] = entries.splice(draggedIndex, 1);
// 
//     // Calculate new target index (adjust if dragged was before target)
//     const newTargetIndex = draggedIndex < targetIndex ? targetIndex - 1 : targetIndex;
// 
//     // Insert at new position
//     entries.splice(newTargetIndex, 0, draggedEntry);
// 
//     // Rebuild the map (maintains new order)
//     this.openFiles.clear();
//     entries.forEach(([path, file]) => {
//       this.openFiles.set(path, file);
//     });
// 
//     this.updateTabs();
//   }
// 
//   getOpenFilePaths(): string[] {
//     return Array.from(this.openFiles.keys());
//   }
// 
//   /**
//    * Start inline rename for a file tab
//    */
//   private startInlineRename(filePath: string, labelElement: HTMLSpanElement): void {
//     const fileName = filePath.split("/").pop() || filePath;
// 
//     // Create input field
//     const input = document.createElement("input");
//     input.type = "text";
//     input.value = fileName;
//     input.className = "file-tab-rename-input";
//     input.style.cssText = `
//       width: 120px;
//       padding: 2px 4px;
//       font-size: 13px;
//       border: 1px solid var(--workspace-icon-primary);
//       border-radius: 3px;
//       background: var(--workspace-bg-primary);
//       color: var(--text-primary);
//       outline: none;
//     `;
// 
//     // Replace label with input
//     labelElement.style.display = "none";
//     labelElement.parentElement?.insertBefore(input, labelElement);
//     input.focus();
//     input.select();
// 
//     const finishRename = async () => {
//       const newName = input.value.trim();
//       if (newName && newName !== fileName) {
//         // Calculate new path (preserve directory structure)
//         const dirPath = filePath.includes("/")
//           ? filePath.substring(0, filePath.lastIndexOf("/"))
//           : "";
//         const newPath = dirPath ? `${dirPath}/${newName}` : newName;
// 
//         // Trigger rename callback if available
//         if (this.onRenameFile) {
//           await this.onRenameFile(filePath, newPath);
//         }
//       }
//       // Restore label (updateTabs will be called after rename)
//       labelElement.style.display = "";
//       input.remove();
//     };
// 
//     input.onblur = () => finishRename();
//     input.onkeydown = (e) => {
//       if (e.key === "Enter") {
//         e.preventDefault();
//         finishRename();
//       } else if (e.key === "Escape") {
//         e.preventDefault();
//         labelElement.style.display = "";
//         input.remove();
//       }
//     };
//   }
// 
//   /**
//    * Set callback for file rename
//    */
//   private onRenameFile: ((oldPath: string, newPath: string) => Promise<void>) | null = null;
// 
//   setRenameCallback(callback: (oldPath: string, newPath: string) => Promise<void>): void {
//     this.onRenameFile = callback;
//   }
// 
//   /**
//    * Show inline input for creating a new file
//    */
//   private showInlineNewFileInput(container: HTMLElement, plusBtn: HTMLElement): void {
//     // Check if input already exists
//     const existingInput = container.querySelector('.inline-new-file-input');
//     if (existingInput) {
//       (existingInput as HTMLInputElement).focus();
//       return;
//     }
// 
//     // Create inline input container (styled like a tab)
//     const inputWrapper = document.createElement("div");
//     inputWrapper.className = "file-tab inline-new-file-wrapper";
//     inputWrapper.style.cssText = `
//       display: inline-flex;
//       align-items: center;
//       padding: 4px 8px;
//     `;
// 
//     // Create the input field
//     const input = document.createElement("input");
//     input.type = "text";
//     input.className = "inline-new-file-input";
//     input.placeholder = "filename.py";
//     input.value = this.getNextAvailableFilename("untitled.py");
//     input.style.cssText = `
//       width: 120px;
//       padding: 4px 8px;
//       font-size: 13px;
//       border: 1px solid var(--workspace-icon-primary);
//       border-radius: 4px;
//       background: var(--workspace-bg-primary);
//       color: var(--text-primary);
//       outline: none;
//     `;
// 
//     inputWrapper.appendChild(input);
// 
//     // Insert before the plus button
//     container.insertBefore(inputWrapper, plusBtn);
// 
//     // Focus and select the input
//     input.focus();
//     input.select();
// 
//     const finishCreate = async () => {
//       const fileName = input.value.trim();
//       inputWrapper.remove();
// 
//       if (fileName && this.onNewFile) {
//         await this.onNewFile(fileName);
//       }
//     };
// 
//     const cancelCreate = () => {
//       inputWrapper.remove();
//     };
// 
//     input.onblur = () => {
//       // Small delay to allow click events to register
//       setTimeout(() => {
//         if (document.activeElement !== input) {
//           finishCreate();
//         }
//       }, 100);
//     };
// 
//     input.onkeydown = (e) => {
//       if (e.key === "Enter") {
//         e.preventDefault();
//         finishCreate();
//       } else if (e.key === "Escape") {
//         e.preventDefault();
//         cancelCreate();
//       }
//     };
//   }
// 
//   /**
//    * Generate next available filename with numbering
//    * Examples:
//    *   untitled.py -> untitled_01.py
//    *   untitled_01.py -> untitled_02.py
//    *   untitled_99.py -> untitled_100.py
//    */
//   private getNextAvailableFilename(baseName: string): string {
//     // Extract extension and base name
//     const lastDotIndex = baseName.lastIndexOf('.');
//     const extension = lastDotIndex > 0 ? baseName.substring(lastDotIndex) : '';
//     const nameWithoutExt = lastDotIndex > 0 ? baseName.substring(0, lastDotIndex) : baseName;
// 
//     // Check if base name is available
//     if (!this.existingFiles.includes(baseName) && !this.openFiles.has(baseName)) {
//       return baseName;
//     }
// 
//     // Pattern to match existing numbered files: name_01, name_02, etc.
//     const numberPattern = /^(.+?)_(\d+)$/;
//     const match = nameWithoutExt.match(numberPattern);
// 
//     let basePrefix = match ? match[1] : nameWithoutExt;
//     let maxNumber = 0;
// 
//     // Find the highest number used for this base name
//     const allFiles = [...this.existingFiles, ...Array.from(this.openFiles.keys())];
//     allFiles.forEach(file => {
//       const fileWithoutExt = file.lastIndexOf('.') > 0
//         ? file.substring(0, file.lastIndexOf('.'))
//         : file;
// 
//       // Check exact base name match
//       if (fileWithoutExt === basePrefix) {
//         maxNumber = Math.max(maxNumber, 0);
//       }
// 
//       // Check numbered variants
//       const fileMatch = fileWithoutExt.match(numberPattern);
//       if (fileMatch && fileMatch[1] === basePrefix) {
//         const num = parseInt(fileMatch[2], 10);
//         maxNumber = Math.max(maxNumber, num);
//       }
//     });
// 
//     // Generate next number with zero-padding
//     const nextNumber = maxNumber + 1;
//     const paddedNumber = nextNumber.toString().padStart(2, '0');
// 
//     return `${basePrefix}_${paddedNumber}${extension}`;
//   }
// 
//   /**
//    * Public method to trigger inline new file input
//    */
//   public triggerNewFileInput(): void {
//     const tabsContainer = document.getElementById("file-tabs");
//     const plusBtn = document.getElementById("btn-new-file-tab");
//     if (tabsContainer && plusBtn) {
//       this.showInlineNewFileInput(tabsContainer, plusBtn);
//     }
//   }
// }

// =============================================================================
// End of Source Code
// =============================================================================
