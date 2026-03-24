/**
 * Monaco Editor Manager — console_app thin wrapper
 * Delegates to scitex-ui MonacoEditor for core functionality.
 * Keeps only console-specific: navigation shortcuts, run-code, tooltips.
 */

import type { EditorConfig } from "../core/types";
import {
  MonacoEditor,
  detectLanguage,
} from "scitex-ui/ts/app/monaco-editor/index";
import {
  addGlobalNavigationKeybindings,
  addRunCodeKeybinding,
} from "./MonacoKeybindings";

export class MonacoManager {
  private monacoEditor: MonacoEditor | null = null;
  private config: EditorConfig;

  constructor(config: EditorConfig) {
    this.config = config;
  }

  async initialize(language: string = "python"): Promise<void> {
    const container = document.getElementById("monaco-editor");
    if (!container) {
      console.error("[MonacoManager] Monaco container not found");
      return;
    }

    // Hide welcome screen
    const welcomeScreen = document.getElementById("welcome-screen");
    if (welcomeScreen) {
      welcomeScreen.style.display = "none";
    }

    // Create editor via scitex-ui
    this.monacoEditor = new MonacoEditor({
      container,
      language,
      value: "",
      keybindingMode:
        (localStorage.getItem("scitex-keybinding-mode") as any) || "emacs",
    });
    await this.monacoEditor.initialize();

    const editor = this.monacoEditor.getEditor();
    const monaco = this.monacoEditor.getMonaco();
    if (!editor || !monaco) return;

    // Console-specific: navigation shortcuts (Alt+Z/F/S/C/V/W)
    addGlobalNavigationKeybindings(editor, monaco);

    // Console-specific: Ctrl+Enter to run code
    addRunCodeKeybinding(editor, monaco);

    // Initialize theme toggle button
    this.updateThemeToggleButton(this.monacoEditor.getCurrentTheme());
  }

  getEditor(): any {
    return this.monacoEditor?.getEditor() ?? null;
  }

  async updateTheme(theme: string): Promise<void> {
    if (!this.monacoEditor) return;
    this.monacoEditor.updateTheme(theme as "dark" | "light");
    this.updateThemeToggleButton(this.monacoEditor.getCurrentTheme());
  }

  toggleEditorTheme(): void {
    if (!this.monacoEditor) return;
    this.monacoEditor.toggleTheme();
    this.updateThemeToggleButton(this.monacoEditor.getCurrentTheme());
  }

  getCurrentTheme(): string {
    return this.monacoEditor?.getCurrentTheme() ?? "scitex-dark";
  }

  detectLanguage(filePath: string, content?: string): string {
    return detectLanguage(filePath, content);
  }

  setKeybindingMode(mode: string): void {
    if (!this.monacoEditor) return;
    this.monacoEditor.setKeybindingMode(mode as "emacs" | "vim" | "vscode");
    this.updateTooltipsForMode(mode);
  }

  private updateThemeToggleButton(theme: string): void {
    const toggleBtn = document.getElementById("monaco-theme-toggle");
    const themeIcon = toggleBtn?.querySelector(".theme-icon");
    if (themeIcon) {
      const isDark = theme === "scitex-dark" || theme === "vs-dark";
      themeIcon.textContent = isDark ? "\u{1F319}" : "\u{2600}\u{FE0F}";
      toggleBtn?.setAttribute(
        "title",
        isDark ? "Switch to light theme" : "Switch to dark theme",
      );
    }
  }

  private updateTooltipsForMode(mode: string): void {
    const btnSave = document.getElementById("btn-save") as HTMLButtonElement;
    const btnNewFileTab = document.getElementById(
      "btn-new-file-tab",
    ) as HTMLButtonElement;
    const btnDelete = document.getElementById(
      "btn-delete",
    ) as HTMLButtonElement;
    const btnRun = document.getElementById("btn-run") as HTMLButtonElement;

    if (mode === "emacs") {
      if (btnSave) btnSave.title = "Save (C-x C-s or C-s)";
      if (btnNewFileTab) btnNewFileTab.title = "New file (C-x C-f)";
      if (btnDelete) btnDelete.title = "Delete file";
      if (btnRun) btnRun.title = "Run Python script (Ctrl+Enter)";
    } else if (mode === "vim") {
      if (btnSave) btnSave.title = "Save (:w or Ctrl+S)";
      if (btnNewFileTab) btnNewFileTab.title = "New file (:e filename)";
      if (btnDelete) btnDelete.title = "Delete file (:bd)";
      if (btnRun) btnRun.title = "Run Python script (Ctrl+Enter)";
    } else {
      if (btnSave) btnSave.title = "Save (Ctrl+S)";
      if (btnNewFileTab) btnNewFileTab.title = "New file (Ctrl+N)";
      if (btnDelete) btnDelete.title = "Delete file";
      if (btnRun) btnRun.title = "Run Python script (Ctrl+Enter)";
    }
  }
}
