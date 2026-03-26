/**
 * Git Diff Viewer
 * Renders file diffs using scitex-ui's MonacoDiffEditor component.
 * Provides a file list and a Monaco-based side-by-side diff display.
 */

import { MonacoDiffEditor } from "scitex-ui/ts/app/monaco-editor/index";
import type { GitDiff } from "./types";

export class GitDiffViewer {
  private diffEditor: MonacoDiffEditor | null = null;
  private currentDiff: GitDiff | null = null;
  private currentFileIndex: number = -1;
  private diffContent: HTMLElement;

  constructor(diffContent: HTMLElement) {
    this.diffContent = diffContent;
  }

  /**
   * Render the diff: file list on top, Monaco DiffEditor below.
   * Clicking a file loads its original/modified content into the editor.
   */
  renderDiff(diff: GitDiff): void {
    this.currentDiff = diff;
    this.currentFileIndex = -1;

    if (diff.files.length === 0) {
      this.diffContent.innerHTML = `
        <div class="text-center text-muted py-3">
          <i class="fas fa-info-circle me-2"></i>
          No changes in this commit
        </div>
      `;
      return;
    }

    const fileListHtml = diff.files
      .map(
        (file, index) => `
      <div class="git-diff-file-entry"
           data-file-index="${index}"
           style="display:flex;align-items:center;gap:8px;padding:8px 12px;cursor:pointer;
                  border:1px solid var(--color-border-default);border-radius:6px;
                  transition:all 0.15s ease;${index === 0 ? "border-color:var(--color-accent-emphasis);background:var(--color-accent-subtle);" : ""}">
        <i class="fas fa-file-code" style="opacity:0.6;"></i>
        <span style="flex:1;font-size:13px;font-weight:500;">${this.escapeHtml(file.path)}</span>
        <span class="badge bg-secondary" style="font-size:10px;">${file.change_type}</span>
        ${file.insertions > 0 ? `<span class="badge bg-success" style="font-size:10px;">+${file.insertions}</span>` : ""}
        ${file.deletions > 0 ? `<span class="badge bg-danger" style="font-size:10px;">-${file.deletions}</span>` : ""}
      </div>
    `,
      )
      .join("");

    this.diffContent.innerHTML = `
      <div class="git-diff-file-list" style="display:flex;flex-direction:column;gap:4px;margin-bottom:12px;">
        ${fileListHtml}
      </div>
      <div id="gitMonacoDiffContainer"
           style="flex:1;min-height:400px;border:1px solid var(--color-border-default);border-radius:6px;overflow:hidden;">
      </div>
    `;

    this.attachFileClickHandlers();

    // Auto-show first file
    if (diff.files.length > 0) {
      this.showFileDiff(0);
    }
  }

  /**
   * Destroy the Monaco DiffEditor and reset state.
   */
  destroy(): void {
    if (this.diffEditor) {
      this.diffEditor.destroy();
      this.diffEditor = null;
    }
    this.currentDiff = null;
    this.currentFileIndex = -1;
  }

  // ── Private ────────────────────────────────────────────────────────

  private attachFileClickHandlers(): void {
    const entries = this.diffContent.querySelectorAll(".git-diff-file-entry");
    entries.forEach((entry) => {
      entry.addEventListener("click", () => {
        const idx = parseInt(
          (entry as HTMLElement).getAttribute("data-file-index") || "0",
          10,
        );
        entries.forEach((e) => {
          (e as HTMLElement).style.borderColor = "var(--color-border-default)";
          (e as HTMLElement).style.background = "";
        });
        (entry as HTMLElement).style.borderColor =
          "var(--color-accent-emphasis)";
        (entry as HTMLElement).style.background = "var(--color-accent-subtle)";
        this.showFileDiff(idx);
      });
    });
  }

  private async showFileDiff(fileIndex: number): Promise<void> {
    if (
      !this.currentDiff ||
      fileIndex < 0 ||
      fileIndex >= this.currentDiff.files.length
    ) {
      return;
    }

    const file = this.currentDiff.files[fileIndex];
    this.currentFileIndex = fileIndex;

    const container = document.getElementById("gitMonacoDiffContainer");
    if (!container) {
      console.error("[GitDiffViewer] Monaco diff container not found");
      return;
    }

    // Reuse existing editor when possible
    if (this.diffEditor) {
      this.diffEditor.setDiff(
        file.original_content || "",
        file.modified_content || "",
        file.path,
      );
      console.log("[GitDiffViewer] Updated DiffEditor for:", file.path);
      return;
    }

    try {
      this.diffEditor = new MonacoDiffEditor({
        container,
        original: file.original_content || "",
        modified: file.modified_content || "",
        filePath: file.path,
        readOnly: true,
        renderSideBySide: true,
        enableHunkNavigation: true,
        enableHunkActions: false,
      });

      await this.diffEditor.initialize();
      console.log(
        "[GitDiffViewer] MonacoDiffEditor initialized for:",
        file.path,
      );
    } catch (err) {
      console.error("[GitDiffViewer] Failed to init MonacoDiffEditor:", err);
      container.innerHTML = `
        <div class="alert alert-warning m-3">
          <i class="fas fa-exclamation-triangle me-2"></i>
          Could not initialize diff editor. Showing raw diff instead.
        </div>
        <pre style="padding:12px;font-size:12px;overflow:auto;">${this.escapeHtml(file.diff)}</pre>
      `;
    }
  }

  private escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}
