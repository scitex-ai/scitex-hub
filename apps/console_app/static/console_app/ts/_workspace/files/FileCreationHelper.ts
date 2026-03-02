/**
 * File Creation Helper
 * Handles inline new file creation UI and filename generation
 */

import type { OpenFile } from "../core/types";

export class FileCreationHelper {
  private openFiles: Map<string, OpenFile>;
  private existingFiles: string[] = [];
  private onNewFile: ((fileName: string) => Promise<void>) | null = null;

  constructor(openFiles: Map<string, OpenFile>) {
    this.openFiles = openFiles;
  }

  setNewFileCallback(callback: (fileName: string) => Promise<void>): void {
    this.onNewFile = callback;
  }

  setExistingFiles(files: string[]): void {
    this.existingFiles = files;
  }

  /**
   * Public method to trigger inline new file input
   */
  triggerNewFileInput(): void {
    const tabsContainer = document.getElementById("file-tabs");
    const plusBtn = document.getElementById("btn-new-file-tab");
    if (tabsContainer && plusBtn) {
      this.showInlineNewFileInput(tabsContainer, plusBtn);
    }
  }

  /**
   * Show inline input for creating a new file
   */
  showInlineNewFileInput(container: HTMLElement, plusBtn: HTMLElement): void {
    const existingInput = container.querySelector(".inline-new-file-input");
    if (existingInput) {
      (existingInput as HTMLInputElement).focus();
      return;
    }

    const inputWrapper = document.createElement("div");
    inputWrapper.className = "file-tab inline-new-file-wrapper";
    inputWrapper.style.cssText = `
      display: inline-flex;
      align-items: center;
      padding: 4px 8px;
    `;

    const input = document.createElement("input");
    input.type = "text";
    input.className = "inline-new-file-input";
    input.placeholder = "filename.py";
    input.value = this.getNextAvailableFilename("untitled.py");
    input.style.cssText = `
      width: 120px;
      padding: 4px 8px;
      font-size: 13px;
      border: 1px solid var(--workspace-icon-primary);
      border-radius: 4px;
      background: var(--workspace-bg-primary);
      color: var(--text-primary);
      outline: none;
    `;

    inputWrapper.appendChild(input);
    container.insertBefore(inputWrapper, plusBtn);

    input.focus();
    input.select();

    const finishCreate = async () => {
      const fileName = input.value.trim();
      inputWrapper.remove();

      if (fileName && this.onNewFile) {
        await this.onNewFile(fileName);
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
   * Generate next available filename with numbering
   */
  getNextAvailableFilename(baseName: string): string {
    const lastDotIndex = baseName.lastIndexOf(".");
    const extension = lastDotIndex > 0 ? baseName.substring(lastDotIndex) : "";
    const nameWithoutExt =
      lastDotIndex > 0 ? baseName.substring(0, lastDotIndex) : baseName;

    if (
      !this.existingFiles.includes(baseName) &&
      !this.openFiles.has(baseName)
    ) {
      return baseName;
    }

    const numberPattern = /^(.+?)_(\d+)$/;
    const match = nameWithoutExt.match(numberPattern);

    const basePrefix = match ? match[1] : nameWithoutExt;
    let maxNumber = 0;

    const allFiles = [
      ...this.existingFiles,
      ...Array.from(this.openFiles.keys()),
    ];
    allFiles.forEach((file) => {
      const fileWithoutExt =
        file.lastIndexOf(".") > 0
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
