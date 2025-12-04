/**
 * File Operations Manager
 * Handles file CRUD operations (Create, Read, Update, Delete)
 */

import type { EditorConfig, OpenFile } from "../core/types.js";

export class FileOperations {
  private config: EditorConfig;

  constructor(config: EditorConfig) {
    this.config = config;
  }

  async loadFile(filePath: string): Promise<{ content: string; success: boolean }> {
    if (!this.config.currentProject) {
      return { content: "", success: false };
    }

    try {
      const projectId = this.config.currentProject?.id;
      const response = await fetch(`/code/api/file-content/${encodeURIComponent(filePath)}?project_id=${projectId}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.config.csrfToken,
        },
      });

      const data = await response.json();

      if (data.success) {
        return { content: data.content, success: true };
      } else {
        console.error("[FileOperations] Failed to load file:", data.message);
        return { content: "", success: false };
      }
    } catch (err) {
      console.error("[FileOperations] Error loading file:", err);
      return { content: "", success: false };
    }
  }

  async saveFile(filePath: string, content: string): Promise<boolean> {
    if (!this.config.currentProject) return false;

    try {
      const response = await fetch(`/code/api/save/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.config.csrfToken,
        },
        body: JSON.stringify({
          project_id: this.config.currentProject?.id,
          path: filePath,
          content: content,
        }),
      });

      const data = await response.json();

      if (data.success) {
        console.log("[FileOperations] File saved:", filePath);
        return true;
      } else {
        console.error("[FileOperations] Save failed:", data.message);
        return false;
      }
    } catch (err) {
      console.error("[FileOperations] Error saving file:", err);
      return false;
    }
  }

  async deleteFile(filePath: string): Promise<boolean> {
    if (!this.config.currentProject) return false;

    try {
      const response = await fetch(`/code/api/delete/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.config.csrfToken,
        },
        body: JSON.stringify({
          project_id: this.config.currentProject?.id,
          path: filePath,
        }),
      });

      const data = await response.json();

      if (data.success) {
        console.log("[FileOperations] File deleted:", filePath);
        return true;
      } else {
        console.error("[FileOperations] Delete failed:", data.message);
        return false;
      }
    } catch (err) {
      console.error("[FileOperations] Error deleting file:", err);
      return false;
    }
  }

  async createFile(filePath: string, content: string = ""): Promise<boolean> {
    // Create is basically save with default empty content
    return this.saveFile(filePath, content);
  }

  async createFolder(folderPath: string): Promise<boolean> {
    if (!this.config.currentProject) return false;

    try {
      // Use command API to create folder via mkdir
      const response = await fetch(`/code/api/command/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.config.csrfToken,
        },
        body: JSON.stringify({
          project_id: this.config.currentProject?.id,
          command: `mkdir -p "${folderPath}"`,
        }),
      });

      const data = await response.json();

      if (data.success) {
        console.log("[FileOperations] Folder created:", folderPath);
        return true;
      } else {
        console.error("[FileOperations] Create folder failed:", data.stderr);
        return false;
      }
    } catch (err) {
      console.error("[FileOperations] Error creating folder:", err);
      return false;
    }
  }

  async renameFile(oldPath: string, newPath: string): Promise<boolean> {
    if (!this.config.currentProject) return false;

    try {
      // Use command API to rename via mv
      const response = await fetch(`/code/api/command/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.config.csrfToken,
        },
        body: JSON.stringify({
          project_id: this.config.currentProject?.id,
          command: `mv "${oldPath}" "${newPath}"`,
        }),
      });

      const data = await response.json();

      if (data.success) {
        console.log("[FileOperations] File renamed:", oldPath, "->", newPath);
        return true;
      } else {
        console.error("[FileOperations] Rename failed:", data.stderr);
        return false;
      }
    } catch (err) {
      console.error("[FileOperations] Error renaming file:", err);
      return false;
    }
  }
}
