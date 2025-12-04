/**
 * Figure Upload Module
 * Handles file upload and drag-drop functionality
 */

import { getCsrfToken } from "../../shared/utils.js";

export class FigureUpload {
  private projectId: string | null = null;
  private dragCounter: number = 0;
  private onUploadSuccess?: () => void;

  constructor(projectId: string | null = null) {
    this.projectId = projectId;
    console.log("[FigureUpload] Initialized with project:", projectId);
  }

  /**
   * Set project ID
   */
  setProjectId(projectId: string | null): void {
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
  setupDropZone(
    dropZoneId: string = "figures-drop-zone",
    fileInputId: string = "figures-file-input",
  ): void {
    const dropZone = document.getElementById(dropZoneId);
    const fileInput = document.getElementById(fileInputId) as HTMLInputElement;

    if (!dropZone || !fileInput) {
      console.warn("[FigureUpload] Drop zone elements not found");
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

    console.log("[FigureUpload] Drop zone setup complete");
  }

  /**
   * Handle file upload
   */
  private async handleFileUpload(files: File[]): Promise<void> {
    if (!this.projectId) {
      console.error("[FigureUpload] No project ID for upload");
      alert("Error: No project ID found");
      return;
    }

    // Validate file types
    const validationResult = this.validateFiles(files);
    if (!validationResult.valid) {
      alert(validationResult.message);
      return;
    }

    // Upload files
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    try {
      const apiUrl = `/writer/api/project/${this.projectId}/upload-figures/`;
      console.log(`[FigureUpload] Uploading ${files.length} files to:`, apiUrl);

      const response = await fetch(apiUrl, {
        method: "POST",
        body: formData,
        headers: {
          "X-CSRFToken": getCsrfToken(),
        },
      });

      const data = await response.json();

      if (data.success) {
        console.log("[FigureUpload] Upload successful:", data);
        alert(`Successfully uploaded ${files.length} figure(s)`);
        this.onUploadSuccess?.();
      } else {
        console.error("[FigureUpload] Upload failed:", data);
        alert(`Upload failed: ${data.error || "Unknown error"}`);
      }
    } catch (error) {
      console.error("[FigureUpload] Upload error:", error);
      alert("Upload failed due to network error");
    }
  }

  /**
   * Validate files before upload
   */
  private validateFiles(files: File[]): { valid: boolean; message: string } {
    const validExtensions = [".png", ".jpg", ".jpeg", ".pdf", ".svg"];
    const invalidFiles = files.filter((file) => {
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      return !validExtensions.includes(ext);
    });

    if (invalidFiles.length > 0) {
      return {
        valid: false,
        message: `Invalid file types: ${invalidFiles.map((f) => f.name).join(", ")}\nSupported: PNG, JPG, PDF, SVG`,
      };
    }

    return { valid: true, message: "" };
  }
}
