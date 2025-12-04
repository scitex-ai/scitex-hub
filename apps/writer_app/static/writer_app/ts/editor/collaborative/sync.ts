/**
 * Sync and Auto-save Operations
 *
 * @version 2.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

import { getCsrfToken } from "@/utils/csrf.js";
import type {
  ManuscriptConfig,
  ManuscriptData,
  VersionData,
  VersionResponse,
  ExportData,
} from "./types.js";

export class SyncManager {
  private autoSaveInterval: ReturnType<typeof setInterval> | null = null;

  constructor(private manuscriptConfig: ManuscriptConfig) {}

  /**
   * Setup auto-save interval
   */
  setupAutoSave(): void {
    // Auto-save every 30 seconds
    this.autoSaveInterval = setInterval(() => this.autoSave(), 30000);

    // Save on page unload
    window.addEventListener("beforeunload", () => this.autoSave());
  }

  /**
   * Auto-save manuscript to localStorage
   */
  autoSave(): void {
    const data: ManuscriptData = {};

    this.manuscriptConfig.sections.forEach((section) => {
      const textarea = document.getElementById(
        `section-${section}`,
      ) as HTMLTextAreaElement;
      if (textarea) {
        data[section] = textarea.value;
      }
    });

    // Save to localStorage
    const storageKey = `manuscript_${this.manuscriptConfig.id}`;
    localStorage.setItem(storageKey, JSON.stringify(data));

    // Update save time
    this.updateLastSaveTime("Auto-saved just now");

    console.log("[CollabEditor] Manuscript auto-saved");
  }

  /**
   * Load saved content from localStorage
   */
  loadSavedContent(): void {
    const storageKey = `manuscript_${this.manuscriptConfig.id}`;
    const saved = localStorage.getItem(storageKey);

    if (saved) {
      try {
        const data: ManuscriptData = JSON.parse(saved);

        this.manuscriptConfig.sections.forEach((section) => {
          const textarea = document.getElementById(
            `section-${section}`,
          ) as HTMLTextAreaElement;
          if (textarea && data[section]) {
            textarea.value = data[section];
          }
        });

        console.log("[CollabEditor] Loaded saved content from localStorage");
      } catch (error) {
        console.error("[CollabEditor] Error loading saved content:", error);
      }
    }
  }

  /**
   * Update last save time message
   */
  private updateLastSaveTime(message: string): void {
    const saveTime = document.getElementById("last-save-time");
    if (saveTime) {
      saveTime.textContent = message;
    }
  }

  /**
   * Export manuscript as JSON
   */
  exportJSON(): void {
    const data: ExportData = {
      manuscript_id: this.manuscriptConfig.id,
      sections: {},
      exported_at: new Date().toISOString(),
    };

    this.manuscriptConfig.sections.forEach((section) => {
      const textarea = document.getElementById(
        `section-${section}`,
      ) as HTMLTextAreaElement;
      if (textarea) {
        data.sections[section] = textarea.value;
      }
    });

    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `manuscript_${this.manuscriptConfig.id}.json`;
    a.click();
    URL.revokeObjectURL(url);

    console.log("[CollabEditor] Manuscript exported as JSON");
  }

  /**
   * Create a new version with git commit
   */
  async createVersion(): Promise<void> {
    const commitMessage = prompt("Enter a commit message for this version:");
    if (!commitMessage) return;

    const versionTag =
      prompt(
        'Enter an optional version tag (e.g., "Draft 1", "Final Version"):',
      ) || "";

    // First auto-save current content
    this.autoSave();

    const formData: VersionData = {
      commit_message: commitMessage,
      version_tag: versionTag,
      branch_name: "main",
      is_major: false,
    };

    try {
      const response = await fetch(
        `/writer/api/version/${this.manuscriptConfig.id}/create/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify(formData),
        },
      );

      const data: VersionResponse = await response.json();

      if (data.success && data.version) {
        alert(`Version created successfully: v${data.version.version_number}`);
        this.updateLastSaveTime("Version saved");
      } else {
        alert("Error creating version: " + (data.error || "Unknown error"));
      }
    } catch (error) {
      console.error("[CollabEditor] Error creating version:", error);
      alert("Error creating version");
    }
  }

  /**
   * Cleanup auto-save interval
   */
  destroy(): void {
    if (this.autoSaveInterval) {
      clearInterval(this.autoSaveInterval);
      this.autoSaveInterval = null;
    }

    // Final auto-save
    this.autoSave();
  }
}
