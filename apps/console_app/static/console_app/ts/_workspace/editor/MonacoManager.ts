/**
 * Monaco Editor Manager
 * Handles Monaco editor initialization, theme sync, and language detection
 */

import { LANGUAGE_MAP, type EditorConfig, type OpenFile } from "../core/types";
import {
  addEmacsKeybindings,
  addGlobalNavigationKeybindings,
  addRunCodeKeybinding,
} from "./MonacoKeybindings";

// MonacoTheme functions are loaded at runtime from shared components
declare function initializeMonacoThemes(monaco: any): void;
declare function setupMonacoThemeObserver(monaco: any): void;
declare function getThemeForMode(mode: "dark" | "light"): string;
declare function getCurrentThemeMode(): "dark" | "light";

// Dynamic loader for shared Monaco modules
async function loadMonacoTheme(): Promise<{
  initializeMonacoThemes: typeof initializeMonacoThemes;
  setupMonacoThemeObserver: typeof setupMonacoThemeObserver;
  getThemeForMode: typeof getThemeForMode;
  getCurrentThemeMode: typeof getCurrentThemeMode;
}> {
  // @ts-ignore - Runtime dynamic import
  return await import("@/monaco/MonacoTheme");
}

async function loadMonacoDefaults(): Promise<{
  MONACO_EDITOR_DEFAULTS: Record<string, any>;
}> {
  // @ts-ignore - Runtime dynamic import
  return await import("@/monaco/_MonacoDefaults");
}

// Cached module references
let monacoThemeModule: Awaited<ReturnType<typeof loadMonacoTheme>> | null =
  null;
let monacoDefaultsModule: Awaited<
  ReturnType<typeof loadMonacoDefaults>
> | null = null;

export class MonacoManager {
  private editor: any = null;
  private config: EditorConfig;

  constructor(config: EditorConfig) {
    this.config = config;
  }

  async initialize(language: string = "python"): Promise<void> {
    console.log(`[MonacoManager] Initializing with language: ${language}`);
    await this.createMonacoEditor(language);
    console.log("[MonacoManager] Initialization complete");
  }

  getEditor(): any {
    return this.editor;
  }

  /**
   * Update Monaco editor theme when global theme changes
   * This syncs Monaco with the global site theme using shared SciTeX themes
   */
  async updateTheme(theme: string): Promise<void> {
    if (!this.editor) {
      console.warn(
        "[MonacoManager] Cannot update theme - editor not initialized",
      );
      return;
    }

    const monaco = (window as any).monaco;
    if (!monaco) {
      console.warn(
        "[MonacoManager] Cannot update theme - Monaco not available",
      );
      return;
    }

    // Load theme module if not cached
    if (!monacoThemeModule) {
      monacoThemeModule = await loadMonacoTheme();
    }

    // Use SciTeX themes for consistency across modules
    const monacoTheme = monacoThemeModule.getThemeForMode(
      theme as "dark" | "light",
    );
    this.editor.updateOptions({ theme: monacoTheme });

    // Update toggle button to reflect new theme
    this.updateThemeToggleButton(monacoTheme);

    console.log(`[MonacoManager] Theme synced to global: ${monacoTheme}`);
  }

  /**
   * Toggle Monaco editor theme independently from global theme
   */
  toggleEditorTheme(): void {
    if (!this.editor) {
      console.warn(
        "[MonacoManager] Cannot toggle theme - editor not initialized",
      );
      return;
    }

    const monaco = (window as any).monaco;
    if (!monaco) {
      console.warn(
        "[MonacoManager] Cannot toggle theme - Monaco not available",
      );
      return;
    }

    // Get current theme from editor and toggle between SciTeX themes
    const currentTheme = this.editor.getOption(
      monaco.editor.EditorOption.theme,
    );
    const isDark = currentTheme === "scitex-dark" || currentTheme === "vs-dark";
    const newTheme = isDark ? "scitex-light" : "scitex-dark";

    // Update editor theme
    this.editor.updateOptions({ theme: newTheme });

    // Update toggle button emoji
    this.updateThemeToggleButton(newTheme);

    console.log(`[MonacoManager] Editor theme toggled to: ${newTheme}`);
  }

  /**
   * Get current Monaco editor theme
   */
  getCurrentTheme(): string {
    const monaco = (window as any).monaco;
    if (!this.editor || !monaco) return "vs-dark";
    return this.editor.getOption(monaco.editor.EditorOption.theme);
  }

  /**
   * Update theme toggle button emoji
   */
  private updateThemeToggleButton(theme: string): void {
    const toggleBtn = document.getElementById("monaco-theme-toggle");
    const themeIcon = toggleBtn?.querySelector(".theme-icon");

    if (themeIcon) {
      const isDark = theme === "scitex-dark" || theme === "vs-dark";
      themeIcon.textContent = isDark ? "🌙" : "☀️";
      toggleBtn?.setAttribute(
        "title",
        isDark ? "Switch to light theme" : "Switch to dark theme",
      );
    }
  }

  detectLanguage(filePath: string, content?: string): string {
    // First try to detect from shebang if content is provided
    if (content) {
      const firstLine = content.split("\n")[0];
      if (firstLine.startsWith("#!")) {
        const shebang = firstLine.toLowerCase();
        if (shebang.includes("python")) return "python";
        if (shebang.includes("bash") || shebang.includes("/sh")) return "shell";
        if (shebang.includes("node")) return "javascript";
        if (shebang.includes("ruby")) return "ruby";
        if (shebang.includes("perl")) return "perl";
      }
    }

    // Fallback to extension detection
    const ext = filePath.substring(filePath.lastIndexOf("."));
    return LANGUAGE_MAP[ext] || "plaintext";
  }

  private async createMonacoEditor(language: string = "python"): Promise<void> {
    // Wait for Monaco to be available
    await this.waitForMonaco();

    const monaco = (window as any).monaco;
    if (!monaco) {
      console.warn(
        "[MonacoManager] Monaco not available - keeping welcome screen",
      );
      return;
    }

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

    // Load shared modules if not cached
    if (!monacoThemeModule) {
      monacoThemeModule = await loadMonacoTheme();
    }
    if (!monacoDefaultsModule) {
      monacoDefaultsModule = await loadMonacoDefaults();
    }

    // Initialize shared SciTeX themes
    monacoThemeModule.initializeMonacoThemes(monaco);

    // Always sync with global site theme
    const initialTheme = monacoThemeModule.getThemeForMode(
      monacoThemeModule.getCurrentThemeMode(),
    );

    // Setup observer to auto-switch Monaco theme when global theme changes
    monacoThemeModule.setupMonacoThemeObserver(monaco);

    // Create Monaco editor using shared defaults
    const { MONACO_EDITOR_DEFAULTS } = monacoDefaultsModule;
    this.editor = monaco.editor.create(container, {
      ...MONACO_EDITOR_DEFAULTS,
      value: "",
      language: language,
      theme: initialTheme,
    });

    console.log("[MonacoManager] Monaco editor created successfully");

    // Initialize theme toggle button
    this.updateThemeToggleButton(initialTheme);

    // Add global navigation shortcuts FIRST (highest priority)
    addGlobalNavigationKeybindings(this.editor, monaco);

    // Apply saved keybinding mode
    const savedMode = localStorage.getItem("code-keybinding-mode") || "emacs";
    this.setKeybindingMode(savedMode);

    // Add Ctrl+Enter keybinding AFTER setting mode (so it doesn't get cleared)
    addRunCodeKeybinding(this.editor, monaco);
  }

  private async waitForMonaco(): Promise<void> {
    return new Promise<void>((resolve) => {
      if ((window as any).monaco) {
        console.log("[MonacoManager] Monaco already available");
        resolve();
        return;
      }

      if ((window as any).monacoReady) {
        console.log(
          "[MonacoManager] Monaco ready flag set, waiting for object...",
        );
        setTimeout(() => resolve(), 100);
        return;
      }

      let attempts = 0;
      const maxAttempts = 100;
      const checkInterval = 100;

      const checkMonaco = () => {
        attempts++;

        if ((window as any).monaco) {
          console.log(
            `[MonacoManager] Monaco loaded after ${attempts * checkInterval}ms`,
          );
          resolve();
        } else if ((window as any).monacoReady && attempts > 5) {
          console.error(
            "[MonacoManager] monacoReady flag set but window.monaco is undefined",
          );
          resolve();
        } else if (attempts < maxAttempts) {
          setTimeout(checkMonaco, checkInterval);
        } else {
          console.error(
            `[MonacoManager] Monaco timeout after ${attempts * checkInterval}ms`,
          );
          resolve();
        }
      };

      const eventHandler = () => {
        console.log("[MonacoManager] monaco-ready event received");
        setTimeout(() => resolve(), 50);
      };
      window.addEventListener("monaco-ready", eventHandler, { once: true });

      checkMonaco();
    });
  }

  setKeybindingMode(mode: string): void {
    if (!this.editor) return;

    const monaco = (window as any).monaco;
    if (!monaco) return;

    // Remove previous Emacs event listener if exists
    if ((this.editor as any)._emacsPreventDefaultHandler) {
      document.removeEventListener(
        "keydown",
        (this.editor as any)._emacsPreventDefaultHandler,
        true,
      );
      (this.editor as any)._emacsPreventDefaultHandler = null;
    }

    // Remove all custom keybindings
    if ((this.editor as any)._standaloneKeybindingService) {
      (this.editor as any)._standaloneKeybindingService._dynamicKeybindings =
        [];
    }

    if (mode === "vim") {
      console.log(
        "[Keybindings] Vim mode selected (requires monaco-vim extension)",
      );
    } else if (mode === "emacs") {
      console.log("[Keybindings] Emacs mode selected");
      addEmacsKeybindings(this.editor, monaco);
    } else {
      console.log("[Keybindings] VS Code mode selected");
    }

    this.updateTooltipsForMode(mode);
    localStorage.setItem("code-keybinding-mode", mode);
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

    console.log("[Tooltips] Updated for", mode, "mode");
  }
}
