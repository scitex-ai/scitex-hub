/**
 * Monaco Editor Module
 * Enhanced editor with Monaco Editor capabilities
 * Falls back to CodeMirror if Monaco is not available
 *
 * This is the main orchestrator that delegates to specialized modules:
 * - EditorHistory: Undo/redo and history management
 * - CursorManager: Cursor position persistence
 * - EditorContent: Content operations
 * - EditorConfig: Configuration management
 * - SpellCheckIntegration: Spell checking
 */

import { SpellChecker, injectSpellCheckStyles } from "./spell-checker.js";
import {
  registerLatexLanguage,
  registerLatexCompletionProvider,
  registerCitationCompletionProvider,
  registerCitationHoverProvider,
  defineScitexTheme,
  createMonacoEditor,
  setupThemeObserver,
} from "./monaco-editor/monaco-init.js";
import {
  setupMonacoEditorListeners,
  setupCitationDropZone,
  setupCitationProtection,
  setupSuggestionWidgetObserver,
} from "./monaco-editor/monaco-features.js";
import { EditorHistory } from "./monaco-editor/editor-history.js";
import { CursorManager } from "./monaco-editor/cursor-manager.js";
import { EditorContent } from "./monaco-editor/editor-content.js";
import { EditorConfig } from "./monaco-editor/editor-config.js";
import { SpellCheckIntegration } from "./monaco-editor/spell-check-integration.js";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/monaco-editor.ts loaded",
);

export interface MonacoEditorConfig {
  elementId: string;
  mode?: string;
  theme?: string;
  lineNumbers?: boolean;
  lineWrapping?: boolean;
  indentUnit?: number;
  useMonaco?: boolean;
}

export class EnhancedEditor {
  // Editor instances
  private editor: any; // Monaco or CodeMirror instance
  private editorType: "monaco" | "codemirror" = "codemirror";
  private monacoEditor?: any;
  private spellChecker?: SpellChecker;

  // Callbacks
  private onChangeCallback?: (content: string, wordCount: number) => void;

  // Specialized modules
  private history: EditorHistory;
  private cursorManager: CursorManager;
  private content?: EditorContent;
  private config?: EditorConfig;
  private spellCheckIntegration?: SpellCheckIntegration;

  constructor(config: MonacoEditorConfig) {
    this.history = new EditorHistory("writer_editor_");
    this.cursorManager = new CursorManager("writer_editor_");

    // Try to use Monaco if requested and available
    if (config.useMonaco !== false && (window as any).monaco) {
      this.initializeMonaco(config);
    } else {
      this.initializeCodeMirror(config);
    }
  }

  /**
   * Initialize Monaco Editor
   */
  private initializeMonaco(config: MonacoEditorConfig): void {
    const element = document.getElementById(config.elementId);
    if (!element) {
      console.warn("[Editor] Element not found, falling back to CodeMirror");
      this.initializeCodeMirror(config);
      return;
    }

    // Wait for Monaco to be available
    const waitForMonaco = (): void => {
      if (!(window as any).monaco) {
        console.log("[Editor] Waiting for Monaco to load...");
        setTimeout(() => waitForMonaco(), 100);
        return;
      }

      try {
        const monaco = (window as any).monaco;

        // Register LaTeX language if not already registered
        console.log(
          "[Monaco] Available languages:",
          monaco.languages.getLanguages().map((l: any) => l.id),
        );

        registerLatexLanguage(monaco);
        registerLatexCompletionProvider(monaco);
        registerCitationCompletionProvider(monaco);
        registerCitationHoverProvider(monaco);

        // Define custom SciTeX dark theme
        defineScitexTheme(monaco);

        // Get initial value before replacing element
        const textareaElement = element as HTMLTextAreaElement;
        const initialValue = textareaElement.value || "";

        // Create editor container
        const editorContainer = document.createElement("div");
        editorContainer.id = `${config.elementId}-monaco`;
        editorContainer.style.cssText =
          "width: 100%; height: 100%; border: none;";
        element.parentElement?.replaceChild(editorContainer, element);

        // Create Monaco editor
        this.monacoEditor = createMonacoEditor(
          monaco,
          editorContainer,
          initialValue,
          config
        );

        this.editor = this.monacoEditor;
        this.editorType = "monaco";
        this.setupMonacoEditor();

        // Initialize spell checker
        injectSpellCheckStyles();
        this.spellChecker = new SpellChecker(monaco, this.monacoEditor, {
          enabled: true,
          language: 'en-US',
          skipLaTeXCommands: true,
          skipMathMode: true,
          skipCodeBlocks: true,
        });
        this.spellChecker.loadCustomDictionary();
        this.spellChecker.enable();
        console.log("[Editor] Spell checker initialized and enabled");

        // Initialize specialized modules
        this.content = new EditorContent(
          this.editor,
          this.monacoEditor,
          this.editorType,
          this.spellChecker,
          this.history
        );
        this.config = new EditorConfig(
          this.editor,
          this.monacoEditor,
          this.editorType
        );
        this.spellCheckIntegration = new SpellCheckIntegration(this.spellChecker);

        // Listen for global theme changes and update editor theme
        setupThemeObserver(monaco);

        console.log("[Editor] Monaco Editor initialized with LaTeX support");
      } catch (error) {
        console.warn(
          "[Editor] Monaco initialization failed, falling back to CodeMirror",
          error,
        );
        this.initializeCodeMirror(config);
      }
    };

    // Start waiting for Monaco
    waitForMonaco();
  }

  /**
   * Setup Monaco Editor event listeners
   */
  private setupMonacoEditor(): void {
    if (!this.monacoEditor) return;

    const monaco = (window as any).monaco;

    // Setup event listeners and actions
    // Pass a getter function for the callback so it can be set after initialization
    setupMonacoEditorListeners(
      this.monacoEditor,
      monaco,
      undefined, // Don't pass direct callback
      this.cursorManager.getCurrentSectionId(),
      (sectionId: string) => this.cursorManager.saveCursorPosition(this.monacoEditor, sectionId),
      () => this.onChangeCallback // Getter function for late binding
    );

    // Setup drag-and-drop for citation insertion
    setupCitationDropZone(this.monacoEditor);

    // Setup citation protection (atomic delete)
    setupCitationProtection(this.monacoEditor, monaco);

    // Setup suggestion widget observer
    setupSuggestionWidgetObserver(this.monacoEditor);

    console.log("[Editor] Monaco Editor listeners and actions configured");
  }

  /**
   * Initialize CodeMirror fallback
   */
  private initializeCodeMirror(config: MonacoEditorConfig): void {
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

      this.editorType = "codemirror";

      // Initialize specialized modules for CodeMirror
      this.content = new EditorContent(
        this.editor,
        this.monacoEditor,
        this.editorType,
        this.spellChecker,
        this.history
      );
      this.config = new EditorConfig(
        this.editor,
        this.monacoEditor,
        this.editorType
      );
      this.spellCheckIntegration = new SpellCheckIntegration(this.spellChecker);

      this.setupCodeMirrorEditor();
    } else {
      console.warn(
        "[Editor] Neither Monaco nor CodeMirror available. Editor will not be initialized.",
      );
    }
  }

  /**
   * Setup CodeMirror event listeners
   */
  private setupCodeMirrorEditor(): void {
    if (!this.editor || this.editorType !== "codemirror") return;

    // Track changes
    this.editor.on("change", (editor: any) => {
      const content = editor.getValue();
      const wordCount = this.history.countWords(content);

      if (this.onChangeCallback) {
        this.onChangeCallback(content, wordCount);
      }
    });

    console.log("[Editor] CodeMirror initialized");
  }

  // ========================================================================
  // PUBLIC API - Delegating to specialized modules
  // ========================================================================

  /**
   * Get editor content
   */
  getContent(): string {
    return this.content?.getContent() ?? "";
  }

  /**
   * Set editor content
   */
  setContent(content: string, emitChange: boolean = false): void {
    this.content?.setContent(content, emitChange);
  }

  /**
   * Append content to editor
   */
  appendContent(content: string): void {
    this.content?.appendContent(content);
  }

  /**
   * Clear editor content
   */
  clear(): void {
    this.content?.clear();
  }

  /**
   * Add entry to history
   */
  addToHistory(content: string, wordCount: number): void {
    this.history.addToHistory(content, wordCount);
  }

  /**
   * Undo last change
   */
  undo(): boolean {
    return this.history.undo(
      this.editorType === "monaco" ? this.monacoEditor : this.editor,
      this.editorType
    );
  }

  /**
   * Redo change
   */
  redo(): boolean {
    return this.history.redo(
      this.editorType === "monaco" ? this.monacoEditor : this.editor,
      this.editorType
    );
  }

  /**
   * Get word count of current content
   */
  getWordCount(): number {
    return this.content?.getWordCount() ?? 0;
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
    if (this.editorType === "monaco" && this.monacoEditor) {
      this.monacoEditor.focus();
    } else if (this.editor) {
      this.editor.focus();
    }
  }

  /**
   * Check if editor has unsaved changes
   */
  hasUnsavedChanges(lastSavedContent: string): boolean {
    return this.content?.hasUnsavedChanges(lastSavedContent) ?? false;
  }

  /**
   * Get editor instance (for advanced usage)
   */
  getInstance(): any {
    return this.editor;
  }

  /**
   * Get editor type
   */
  getEditorType(): string {
    return this.editorType;
  }

  /**
   * Set editor theme
   */
  setTheme(theme: string): void {
    this.config?.setTheme(theme);
  }

  /**
   * Set editor read-only state
   */
  setReadOnly(readOnly: boolean): void {
    this.config?.setReadOnly(readOnly);
  }

  /**
   * Set editor keybinding mode
   */
  setKeyBinding(mode: string): void {
    this.config?.setKeyBinding(mode);
  }

  /**
   * Set content with optional section ID for cursor position management
   */
  setContentForSection(sectionId: string, content: string): void {
    this.cursorManager.setContentForSection(
      this.monacoEditor,
      sectionId,
      content,
      (c: string) => this.setContent(c)
    );
  }

  /**
   * Enable spell checking
   */
  enableSpellCheck(): void {
    this.spellCheckIntegration?.enableSpellCheck();
  }

  /**
   * Disable spell checking
   */
  disableSpellCheck(): void {
    this.spellCheckIntegration?.disableSpellCheck();
  }

  /**
   * Re-check all content for spelling errors
   */
  recheckSpelling(): void {
    this.spellCheckIntegration?.recheckSpelling();
  }

  /**
   * Add word to custom dictionary
   */
  addToSpellCheckDictionary(word: string): void {
    this.spellCheckIntegration?.addToSpellCheckDictionary(word);
  }

  /**
   * Clear custom spell check dictionary
   */
  clearSpellCheckDictionary(): void {
    this.spellCheckIntegration?.clearSpellCheckDictionary();
  }

  /**
   * Toggle Monaco editor theme independently from global theme
   */
  toggleEditorTheme(): void {
    if (this.editorType !== "monaco" || !this.monacoEditor) {
      console.warn("[Editor] Cannot toggle theme - Monaco editor not active");
      return;
    }

    const monaco = (window as any).monaco;
    if (!monaco) {
      console.warn("[Editor] Cannot toggle theme - Monaco not available");
      return;
    }

    // Get current theme from editor
    const currentTheme = this.monacoEditor.getOption(monaco.editor.EditorOption.theme);
    // Toggle between scitex themes (with fallback for legacy vs-dark/vs)
    const isDark = currentTheme === "scitex-dark" || currentTheme === "vs-dark";
    const newTheme = isDark ? "scitex-light" : "scitex-dark";

    // Update editor theme
    this.monacoEditor.updateOptions({ theme: newTheme });

    // Store preference
    localStorage.setItem("monaco-editor-theme-writer", newTheme);

    // Update toggle button emoji
    this.updateThemeToggleButton(newTheme);

    console.log(`[Editor] Monaco theme toggled to: ${newTheme}`);
  }

  /**
   * Get current Monaco editor theme
   */
  getCurrentTheme(): string {
    const monaco = (window as any).monaco;
    if (this.editorType !== "monaco" || !this.monacoEditor || !monaco) {
      return "vs-dark";
    }
    return this.monacoEditor.getOption(monaco.editor.EditorOption.theme);
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
      toggleBtn?.setAttribute("title",
        isDark ? "Switch to light editor theme" : "Switch to dark editor theme"
      );
    }
  }
}
