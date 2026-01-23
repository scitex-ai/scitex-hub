/**
 * Cursor Manager Module
 * Manages cursor position persistence across section switches
 */

import { StorageManager } from "@/utils/storage";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/monaco-editor/cursor-manager.ts loaded",
);

export class CursorManager {
  private storage: StorageManager;
  private currentSectionId: string = "";

  constructor(storagePrefix: string = "writer_editor_") {
    this.storage = new StorageManager(storagePrefix);
  }

  /**
   * Generate simple hash for content
   */
  private generateHash(content: string): string {
    let hash = 0;
    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash;
    }
    return hash.toString(36);
  }

  /**
   * Save cursor position for a section (like Emacs save-place)
   */
  saveCursorPosition(monacoEditor: any, sectionId: string): void {
    if (!monacoEditor || !sectionId) return;

    const position = monacoEditor.getPosition();
    const content = monacoEditor.getValue();
    const contentHash = this.generateHash(content);

    const cursorData = {
      lineNumber: position.lineNumber,
      column: position.column,
      contentHash: contentHash,
      timestamp: Date.now(),
    };

    this.storage.save(`cursor_${sectionId}`, cursorData);
    console.log(
      `[Editor] Saved cursor position for ${sectionId}:`,
      cursorData.lineNumber,
      ":",
      cursorData.column,
    );
  }

  /**
   * Restore cursor position for a section if content hash matches
   */
  restoreCursorPosition(monacoEditor: any, sectionId: string, content: string): void {
    if (!monacoEditor || !sectionId) return;

    const savedData = this.storage.load<any>(`cursor_${sectionId}`);
    if (!savedData) {
      console.log(`[Editor] No saved cursor position for ${sectionId}`);
      return;
    }

    const currentHash = this.generateHash(content);
    if (savedData.contentHash !== currentHash) {
      console.log(
        `[Editor] Content changed for ${sectionId}, not restoring cursor (hash mismatch)`,
      );
      return;
    }

    // Restore cursor position
    const position = {
      lineNumber: savedData.lineNumber,
      column: savedData.column,
    };

    // Use setTimeout to ensure editor is fully rendered
    setTimeout(() => {
      monacoEditor.setPosition(position);
      monacoEditor.revealPositionInCenter(position);
      monacoEditor.focus(); // Activate cursor automatically
      console.log(
        `[Editor] Restored cursor position for ${sectionId}:`,
        position.lineNumber,
        ":",
        position.column,
      );
    }, 50);
  }

  /**
   * Set content with optional section ID for cursor position management
   */
  setContentForSection(
    monacoEditor: any,
    sectionId: string,
    content: string,
    setContentFn: (content: string) => void
  ): void {
    // Save cursor position for current section before switching
    if (this.currentSectionId && this.currentSectionId !== sectionId) {
      this.saveCursorPosition(monacoEditor, this.currentSectionId);
    }

    // Update current section
    this.currentSectionId = sectionId;

    // Set content
    setContentFn(content);

    // Restore cursor position for new section
    const savedData = this.storage.load<any>(`cursor_${sectionId}`);
    if (savedData) {
      this.restoreCursorPosition(monacoEditor, sectionId, content);
    } else {
      // No saved cursor position, just focus the editor
      setTimeout(() => {
        if (monacoEditor) {
          monacoEditor.focus();
          console.log(
            `[Editor] No saved cursor for ${sectionId}, focused editor at start`,
          );
        }
      }, 50);
    }
  }

  /**
   * Get current section ID
   */
  getCurrentSectionId(): string {
    return this.currentSectionId;
  }

  /**
   * Set current section ID
   */
  setCurrentSectionId(sectionId: string): void {
    this.currentSectionId = sectionId;
  }
}
