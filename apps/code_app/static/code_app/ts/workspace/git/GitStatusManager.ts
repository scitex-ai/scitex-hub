/**
 * Git Status Manager
 * Handles git status caching and git decorations in the editor
 */

import type { EditorConfig, GitFileStatus, GitDiff } from "../core/types.js";

export class GitStatusManager {
  private config: EditorConfig;
  private gitStatusCache: Map<string, GitFileStatus> = new Map();
  private currentDecorations: string[] = [];

  constructor(config: EditorConfig) {
    this.config = config;
  }

  async updateGitStatus(): Promise<void> {
    if (!this.config.currentProject) return;

    try {
      const response = await fetch(
        `/code/api/git-status/?project_id=${this.config.currentProject.id}`
      );
      const data = await response.json();

      if (data.success) {
        this.gitStatusCache.clear();
        for (const [path, status] of Object.entries(data.statuses)) {
          this.gitStatusCache.set(path, status as GitFileStatus);
        }
        console.log("[GitStatus] Updated status cache");
      }
    } catch (err) {
      console.error("[GitStatus] Failed to fetch git status:", err);
    }
  }

  getFileStatus(filePath: string): GitFileStatus | undefined {
    return this.gitStatusCache.get(filePath);
  }

  async updateGitDecorations(filePath: string, editor: any): Promise<void> {
    if (!this.config.currentProject || !editor) return;

    try {
      const response = await fetch(
        `/code/api/file-diff/${filePath}?project_id=${this.config.currentProject.id}`
      );
      const data = await response.json();

      if (data.success) {
        this.applyGitDecorations(data.diffs, editor);
      }
    } catch (err) {
      console.error("[GitStatus] Failed to fetch file diff:", err);
    }
  }

  private applyGitDecorations(diffs: GitDiff[], editor: any): void {
    if (!editor) return;

    const monaco = (window as any).monaco;
    if (!monaco) return;

    // Clear previous decorations
    this.currentDecorations = editor.deltaDecorations(this.currentDecorations, []);

    // Create new decorations
    const newDecorations: any[] = [];

    for (const diff of diffs) {
      let className = "git-gutter-modified";
      let glyphMarginClassName = "git-glyph-modified";

      if (diff.status === "added") {
        className = "git-gutter-added";
        glyphMarginClassName = "git-glyph-added";
      } else if (diff.status === "deleted") {
        className = "git-gutter-deleted";
        glyphMarginClassName = "git-glyph-deleted";
      }

      newDecorations.push({
        range: new monaco.Range(diff.line, 1, diff.line, 1),
        options: {
          isWholeLine: true,
          linesDecorationsClassName: className,
          glyphMarginClassName: glyphMarginClassName,
        },
      });
    }

    // Apply new decorations
    this.currentDecorations = editor.deltaDecorations([], newDecorations);

    console.log(`[GitStatus] Applied ${newDecorations.length} decorations`);
  }

  clearDecorations(editor: any): void {
    if (!editor) return;
    this.currentDecorations = editor.deltaDecorations(this.currentDecorations, []);
  }

  getStatusCache(): Map<string, GitFileStatus> {
    return this.gitStatusCache;
  }
}
