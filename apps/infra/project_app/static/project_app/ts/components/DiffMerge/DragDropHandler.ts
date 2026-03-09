/**
 * DiffMerge Drag and Drop Handler
 */

import { Side } from "./types";

export class DragDropHandler {
  private onFileDropped: (file: File, side: Side) => void;

  constructor(onFileDropped: (file: File, side: Side) => void) {
    this.onFileDropped = onFileDropped;
  }

  /**
   * Setup drag-and-drop functionality for both sides
   */
  public setup(): void {
    this.setupDropZone("left-drop-zone", "left");
    this.setupDropZone("right-drop-zone", "right");
  }

  /**
   * Setup a single drop zone
   */
  private setupDropZone(dropZoneId: string, side: Side): void {
    const dropZone = document.getElementById(dropZoneId);
    if (!dropZone) return;

    // Prevent default drag behaviors
    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
      });
    });

    // Highlight drop zone when item is dragged over it
    ["dragenter", "dragover"].forEach((eventName) => {
      dropZone.addEventListener(eventName, () => {
        dropZone.classList.add("drag-over");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(eventName, () => {
        dropZone.classList.remove("drag-over");
      });
    });

    // Handle dropped files
    dropZone.addEventListener("drop", (e: Event) => {
      const dragEvent = e as DragEvent;
      const files = dragEvent.dataTransfer?.files;
      if (files && files.length > 0) {
        this.onFileDropped(files[0], side);
      }
    });

    // Click to upload
    dropZone.addEventListener("click", () => {
      const fileInput = document.getElementById(
        `${side}-file-input`
      ) as HTMLInputElement;
      if (fileInput) {
        fileInput.click();
      }
    });
  }
}
