/**
 * Commit Manager
 * Handles git commit modal and operations
 */

import type { EditorConfig } from "../core/types.js";
import type { GitOperations } from "./GitOperations.js";
import type { GitStatusManager } from "./GitStatusManager.js";

export class CommitManager {
  constructor(
    private config: EditorConfig,
    private gitOperations: GitOperations,
    private gitStatusManager: GitStatusManager
  ) {}

  /**
   * Show commit modal for git operations
   */
  async showCommitModal(): Promise<void> {
    // Get current git status to show changed files
    const status = await this.gitOperations.getStatus();
    let filesPreview = "No changes detected";

    if (status && status.size > 0) {
      const entries: string[] = [];
      status.forEach((statusCode, path) => {
        const statusLabel = this.getStatusLabel(statusCode);
        const statusColor = this.getStatusColor(statusCode);
        entries.push(`<div style="padding: 2px 0;"><span style="color: ${statusColor};">${statusLabel}</span> ${path}</div>`);
      });
      filesPreview = entries.join("");
    }

    // Update the commit modal preview
    const previewEl = document.getElementById("commit-files-preview");
    if (previewEl) {
      previewEl.innerHTML = filesPreview;
    }

    // Clear previous message
    const messageInput = document.getElementById("commit-message") as HTMLTextAreaElement;
    if (messageInput) {
      messageInput.value = "";
    }

    // Show the commit modal
    const overlay = document.getElementById("commit-modal-overlay");
    overlay?.classList.add("active");

    // Focus on message input
    setTimeout(() => messageInput?.focus(), 200);

    // Set up submit handler
    const submitBtn = document.getElementById("commit-modal-submit");
    const handleSubmit = async () => {
      const message = messageInput?.value.trim();
      if (!message) {
        alert("Please enter a commit message");
        return;
      }

      const pushCheckbox = document.getElementById("commit-and-push") as HTMLInputElement;
      const shouldPush = pushCheckbox?.checked ?? true;

      overlay?.classList.remove("active");
      submitBtn?.removeEventListener("click", handleSubmit);

      // Perform commit
      const success = await this.gitOperations.commit(message, shouldPush);
      if (success) {
        await this.gitStatusManager.updateGitStatus();
        console.log("[CommitManager] Commit successful");
      }
    };

    submitBtn?.addEventListener("click", handleSubmit);
  }

  /**
   * Get git status label for display
   */
  private getStatusLabel(status: any): string {
    if (typeof status === "string") {
      switch (status) {
        case "M": return "[M]";
        case "A": return "[A]";
        case "D": return "[D]";
        case "?": return "[?]";
        case "U": return "[U]";
        default: return `[${status}]`;
      }
    }
    return "[?]";
  }

  /**
   * Get color for git status
   */
  private getStatusColor(status: any): string {
    if (typeof status === "string") {
      switch (status) {
        case "M": return "var(--scitex-color-04)";
        case "A": return "var(--status-success)";
        case "D": return "var(--status-error)";
        case "?": return "var(--text-muted)";
        default: return "var(--text-default)";
      }
    }
    return "var(--text-default)";
  }
}
