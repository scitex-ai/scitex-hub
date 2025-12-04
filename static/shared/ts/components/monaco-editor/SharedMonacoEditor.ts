/**
 * Shared Monaco Editor
 * A reusable Monaco editor component used across /code/, /writer/, and other pages
 * Ensures consistent theming and behavior across the application
 */

import { MonacoEditorConfig, LANGUAGE_MAP } from "./types.js";

export class SharedMonacoEditor {
  private editor: any = null;
  private config: MonacoEditorConfig;
  private storageKeyPrefix: string;

  constructor(config: MonacoEditorConfig) {
    this.config = {
      language: "plaintext",
      value: "",
      readOnly: false,
      minimap: true,
      lineNumbers: "on",
      wordWrap: "on",
      fontSize: 14,
      tabSize: 4,
      storageKeyPrefix: "monaco",
      ...config,
    };
    this.storageKeyPrefix = this.config.storageKeyPrefix || "monaco";
  }

  /**
   * Initialize the Monaco editor
   */
  async initialize(): Promise<any> {
    console.log(`[SharedMonacoEditor] Initializing for container: ${this.config.containerId}`);
    await this.waitForMonaco();
    return this.createEditor();
  }

  /**
   * Get the Monaco editor instance
   */
  getEditor(): any {
    return this.editor;
  }

  /**
   * Get the Monaco namespace
   */
  getMonaco(): any {
    return (window as any).monaco;
  }

  /**
   * Update editor theme based on global site theme
   * Uses standard vs-dark/vs themes for consistency
   */
  updateTheme(theme: string): void {
    if (!this.editor) {
      console.warn("[SharedMonacoEditor] Cannot update theme - editor not initialized");
      return;
    }

    const monaco = (window as any).monaco;
    if (!monaco) {
      console.warn("[SharedMonacoEditor] Cannot update theme - Monaco not available");
      return;
    }

    // Use standard Monaco themes only (vs-dark / vs)
    const monacoTheme = theme === "dark" ? "vs-dark" : "vs";
    this.editor.updateOptions({ theme: monacoTheme });

    // Save preference
    localStorage.setItem(`${this.storageKeyPrefix}-editor-theme`, monacoTheme);

    // Update toggle button if exists
    this.updateThemeToggleButton(monacoTheme);

    console.log(`[SharedMonacoEditor] Theme updated to: ${monacoTheme}`);
  }

  /**
   * Toggle between light and dark themes
   */
  toggleTheme(): void {
    if (!this.editor) {
      console.warn("[SharedMonacoEditor] Cannot toggle theme - editor not initialized");
      return;
    }

    const monaco = (window as any).monaco;
    if (!monaco) return;

    const currentTheme = this.editor.getOption(monaco.editor.EditorOption.theme);
    const newTheme = currentTheme === "vs-dark" ? "vs" : "vs-dark";

    this.editor.updateOptions({ theme: newTheme });
    localStorage.setItem(`${this.storageKeyPrefix}-editor-theme`, newTheme);
    this.updateThemeToggleButton(newTheme);

    console.log(`[SharedMonacoEditor] Theme toggled to: ${newTheme}`);
  }

  /**
   * Get current theme
   */
  getCurrentTheme(): string {
    const monaco = (window as any).monaco;
    if (!this.editor || !monaco) return "vs-dark";
    return this.editor.getOption(monaco.editor.EditorOption.theme);
  }

  /**
   * Set editor content
   */
  setValue(content: string): void {
    if (this.editor) {
      this.editor.setValue(content);
    }
  }

  /**
   * Get editor content
   */
  getValue(): string {
    return this.editor ? this.editor.getValue() : "";
  }

  /**
   * Set editor language
   */
  setLanguage(language: string): void {
    if (this.editor) {
      const monaco = (window as any).monaco;
      const model = this.editor.getModel();
      if (model && monaco) {
        monaco.editor.setModelLanguage(model, language);
      }
    }
  }

  /**
   * Set read-only mode
   */
  setReadOnly(readOnly: boolean): void {
    if (this.editor) {
      this.editor.updateOptions({ readOnly });
    }
  }

  /**
   * Detect language from file path
   */
  detectLanguage(filePath: string, content?: string): string {
    // Try shebang detection first
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
    const ext = filePath.substring(filePath.lastIndexOf(".")).toLowerCase();
    return LANGUAGE_MAP[ext] || "plaintext";
  }

  /**
   * Add a custom keybinding
   */
  addKeybinding(keyMod: number, keyCode: number, handler: () => void): void {
    if (this.editor) {
      const monaco = (window as any).monaco;
      this.editor.addCommand(keyMod | keyCode, handler);
    }
  }

  /**
   * Focus the editor
   */
  focus(): void {
    if (this.editor) {
      this.editor.focus();
    }
  }

  /**
   * Dispose the editor
   */
  dispose(): void {
    if (this.editor) {
      this.editor.dispose();
      this.editor = null;
    }
  }

  // Private methods

  private updateThemeToggleButton(theme: string): void {
    const toggleBtn = document.getElementById("monaco-theme-toggle");
    const themeIcon = toggleBtn?.querySelector(".theme-icon");

    if (themeIcon) {
      themeIcon.textContent = theme === "vs-dark" ? "🌙" : "☀️";
      toggleBtn?.setAttribute(
        "title",
        theme === "vs-dark" ? "Switch to light theme" : "Switch to dark theme"
      );
    }
  }

  private async waitForMonaco(): Promise<void> {
    return new Promise<void>((resolve) => {
      if ((window as any).monaco) {
        console.log("[SharedMonacoEditor] Monaco already available");
        resolve();
        return;
      }

      let attempts = 0;
      const maxAttempts = 100;
      const checkInterval = 100;

      const checkMonaco = () => {
        attempts++;

        if ((window as any).monaco) {
          console.log(`[SharedMonacoEditor] Monaco loaded after ${attempts * checkInterval}ms`);
          resolve();
        } else if (attempts < maxAttempts) {
          setTimeout(checkMonaco, checkInterval);
        } else {
          console.error(`[SharedMonacoEditor] Monaco timeout after ${attempts * checkInterval}ms`);
          resolve();
        }
      };

      window.addEventListener("monaco-ready", () => {
        console.log("[SharedMonacoEditor] monaco-ready event received");
        setTimeout(() => resolve(), 50);
      }, { once: true });

      checkMonaco();
    });
  }

  private createEditor(): any {
    const monaco = (window as any).monaco;
    if (!monaco) {
      console.error("[SharedMonacoEditor] Monaco not available");
      return null;
    }

    const container = document.getElementById(this.config.containerId);
    if (!container) {
      console.error(`[SharedMonacoEditor] Container not found: ${this.config.containerId}`);
      return null;
    }

    // Determine initial theme - use standard vs-dark/vs only
    const savedTheme = localStorage.getItem(`${this.storageKeyPrefix}-editor-theme`);
    const documentTheme = document.documentElement.getAttribute("data-theme");
    const initialTheme = savedTheme || (documentTheme === "dark" ? "vs-dark" : "vs");

    // Create editor with consistent options
    this.editor = monaco.editor.create(container, {
      value: this.config.value || "",
      language: this.config.language,
      theme: initialTheme,
      automaticLayout: true,
      fontSize: this.config.fontSize,
      fontFamily: "'JetBrains Mono', 'Monaco', 'Menlo', monospace",
      minimap: { enabled: this.config.minimap },
      lineNumbers: this.config.lineNumbers,
      renderWhitespace: "selection",
      scrollBeyondLastLine: false,
      wordWrap: this.config.wordWrap,
      tabSize: this.config.tabSize,
      insertSpaces: true,
      glyphMargin: true,
      folding: true,
      readOnly: this.config.readOnly,
    });

    console.log("[SharedMonacoEditor] Editor created successfully");

    // Update theme toggle button state
    this.updateThemeToggleButton(initialTheme);

    // Listen for global theme changes
    window.addEventListener("theme-changed", (event: Event) => {
      const customEvent = event as CustomEvent<{ theme: string }>;
      if (customEvent.detail?.theme) {
        this.updateTheme(customEvent.detail.theme);
      }
    });

    return this.editor;
  }
}

// Export for global access
(window as any).SharedMonacoEditor = SharedMonacoEditor;
