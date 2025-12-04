/**
 * Collaborative Editor Manager
 * Handles manuscript editing, collaboration, auto-save, word counts, and version control
 *
 * @version 2.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/editor/collaborative/manager.ts loaded",
);

import type { ManuscriptConfig } from "./types.js";
import { ChangeTracker } from "./changes.js";
import { CursorManager } from "./cursors.js";
import { SyncManager } from "./sync.js";

export class CollaborativeEditorManager {
  private changeTracker: ChangeTracker;
  private cursorManager: CursorManager;
  private syncManager: SyncManager;

  constructor(private manuscriptConfig: ManuscriptConfig) {
    this.changeTracker = new ChangeTracker(manuscriptConfig);
    this.cursorManager = new CursorManager(
      manuscriptConfig,
      this.changeTracker,
    );
    this.syncManager = new SyncManager(manuscriptConfig);
  }

  /**
   * Initialize the editor
   */
  initialize(): void {
    console.log("[CollabEditor] Initializing collaborative editor");

    this.setupEditorListeners();
    this.syncManager.setupAutoSave();
    this.syncManager.loadSavedContent();
    this.changeTracker.updateWordCounts();
    this.changeTracker.updateProgress();

    console.log("[CollabEditor] Initialization complete");
  }

  /**
   * Setup event listeners for all section textareas
   */
  private setupEditorListeners(): void {
    this.manuscriptConfig.sections.forEach((section) => {
      const textarea = document.getElementById(
        `section-${section}`,
      ) as HTMLTextAreaElement;
      if (textarea) {
        textarea.addEventListener("input", () => {
          this.changeTracker.updateWordCount(section);

          // Update section badge
          const wordCount = this.changeTracker.countWords(textarea.value);
          this.cursorManager.updateSectionBadge(section, wordCount);

          this.changeTracker.updateProgress();
          this.changeTracker.markAsModified();
        });
      }
    });
  }

  /**
   * Setup collaboration toggle button
   */
  setupCollaborationToggle(): void {
    this.cursorManager.setupCollaborationToggle();
  }

  /**
   * Export manuscript as JSON
   */
  exportJSON(): void {
    this.syncManager.exportJSON();
  }

  /**
   * Show LaTeX view (placeholder)
   */
  showLatexView(): void {
    alert(
      "LaTeX view coming soon! This will show the generated LaTeX code for your manuscript.",
    );
  }

  /**
   * Compile manuscript to PDF (placeholder)
   */
  compileManuscript(): void {
    alert(
      "PDF compilation coming soon! This will generate a PDF from your manuscript.",
    );
  }

  /**
   * Open version control dashboard
   */
  openVersionControl(): void {
    window.location.href = `/writer/version-control/${this.manuscriptConfig.id}/`;
  }

  /**
   * Create a new version with git commit
   */
  async createVersion(): Promise<void> {
    await this.syncManager.createVersion();
  }

  /**
   * Destroy the editor manager and cleanup
   */
  destroy(): void {
    this.syncManager.destroy();
    console.log("[CollabEditor] Editor manager destroyed");
  }
}
