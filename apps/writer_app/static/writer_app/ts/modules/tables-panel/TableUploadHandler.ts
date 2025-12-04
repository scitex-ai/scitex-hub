/**
 * Table Upload Handler
 * Manages file uploads via drag-and-drop or file input
 */

import { getCsrfToken } from "../../shared/utils.js";

export class TableUploadHandler {
  private dragCounter: number = 0;
  private projectId: string | null = null;
  private onUploadSuccess?: () => void;

  constructor(projectId: string | null) {
    this.projectId = projectId;
  }

  /**
   * Set upload success callback
   */
  setOnUploadSuccess(callback: () => void): void {
    this.onUploadSuccess = callback;
  }

  /**
   * Setup drop zone for file uploads
   */
  setupDropZone(): void {
    const dropZone = document.getElementById("tables-drop-zone");
    const fileInput = document.getElementById("tables-file-input") as HTMLInputElement;

    if (!dropZone || !fileInput) {
      console.warn("[TableUploadHandler] Drop zone elements not found");
      return;
    }

    // Prevent defaults
    const preventDefaults = (e: Event) => {
      e.preventDefault();
      e.stopPropagation();
    };

    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(eventName, preventDefaults, false);
    });

    // Drag enter
    dropZone.addEventListener("dragenter", (e: DragEvent) => {
      this.dragCounter++;
      if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
      dropZone.classList.add("drag-over");
    });

    // Drag leave
    dropZone.addEventListener("dragleave", () => {
      this.dragCounter--;
      if (this.dragCounter === 0) {
        dropZone.classList.remove("drag-over");
      }
    });

    // Drop
    dropZone.addEventListener("drop", (e: DragEvent) => {
      this.dragCounter = 0;
      dropZone.classList.remove("drag-over");
      const files = e.dataTransfer?.files;
      if (files && files.length > 0) {
        this.handleFileUpload(Array.from(files));
      }
    });

    // Click to browse
    dropZone.addEventListener("click", () => {
      fileInput.click();
    });

    // File input change
    fileInput.addEventListener("change", () => {
      if (fileInput.files && fileInput.files.length > 0) {
        this.handleFileUpload(Array.from(fileInput.files));
        fileInput.value = ""; // Reset input
      }
    });

    console.log("[TableUploadHandler] Drop zone setup complete");
  }

  /**
   * Validate file types
   */
  private validateFiles(files: File[]): { valid: File[]; invalid: File[] } {
    const validExtensions = [".csv", ".xlsx", ".xls", ".tsv", ".ods"];
    const valid: File[] = [];
    const invalid: File[] = [];

    files.forEach((file) => {
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (validExtensions.includes(ext)) {
        valid.push(file);
      } else {
        invalid.push(file);
      }
    });

    return { valid, invalid };
  }

  /**
   * Handle file upload
   */
  private async handleFileUpload(files: File[]): Promise<void> {
    if (!this.projectId) {
      console.error("[TableUploadHandler] No project ID for upload");
      alert("Error: No project ID found");
      return;
    }

    // Validate file types
    const { valid, invalid } = this.validateFiles(files);

    if (invalid.length > 0) {
      alert(
        `Invalid file types: ${invalid.map((f) => f.name).join(", ")}\nSupported: CSV, Excel, TSV, ODS`,
      );
      return;
    }

    if (valid.length === 0) {
      return;
    }

    // Upload files
    const formData = new FormData();
    valid.forEach((file) => {
      formData.append("files", file);
    });

    try {
      const apiUrl = `/writer/api/project/${this.projectId}/upload-tables/`;
      console.log(`[TableUploadHandler] Uploading ${valid.length} files to:`, apiUrl);

      const response = await fetch(apiUrl, {
        method: "POST",
        body: formData,
        headers: {
          "X-CSRFToken": getCsrfToken(),
        },
      });

      const data = await response.json();

      if (data.success) {
        console.log("[TableUploadHandler] Upload successful:", data);
        alert(`Successfully uploaded ${valid.length} table(s)`);
        this.onUploadSuccess?.();
      } else {
        console.error("[TableUploadHandler] Upload failed:", data);
        alert(`Upload failed: ${data.error || "Unknown error"}`);
      }
    } catch (error) {
      console.error("[TableUploadHandler] Upload error:", error);
      alert("Upload failed due to network error");
    }
  }
}
