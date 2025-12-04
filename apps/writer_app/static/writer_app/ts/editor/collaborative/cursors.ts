/**
 * Cursor and Collaboration Mode Management
 *
 * @version 2.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

import type { ManuscriptConfig } from "./types.js";
import { ChangeTracker } from "./changes.js";

export class CursorManager {
  private isCollaborationEnabled: boolean = false;

  constructor(
    private manuscriptConfig: ManuscriptConfig,
    private changeTracker: ChangeTracker,
  ) {}

  /**
   * Get collaboration status
   */
  isEnabled(): boolean {
    return this.isCollaborationEnabled;
  }

  /**
   * Setup collaboration toggle button
   */
  setupCollaborationToggle(): void {
    const toggle = document.getElementById("collaboration-toggle");
    if (!toggle) {
      console.warn("[CollabEditor] Collaboration toggle not found");
      return;
    }

    toggle.addEventListener("click", () => {
      if (!this.isCollaborationEnabled) {
        this.enableCollaboration();
      } else {
        this.disableCollaboration();
      }
    });
  }

  /**
   * Enable collaboration mode
   */
  enableCollaboration(): void {
    this.isCollaborationEnabled = true;
    const toggle = document.getElementById("collaboration-toggle");
    const status = document.getElementById("collab-status");
    const info = document.getElementById("collaboration-info");

    if (toggle) {
      toggle.classList.add("active");
      toggle.innerHTML = '<i class="fas fa-users"></i> Collaboration Active';
    }

    if (status) status.classList.remove("hidden");
    if (info) info.classList.remove("hidden");

    // Show collaborative help sections
    document.querySelectorAll(".collaborative-help").forEach((help) => {
      help.classList.remove("hidden");
    });

    // Add collaborative styling to editors
    document.querySelectorAll(".text-editor").forEach((editor) => {
      editor.classList.add("collaborative-editing");
    });

    // Initialize WebSocket collaboration if available
    if ((window as any).collaborativeEditor) {
      console.log("[CollabEditor] Collaborative editing enabled");
    }

    // Update all section badges to show collaboration status
    this.manuscriptConfig.sections.forEach((section) => {
      const textarea = document.getElementById(
        `section-${section}`,
      ) as HTMLTextAreaElement;
      if (textarea) {
        const wordCount = this.changeTracker.countWords(textarea.value);
        this.updateSectionBadge(section, wordCount);
      }
    });
  }

  /**
   * Disable collaboration mode
   */
  disableCollaboration(): void {
    this.isCollaborationEnabled = false;
    const toggle = document.getElementById("collaboration-toggle");
    const status = document.getElementById("collab-status");
    const info = document.getElementById("collaboration-info");

    if (toggle) {
      toggle.classList.remove("active");
      toggle.innerHTML = '<i class="fas fa-users"></i> Enable Collaboration';
    }

    if (status) status.classList.add("hidden");
    if (info) info.classList.add("hidden");

    // Hide collaborative help sections
    document.querySelectorAll(".collaborative-help").forEach((help) => {
      help.classList.add("hidden");
    });

    // Remove collaborative styling from editors
    document.querySelectorAll(".text-editor").forEach((editor) => {
      editor.classList.remove("collaborative-editing");
    });

    // Disconnect WebSocket collaboration if available
    if ((window as any).collaborativeEditor) {
      (window as any).collaborativeEditor.destroy();
      console.log("[CollabEditor] Collaborative editing disabled");
    }

    // Update badges to remove collaboration indicators
    this.manuscriptConfig.sections.forEach((section) => {
      const textarea = document.getElementById(
        `section-${section}`,
      ) as HTMLTextAreaElement;
      if (textarea) {
        const wordCount = this.changeTracker.countWords(textarea.value);
        this.updateSectionBadge(section, wordCount);
      }
    });
  }

  /**
   * Update section badge with word count and collaboration status
   */
  updateSectionBadge(section: string, wordCount: number): void {
    const badgesContainer = document.getElementById(`${section}-badges`);
    if (!badgesContainer) return;

    // Clear existing badges
    badgesContainer.innerHTML = "";

    // Add word count badge
    if (wordCount > 0) {
      const badge = document.createElement("span");
      badge.className = "collaboration-badge active";
      badge.innerHTML = `<i class="fas fa-edit"></i> ${wordCount} words`;
      badgesContainer.appendChild(badge);
    }

    // Add collaboration badges if enabled
    if (this.isCollaborationEnabled) {
      const collabBadge = document.createElement("span");
      collabBadge.className = "collaboration-badge editing";
      collabBadge.innerHTML = `<i class="fas fa-users"></i> Live`;
      badgesContainer.appendChild(collabBadge);
    }
  }
}
