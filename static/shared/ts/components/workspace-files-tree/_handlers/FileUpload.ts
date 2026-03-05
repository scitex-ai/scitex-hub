/**
 * File Upload Handler
 * Handles external file uploads and URL downloads
 */

import type { TreeConfig } from "../types";

export class FileUpload {
  private config: TreeConfig;
  private getCsrfToken: () => string;
  private refresh: () => Promise<void>;
  private showMessage: (
    message: string,
    type: "success" | "error" | "info",
  ) => void;

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
      showMessage ||
      ((msg, type) => console.log(`[FileUpload] ${type}: ${msg}`));
  }

  /** Upload files to the project */
  async uploadFiles(files: FileList, targetPath: string): Promise<void> {
    const fileCount = files.length;
    this.showMessage(
      `Uploading ${fileCount} file${fileCount > 1 ? "s" : ""}...`,
      "info",
    );

    let successCount = 0;
    let errorCount = 0;

    for (const file of Array.from(files)) {
      try {
        await this.uploadFile(file, targetPath);
        successCount++;
      } catch (error) {
        console.error(`[FileUpload] Failed to upload ${file.name}:`, error);
        errorCount++;
      }
    }

    if (successCount > 0) {
      await this.refresh();
      this.showMessage(
        `Uploaded ${successCount} file${successCount > 1 ? "s" : ""}${errorCount > 0 ? ` (${errorCount} failed)` : ""}`,
        errorCount > 0 ? "info" : "success",
      );
    } else {
      this.showMessage(`Failed to upload files`, "error");
    }
  }

  /** Upload a single file */
  async uploadFile(file: File, targetPath: string): Promise<void> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append(
      "path",
      targetPath ? `${targetPath}/${file.name}` : file.name,
    );

    const response = await fetch(
      `/${this.config.ownerUsername}/${this.config.projectSlug}/api/files/upload/`,
      {
        method: "POST",
        headers: {
          "X-CSRFToken": this.getCsrfToken(),
        },
        body: formData,
      },
    );

    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error || "Upload failed");
    }
  }

  /** Check if URL looks like a downloadable resource */
  isDownloadableUrl(url: string): boolean {
    if (!url.startsWith("http://") && !url.startsWith("https://")) return false;
    // Accept any valid URL - the server will handle content type detection
    return true;
  }

  /** Download file from URL and upload to project */
  async downloadAndUploadFromUrl(
    url: string,
    targetPath: string,
  ): Promise<void> {
    this.showMessage("Downloading...", "info");

    try {
      // Extract filename from URL or generate one
      let fileName = url.split("/").pop()?.split("?")[0] || "download";
      if (!fileName.includes(".")) {
        fileName += ".bin";
      }

      const response = await fetch(
        `/${this.config.ownerUsername}/${this.config.projectSlug}/api/files/upload-url/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": this.getCsrfToken(),
          },
          body: JSON.stringify({
            url: url,
            path: targetPath ? `${targetPath}/${fileName}` : fileName,
          }),
        },
      );

      const data = await response.json();
      if (data.success) {
        this.showMessage(`Saved as ${data.path}`, "success");
        await this.refresh();
      } else {
        this.showMessage(`Failed: ${data.error}`, "error");
      }
    } catch (error) {
      this.showMessage("Failed to download", "error");
    }
  }
}
