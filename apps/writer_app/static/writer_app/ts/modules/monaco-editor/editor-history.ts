/**
 * Editor History Module
 * Manages undo/redo history and content versioning
 */

import { StorageManager } from "@/utils/storage";
import { HistoryEntry } from "@/types";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/monaco-editor/editor-history.ts loaded",
);

export class EditorHistory {
  private storage: StorageManager;
  private history: HistoryEntry[] = [];
  private historyIndex: number = -1;
  private maxHistorySize: number = 50;

  constructor(storagePrefix: string = "writer_editor_") {
    this.storage = new StorageManager(storagePrefix);
  }

  /**
   * Add entry to history
   */
  addToHistory(content: string, wordCount: number): void {
    this.history.splice(this.historyIndex + 1);

    this.history.push({
      content,
      timestamp: new Date().toISOString(),
      hash: this.generateHash(content + wordCount),
      message: `${wordCount} words`,
      author: "editor",
    });

    if (this.history.length > this.maxHistorySize) {
      this.history.shift();
    } else {
      this.historyIndex++;
    }

    this.storage.save("history", this.history);
  }

  /**
   * Undo last change
   */
  undo(editor: any, editorType: "monaco" | "codemirror"): boolean {
    if (editorType === "monaco" && editor) {
      editor.trigger("keyboard", "undo", null);
      return true;
    } else if (editor) {
      editor.execCommand("undo");
      return true;
    }
    return false;
  }

  /**
   * Redo change
   */
  redo(editor: any, editorType: "monaco" | "codemirror"): boolean {
    if (editorType === "monaco" && editor) {
      editor.trigger("keyboard", "redo", null);
      return true;
    } else if (editor) {
      editor.execCommand("redo");
      return true;
    }
    return false;
  }

  /**
   * Count words in text
   */
  countWords(text: string): number {
    const trimmed = text.trim();
    if (!trimmed) return 0;
    return trimmed.split(/\s+/).length;
  }

  /**
   * Generate simple hash for content
   */
  generateHash(content: string): string {
    let hash = 0;
    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash;
    }
    return hash.toString(36);
  }

  /**
   * Get current history
   */
  getHistory(): HistoryEntry[] {
    return this.history;
  }

  /**
   * Get current history index
   */
  getHistoryIndex(): number {
    return this.historyIndex;
  }
}
