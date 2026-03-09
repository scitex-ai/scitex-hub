/**
 * DiffMerge UI Manager
 */

import { Side } from "./types";

export class UIManager {
  private onClear: (side: Side) => void;
  private onOpenFileBrowser: (side: Side) => void;
  private onComputeDiff: () => void;
  private onMerge: (strategy: "left" | "right" | "manual") => void;
  private onDownload: () => void;
  private onCopy: () => void;
  private onContentChange: (side: Side, content: string) => void;

  constructor(handlers: {
    onClear: (side: Side) => void;
    onOpenFileBrowser: (side: Side) => void;
    onComputeDiff: () => void;
    onMerge: (strategy: "left" | "right" | "manual") => void;
    onDownload: () => void;
    onCopy: () => void;
    onContentChange: (side: Side, content: string) => void;
  }) {
    this.onClear = handlers.onClear;
    this.onOpenFileBrowser = handlers.onOpenFileBrowser;
    this.onComputeDiff = handlers.onComputeDiff;
    this.onMerge = handlers.onMerge;
    this.onDownload = handlers.onDownload;
    this.onCopy = handlers.onCopy;
    this.onContentChange = handlers.onContentChange;
  }

  /**
   * Setup all button handlers
   */
  public setupButtons(): void {
    // Upload buttons
    document
      .getElementById("left-upload-file")
      ?.addEventListener("click", (e) => {
        e.stopPropagation();
        const fileInput = document.getElementById(
          "left-file-input"
        ) as HTMLInputElement;
        fileInput?.click();
      });

    document
      .getElementById("right-upload-file")
      ?.addEventListener("click", (e) => {
        e.stopPropagation();
        const fileInput = document.getElementById(
          "right-file-input"
        ) as HTMLInputElement;
        fileInput?.click();
      });

    // Clear buttons
    document.getElementById("left-clear")?.addEventListener("click", (e) => {
      e.stopPropagation();
      this.onClear("left");
    });

    document.getElementById("right-clear")?.addEventListener("click", (e) => {
      e.stopPropagation();
      this.onClear("right");
    });

    // From repo buttons
    document
      .getElementById("left-select-from-repo")
      ?.addEventListener("click", (e) => {
        e.stopPropagation();
        this.onOpenFileBrowser("left");
      });

    document
      .getElementById("right-select-from-repo")
      ?.addEventListener("click", (e) => {
        e.stopPropagation();
        this.onOpenFileBrowser("right");
      });

    // Compute diff button
    document.getElementById("compute-diff")?.addEventListener("click", () => {
      this.onComputeDiff();
    });

    // Merge buttons
    document.getElementById("merge-left")?.addEventListener("click", () => {
      this.onMerge("left");
    });

    document.getElementById("merge-right")?.addEventListener("click", () => {
      this.onMerge("right");
    });

    document.getElementById("merge-manual")?.addEventListener("click", () => {
      this.onMerge("manual");
    });

    // Download button
    document
      .getElementById("download-merged")
      ?.addEventListener("click", () => {
        this.onDownload();
      });

    // Copy merged button
    document.getElementById("copy-merged")?.addEventListener("click", () => {
      this.onCopy();
    });

    // Content change handlers
    this.setupContentChangeHandlers();
  }

  /**
   * Setup content change handlers
   */
  private setupContentChangeHandlers(): void {
    const leftTextarea = document.getElementById(
      "left-content"
    ) as HTMLTextAreaElement;
    const rightTextarea = document.getElementById(
      "right-content"
    ) as HTMLTextAreaElement;

    leftTextarea?.addEventListener("input", (e) => {
      const target = e.target as HTMLTextAreaElement;
      this.onContentChange("left", target.value);
      const dropZone = document.getElementById("left-drop-zone");
      if (dropZone) {
        if (target.value) {
          dropZone.classList.add("has-content");
        } else {
          dropZone.classList.remove("has-content");
        }
      }
    });

    rightTextarea?.addEventListener("input", (e) => {
      const target = e.target as HTMLTextAreaElement;
      this.onContentChange("right", target.value);
      const dropZone = document.getElementById("right-drop-zone");
      if (dropZone) {
        if (target.value) {
          dropZone.classList.add("has-content");
        } else {
          dropZone.classList.remove("has-content");
        }
      }
    });
  }
}
