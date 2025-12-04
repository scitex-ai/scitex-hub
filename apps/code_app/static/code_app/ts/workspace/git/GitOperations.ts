/**
 * Git Operations Manager
 * Handles git commands: commit, push, diff, etc.
 */

import type { EditorConfig } from "../core/types.js";

export class GitOperations {
  private config: EditorConfig;

  constructor(config: EditorConfig) {
    this.config = config;
  }

  async commit(message: string, push: boolean = true): Promise<boolean> {
    if (!this.config.currentProject) return false;

    try {
      console.log(`[GitOperations] Committing with message: ${message}`);
      console.log(`[GitOperations] Push to remote: ${push}`);

      const response = await fetch(`/code/api/git-commit/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.config.csrfToken,
        },
        body: JSON.stringify({
          project_id: this.config.currentProject.id,
          message: message,
          push: push,
        }),
      });

      const data = await response.json();

      if (data.success) {
        console.log(`[GitOperations] ✓ ${data.message}`);
        return true;
      } else {
        console.error(`[GitOperations] ✗ Commit failed: ${data.error}`);
        alert(`Commit failed: ${data.error}`);
        return false;
      }
    } catch (err) {
      console.error(`[GitOperations] ✗ Failed to commit:`, err);
      alert(`Failed to commit: ${err}`);
      return false;
    }
  }

  async getFileDiff(filePath: string): Promise<any> {
    if (!this.config.currentProject) return null;

    try {
      const response = await fetch(
        `/code/api/file-diff/${filePath}?project_id=${this.config.currentProject.id}`
      );
      const data = await response.json();

      if (data.success) {
        return data.diffs;
      }
      return null;
    } catch (err) {
      console.error("[GitOperations] Failed to fetch file diff:", err);
      return null;
    }
  }

  async getStatus(): Promise<Map<string, any> | null> {
    if (!this.config.currentProject) return null;

    try {
      const response = await fetch(
        `/code/api/git-status/?project_id=${this.config.currentProject.id}`
      );
      const data = await response.json();

      if (data.success) {
        const statusMap = new Map();
        for (const [path, status] of Object.entries(data.statuses)) {
          statusMap.set(path, status);
        }
        return statusMap;
      }
      return null;
    } catch (err) {
      console.error("[GitOperations] Failed to fetch git status:", err);
      return null;
    }
  }
}
