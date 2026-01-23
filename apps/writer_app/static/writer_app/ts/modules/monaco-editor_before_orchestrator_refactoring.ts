/**
 * Monaco Editor Module
 * Enhanced editor with Monaco Editor capabilities
 * Falls back to CodeMirror if Monaco is not available
 */

import { SpellChecker, injectSpellCheckStyles } from "./spell-checker";
import {
  registerLatexLanguage,
  registerLatexCompletionProvider,
  registerCitationCompletionProvider,
  registerCitationHoverProvider,
  defineScitexTheme,
  createMonacoEditor,
  setupThemeObserver,
} from "./monaco-editor/monaco-init";
import {
  setupMonacoEditorListeners,
  setupCitationDropZone,
  setupCitationProtection,
  setupSuggestionWidgetObserver,
} from "./monaco-editor/monaco-features";
import { EditorHistory } from "./monaco-editor/editor-history";
import { CursorManager } from "./monaco-editor/cursor-manager";

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
  private editor: any; // Monaco or CodeMirror instance
  private editorType: "monaco" | "codemirror" = "codemirror";
  private onChangeCallback?: (content: string, wordCount: number) => void;
  private monacoEditor?: any;
  private spellChecker?: SpellChecker;
  private history: EditorHistory;
  private cursorManager: CursorManager;

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
    setupMonacoEditorListeners(
      this.monacoEditor,
      monaco,
      this.onChangeCallback,
      this.cursorManager.getCurrentSectionId(),
      (sectionId: string) => this.cursorManager.saveCursorPosition(this.monacoEditor, sectionId)
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
    return this.history.countWords(this.getContent());
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
    return this.getContent() !== lastSavedContent;
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
    if (this.editorType === "monaco" && this.monacoEditor) {
      console.log("[Editor] Setting Monaco theme to:", theme);
      // Map common CodeMirror theme names to Monaco themes
      const monacoThemeMap: Record<string, string> = {
        zenburn: "vs-dark",
        monokai: "vs-dark",
        dracula: "vs-dark",
        eclipse: "vs",
        neat: "vs",
        "solarized light": "vs",
        "scitex-dark": "scitex-dark",
        default: "vs",
      };
      const monacoTheme = monacoThemeMap[theme.toLowerCase()] || "scitex-dark";
      (window as any).monaco.editor.setTheme(monacoTheme);
    } else {
      // CodeMirror theme change
      console.log("[Editor] Setting CodeMirror theme to:", theme);
      const cmEditor = (document.querySelector(".CodeMirror") as any)
        ?.CodeMirror;
      if (cmEditor) {
        cmEditor.setOption("theme", theme);
      }
    }
  }

  /**
   * Set editor read-only state
   */
  setReadOnly(readOnly: boolean): void {
    if (this.editorType === "monaco" && this.monacoEditor) {
      console.log("[Editor] Setting Monaco readOnly to:", readOnly);
      this.monacoEditor.updateOptions({ readOnly: readOnly });
    } else {
      // CodeMirror read-only mode
      console.log("[Editor] Setting CodeMirror readOnly to:", readOnly);
      const cmEditor = (document.querySelector(".CodeMirror") as any)
        ?.CodeMirror;
      if (cmEditor) {
        cmEditor.setOption("readOnly", readOnly);
      }
    }
  }

  /**
   * Set editor keybinding mode
   */
  setKeyBinding(mode: string): void {
    if (this.editorType === "monaco" && this.monacoEditor) {
      console.log("[Editor] Monaco keybinding change requested:", mode);
      // Monaco doesn't directly support Vim/Emacs keybindings without extensions
      // For now, just log - would need monaco-vim or monaco-emacs packages
      console.warn(
        "[Editor] Monaco Vim/Emacs keybindings require additional packages",
      );
    } else {
      // CodeMirror keymap
      console.log("[Editor] Setting CodeMirror keymap to:", mode);
      const cmEditor = (document.querySelector(".CodeMirror") as any)
        ?.CodeMirror;
      if (cmEditor) {
        cmEditor.setOption("keyMap", mode);
      }
    }
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
    if (this.spellChecker) {
      this.spellChecker.enable();
      console.log("[Editor] Spell check enabled");
    }
  }

  /**
   * Disable spell checking
   */
  disableSpellCheck(): void {
    if (this.spellChecker) {
      this.spellChecker.disable();
      console.log("[Editor] Spell check disabled");
    }
  }

  /**
   * Re-check all content for spelling errors
   */
  recheckSpelling(): void {
    if (this.spellChecker) {
      this.spellChecker.recheckAll();
      console.log("[Editor] Re-checking all content");
    }
  }

  /**
   * Add word to custom dictionary
   */
  addToSpellCheckDictionary(word: string): void {
    if (this.spellChecker) {
      this.spellChecker.addToCustomDictionary(word);
    }
  }

  /**
   * Clear custom spell check dictionary
   */
  clearSpellCheckDictionary(): void {
    if (this.spellChecker) {
      this.spellChecker.clearCustomDictionary();
    }
  }
}
