/**
 * Toolbar & Keyboard Shortcut Manager
 * Wires all toolbar button click handlers and document-level keyboard shortcuts.
 * Extracted from WorkspaceOrchestrator to keep the orchestrator under the line limit.
 */

import type { PTYManager } from "../terminal/PTYManager";
import type { FileStateManager } from "../files/FileStateManager";
import type { FileTabManager } from "../files/FileTabManager";
import type { FileCommandHandler } from "../files/FileCommandHandler";
import type { MonacoManager } from "../editor/MonacoManager";
import type { CommitManager } from "../git/CommitManager";
import type { ShortcutsManager } from "./ShortcutsManager";

interface EmacsChordState {
  ctrlXPressed: boolean;
  timeout: number | null;
}

export class ToolbarManager {
  private ptyManager: PTYManager;
  private fileStateManager: FileStateManager;
  private fileTabManager: FileTabManager;
  private fileCommandHandler: FileCommandHandler;
  private monacoManager: MonacoManager;
  private commitManager: CommitManager;
  private shortcutsManager: ShortcutsManager;
  private runCurrentFile: () => Promise<void>;

  private emacsChordState: EmacsChordState = {
    ctrlXPressed: false,
    timeout: null,
  };

  constructor(
    ptyManager: PTYManager,
    fileStateManager: FileStateManager,
    fileTabManager: FileTabManager,
    fileCommandHandler: FileCommandHandler,
    monacoManager: MonacoManager,
    commitManager: CommitManager,
    shortcutsManager: ShortcutsManager,
    runCurrentFile: () => Promise<void>,
  ) {
    this.ptyManager = ptyManager;
    this.fileStateManager = fileStateManager;
    this.fileTabManager = fileTabManager;
    this.fileCommandHandler = fileCommandHandler;
    this.monacoManager = monacoManager;
    this.commitManager = commitManager;
    this.shortcutsManager = shortcutsManager;
    this.runCurrentFile = runCurrentFile;
  }

  attachAll(): void {
    this.attachToolbarButtons();
    this.attachKeyboardShortcuts();
    console.log("[ToolbarManager] All listeners attached");
  }

  private attachToolbarButtons(): void {
    document.getElementById("btn-save")?.addEventListener("click", () => {
      this.fileStateManager.saveCurrentFile();
    });

    document.getElementById("btn-delete")?.addEventListener("click", () => {
      const currentFile = this.fileStateManager.getCurrentFile();
      if (currentFile && currentFile !== "*scratch*") {
        this.fileCommandHandler.deleteFile(currentFile);
      }
    });

    document.getElementById("btn-commit")?.addEventListener("click", () => {
      this.commitManager.showCommitModal();
    });

    document.getElementById("btn-run")?.addEventListener("click", () => {
      this.runCurrentFile();
    });

    const keybindingMode = document.getElementById(
      "keybinding-mode",
    ) as HTMLSelectElement;
    keybindingMode?.addEventListener("change", (e) => {
      this.monacoManager.setKeybindingMode(
        (e.target as HTMLSelectElement).value,
      );
    });

    document
      .getElementById("monaco-theme-toggle")
      ?.addEventListener("click", () => {
        this.monacoManager.toggleEditorTheme();
      });

    document
      .getElementById("btn-editor-shortcuts")
      ?.addEventListener("click", () => {
        this.shortcutsManager.showEditorShortcuts();
      });

    document
      .getElementById("btn-terminal-shortcuts")
      ?.addEventListener("click", () => {
        this.shortcutsManager.showTerminalShortcuts();
      });

    document
      .getElementById("btn-copy-terminal")
      ?.addEventListener("click", () => {
        const terminal = this.ptyManager.getTerminal();
        if (terminal) {
          terminal.copyBuffer();
        }
      });
  }

  private attachKeyboardShortcuts(): void {
    document.addEventListener(
      "keydown",
      (e) => {
        const keybindingEl = document.getElementById(
          "keybinding-mode",
        ) as HTMLSelectElement;
        const keybindingMode = keybindingEl?.value || "emacs";
        const isEmacs = keybindingMode === "emacs";

        if (isEmacs && e.ctrlKey && e.key === "x" && !e.shiftKey && !e.altKey) {
          e.preventDefault();
          e.stopPropagation();
          this.startEmacsChord();
          console.log("[Emacs] C-x prefix started");
          return;
        }

        if (isEmacs && this.emacsChordState.ctrlXPressed && e.ctrlKey) {
          if (e.key === "f") {
            e.preventDefault();
            e.stopPropagation();
            this.clearEmacsChord();
            console.log(
              "[Emacs] C-x C-f triggered - showing inline new file input",
            );
            this.fileTabManager.triggerNewFileInput();
            return;
          }
          if (e.key === "s") {
            e.preventDefault();
            e.stopPropagation();
            this.clearEmacsChord();
            console.log("[Emacs] C-x C-s triggered - saving file");
            this.fileStateManager.saveCurrentFile();
            return;
          }
          this.clearEmacsChord();
        }

        if (e.ctrlKey && e.key === "s") {
          e.preventDefault();
          this.fileStateManager.saveCurrentFile();
        }

        if (!isEmacs && e.ctrlKey && e.key === "n") {
          e.preventDefault();
          this.fileTabManager.triggerNewFileInput();
        }

        if (e.ctrlKey && e.key === "Tab" && !e.shiftKey) {
          e.preventDefault();
          this.fileTabManager.switchToNextTab();
        }

        if (e.ctrlKey && e.shiftKey && e.key === "T") {
          e.preventDefault();
          this.ptyManager.createNewTerminal();
        }

        if (e.ctrlKey && e.key === "PageDown") {
          e.preventDefault();
          this.ptyManager.switchToNextTab();
        }
        if (e.ctrlKey && e.key === "PageUp") {
          e.preventDefault();
          this.ptyManager.switchToPrevTab();
        }
      },
      true,
    );
  }

  private startEmacsChord(): void {
    this.emacsChordState.ctrlXPressed = true;
    if (this.emacsChordState.timeout) {
      window.clearTimeout(this.emacsChordState.timeout);
    }
    this.emacsChordState.timeout = window.setTimeout(() => {
      this.clearEmacsChord();
      console.log("[Emacs] C-x chord timed out");
    }, 2000);
  }

  private clearEmacsChord(): void {
    this.emacsChordState.ctrlXPressed = false;
    if (this.emacsChordState.timeout) {
      window.clearTimeout(this.emacsChordState.timeout);
      this.emacsChordState.timeout = null;
    }
  }
}
