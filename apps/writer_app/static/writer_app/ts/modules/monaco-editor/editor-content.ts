/**
 * Editor Content Module
 * Manages editor content operations (get, set, append, clear)
 */

import { SpellChecker } from "../spell-checker.js";
import { EditorHistory } from "./editor-history.js";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/monaco-editor/editor-content.ts loaded",
);

export class EditorContent {
  private editor: any;
  private monacoEditor: any;
  private editorType: "monaco" | "codemirror";
  private spellChecker?: SpellChecker;
  private history: EditorHistory;

  constructor(
    editor: any,
    monacoEditor: any,
    editorType: "monaco" | "codemirror",
    spellChecker: SpellChecker | undefined,
    history: EditorHistory
  ) {
    this.editor = editor;
    this.monacoEditor = monacoEditor;
    this.editorType = editorType;
    this.spellChecker = spellChecker;
    this.history = history;
  }

  /**
   * Get editor content
   */
  getContent(): string {
    if (!this.editor) return "";
    return this.editorType === "monaco"
      ? this.monacoEditor.getValue()
      : this.editor.getValue();
  }

  /**
   * Set editor content
   */
  setContent(content: string, emitChange: boolean = false): void {
    if (!this.editor) return;

    if (this.editorType === "monaco") {
      this.monacoEditor.setValue(content);

      // Trigger spell check on existing content after a short delay
      // to ensure dictionary is loaded
      if (this.spellChecker && content.length > 0) {
        setTimeout(() => {
          if (this.spellChecker) {
            this.spellChecker.recheckAll();
          }
        }, 1500); // Wait 1.5s for dictionary to load
      }
    } else {
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
  }

  /**
   * Append content to editor
   */
  appendContent(content: string): void {
    if (!this.editor) return;

    if (this.editorType === "monaco") {
      const currentContent = this.monacoEditor.getValue();
      this.monacoEditor.setValue(currentContent + content);
    } else {
      const doc = this.editor.getDoc();
      const lastLine = doc.lastLine();
      doc.replaceRange(content, {
        line: lastLine,
        ch: doc.getLine(lastLine).length,
      });
    }
  }

  /**
   * Clear editor content
   */
  clear(): void {
    this.setContent("");
  }

  /**
   * Get word count of current content
   */
  getWordCount(): number {
    return this.history.countWords(this.getContent());
  }

  /**
   * Check if editor has unsaved changes
   */
  hasUnsavedChanges(lastSavedContent: string): boolean {
    return this.getContent() !== lastSavedContent;
  }
}
