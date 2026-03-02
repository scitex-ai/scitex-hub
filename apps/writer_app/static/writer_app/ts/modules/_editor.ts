/**
 * Writer Editor Module
 * Handles CodeMirror editor initialization and management
 */

import { StorageManager } from "@/utils/storage";
import { HistoryEntry } from "@/types";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/editor.ts loaded",
);
export interface EditorConfig {
  elementId: string;
  mode?: string;
  theme?: string;
  lineNumbers?: boolean;
  lineWrapping?: boolean;
  indentUnit?: number;
}

export class WriterEditor {
  private editor: any; // CodeMirror editor instance
  private storage: StorageManager;
  private history: HistoryEntry[] = [];
  private historyIndex: number = -1;
  private maxHistorySize: number = 50;
  private onChangeCallback?: (content: string, wordCount: number) => void;

  constructor(config: EditorConfig) {
    this.storage = new StorageManager("writer_editor_");

    // Initialize CodeMirror if available
    if ((window as any).CodeMirror) {
      const element = document.getElementById(config.elementId);
      if (!element) {
        throw new Error(
          `Editor element with id "${config.elementId}" not found`,
        );
      }

      this.editor = (window as any).CodeMirror.fromTextArea(element, {
        mode: config.mode || "text/x-latex",
        theme: config.theme || "default",
        lineNumbers: config.lineNumbers !== false,
        lineWrapping: config.lineWrapping !== false,
        indentUnit: config.indentUnit || 4,
        tabSize: 4,
        indentWithTabs: false,
        autoCloseBrackets: true,
        matchBrackets: true,
      });

      this.setupEditor();
    } else {
      console.warn(
        "[Editor] CodeMirror not found. Editor will not be initialized.",
      );
    }
  }

  /**
   * Setup editor event listeners
   */
  private setupEditor(): void {
    if (!this.editor) return;

    // Track changes
    this.editor.on("change", (editor: any) => {
      const content = editor.getValue();
      const wordCount = this.countWords(content);

      if (this.onChangeCallback) {
        this.onChangeCallback(content, wordCount);
      }
    });

    // Track undo/redo
    this.editor.on("beforeChange", (_editor: any, change: any) => {
      if (change.origin === "undo" || change.origin === "redo") {
        // Handle undo/redo
      }
    });

    console.log("[Editor] CodeMirror initialized");
  }

  /**
   * Get editor content
   */
  getContent(): string {
    return this.editor ? this.editor.getValue() : "";
  }

  /**
   * Set editor content
   */
  setContent(content: string, emitChange: boolean = false): void {
    if (!this.editor) return;

    const doc = this.editor.getDoc();
    const lastLine = doc.lastLine();

    this.editor.replaceRange(
      content,
      { line: 0, ch: 0 },
      { line: lastLine, ch: doc.getLine(lastLine).length },
    );

    if (emitChange) {
      this.editor.execCommand("goDocEnd");
    }
  }

  /**
   * Add content to editor
   */
  appendContent(content: string): void {
    if (!this.editor) return;

    const doc = this.editor.getDoc();
    const lastLine = doc.lastLine();
    doc.replaceRange(content, {
      line: lastLine,
      ch: doc.getLine(lastLine).length,
    });
  }

  /**
   * Clear editor content
   */
  clear(): void {
    this.setContent("");
  }

  /**
   * Add entry to history
   */
  addToHistory(content: string, wordCount: number): void {
    // Remove any redo history when adding new entry
    this.history.splice(this.historyIndex + 1);

    // Add new entry
    this.history.push({
      content,
      timestamp: new Date().toISOString(),
      hash: this.generateHash(content + wordCount),
      message: `${wordCount} words`,
      author: "editor",
    });

    // Limit history size
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
  undo(): boolean {
    if (this.historyIndex > 0) {
      this.historyIndex--;
      const entry = this.history[this.historyIndex];
      if (entry.content !== undefined) {
        this.setContent(entry.content);
      }
      return true;
    }
    return false;
  }

  /**
   * Redo change
   */
  redo(): boolean {
    if (this.historyIndex < this.history.length - 1) {
      this.historyIndex++;
      const entry = this.history[this.historyIndex];
      if (entry.content !== undefined) {
        this.setContent(entry.content);
      }
      return true;
    }
    return false;
  }

  /**
   * Check if can undo
   */
  canUndo(): boolean {
    return this.historyIndex > 0;
  }

  /**
   * Check if can redo
   */
  canRedo(): boolean {
    return this.historyIndex < this.history.length - 1;
  }

  /**
   * Load history from storage
   */
  loadHistory(): void {
    const stored = this.storage.load<HistoryEntry[]>("history");
    if (stored) {
      this.history = stored;
      this.historyIndex = stored.length - 1;
    }
  }

  /**
   * Count words in text
   */
  private countWords(text: string): number {
    const trimmed = text.trim();
    if (!trimmed) return 0;
    return trimmed.split(/\s+/).length;
  }

  /**
   * Generate simple hash for content
   */
  private generateHash(content: string): string {
    let hash = 0;
    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return hash.toString(36);
  }

  /**
   * Get word count of current content
   */
  getWordCount(): number {
    return this.countWords(this.getContent());
  }

  /**
   * Set change callback
   */
  onChange(callback: (content: string, wordCount: number) => void): void {
    this.onChangeCallback = callback;
  }

  /**
   * Focus editor
   */
  focus(): void {
    if (this.editor) {
      this.editor.focus();
    }
  }

  /**
   * Check if editor has unsaved changes
   */
  hasUnsavedChanges(lastSavedContent: string): boolean {
    return this.getContent() !== lastSavedContent;
  }

  /**
   * Get editor instance (for advanced usage)
   */
  getInstance(): any {
    return this.editor;
  }

  /**
   * Toggle editor theme (no-op for CodeMirror, implemented for interface compatibility)
   */
  toggleEditorTheme(): void {
    console.warn("[Editor] Theme toggle not supported for CodeMirror editor");
  }
}
