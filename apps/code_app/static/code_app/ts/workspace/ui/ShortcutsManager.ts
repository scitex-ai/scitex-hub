/**
 * Shortcuts Manager
 * Handles keyboard shortcuts help modals
 */

import type { ModalManager } from "./ModalManager.js";

export class ShortcutsManager {
  constructor(private modalManager: ModalManager) {}

  /**
   * Show editor shortcuts modal
   */
  showEditorShortcuts(): void {
    const keybindingMode = (document.getElementById("keybinding-mode") as HTMLSelectElement)?.value || "emacs";
    const content = this.generateShortcutsContent(keybindingMode);

    this.modalManager.showModal({
      title: '<i class="fas fa-keyboard"></i> Editor Shortcuts',
      content: content,
      showCopyButton: true,
      showPrintButton: true,
      maxWidth: "800px",
    });
  }

  /**
   * Show terminal shortcuts modal
   */
  showTerminalShortcuts(): void {
    const content = `
      <h3>Navigation</h3>
      <ul>
        <li><kbd>C-a</kbd> / <kbd>C-e</kbd> - Beginning/End of line</li>
        <li><kbd>C-f</kbd> / <kbd>C-b</kbd> - Forward/Backward character</li>
      </ul>

      <h3>History</h3>
      <ul>
        <li><kbd>M-p</kbd> / <kbd>M-n</kbd> - Previous/Next command</li>
        <li><kbd>Up</kbd> / <kbd>Down</kbd> - Previous/Next command (alternative)</li>
      </ul>

      <h3>Editing</h3>
      <ul>
        <li><kbd>C-d</kbd> - Delete character at cursor</li>
        <li><kbd>C-k</kbd> - Kill line (delete to end, copy to clipboard)</li>
        <li><kbd>C-y</kbd> - Yank (paste from clipboard)</li>
        <li><kbd>Tab</kbd> - File/command completion</li>
      </ul>

      <h3>Other</h3>
      <ul>
        <li><kbd>C-l</kbd> - Clear terminal screen</li>
        <li><kbd>C-m</kbd> or <kbd>Enter</kbd> - Execute command</li>
      </ul>
    `;

    this.modalManager.showModal({
      title: '<i class="fas fa-terminal"></i> Terminal Shortcuts',
      content,
      showCopyButton: true,
      showPrintButton: true,
      maxWidth: "700px",
    });
  }

  /**
   * Generate shortcuts content based on keybinding mode
   */
  private generateShortcutsContent(mode: string): string {
    const commonShortcuts = `
      <h3>File Operations</h3>
      <ul>
        <li><kbd>Ctrl+S</kbd> - Save current file</li>
        <li><kbd>Ctrl+N</kbd> - Create new file</li>
        <li><kbd>Ctrl+Tab</kbd> - Next file tab</li>
      </ul>
      <h3>Terminal</h3>
      <ul>
        <li><kbd>Ctrl+Shift+T</kbd> - New terminal tab</li>
        <li><kbd>Ctrl+PageDown</kbd> - Next terminal tab</li>
        <li><kbd>Ctrl+PageUp</kbd> - Previous terminal tab</li>
      </ul>
    `;

    if (mode === "emacs") {
      return `
        <h3>Emacs Mode</h3>
        ${commonShortcuts}
        <h3>Emacs Navigation</h3>
        <ul>
          <li><kbd>Ctrl+F</kbd> or <kbd>Alt+N</kbd> - Move forward (right)</li>
          <li><kbd>Ctrl+B</kbd> - Move backward (left)</li>
          <li><kbd>Ctrl+N</kbd> or <kbd>Alt+N</kbd> - Next line (down)</li>
          <li><kbd>Ctrl+P</kbd> or <kbd>Alt+P</kbd> - Previous line (up)</li>
          <li><kbd>Ctrl+A</kbd> - Beginning of line</li>
          <li><kbd>Ctrl+E</kbd> - End of line</li>
          <li><kbd>Alt+F</kbd> - Forward word</li>
          <li><kbd>Alt+B</kbd> - Backward word</li>
        </ul>
      `;
    } else if (mode === "vim") {
      return `
        <h3>Vim Mode</h3>
        ${commonShortcuts}
        <h3>Vim Navigation</h3>
        <ul>
          <li><kbd>h</kbd> - Move left (normal mode)</li>
          <li><kbd>j</kbd> - Move down (normal mode)</li>
          <li><kbd>k</kbd> - Move up (normal mode)</li>
          <li><kbd>l</kbd> - Move right (normal mode)</li>
          <li><kbd>i</kbd> - Insert mode</li>
          <li><kbd>Esc</kbd> - Normal mode</li>
          <li><kbd>:w</kbd> - Save file</li>
        </ul>
      `;
    } else {
      return `
        <h3>VS Code Mode</h3>
        ${commonShortcuts}
        <h3>Standard Navigation</h3>
        <ul>
          <li><kbd>Arrow Keys</kbd> - Navigate</li>
          <li><kbd>Home</kbd> - Beginning of line</li>
          <li><kbd>End</kbd> - End of line</li>
          <li><kbd>Ctrl+Home</kbd> - Beginning of file</li>
          <li><kbd>Ctrl+End</kbd> - End of file</li>
        </ul>
      `;
    }
  }
}
