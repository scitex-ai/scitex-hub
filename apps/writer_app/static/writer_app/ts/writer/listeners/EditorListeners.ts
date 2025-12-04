/**
 * Editor Listeners Module
 * Handles all editor-related event listeners including keyboard shortcuts,
 * change tracking, and button interactions
 */

import {
  WriterEditor,
  scheduleSave,
  scheduleAutoCompile,
  saveSections,
  showCommitModal,
  handleGitCommit,
  statusLamp,
} from "../../modules/index.js";
import {
  showToast,
  updateWordCountDisplay,
  hideCompilationProgress,
  minimizeCompilationOutput,
  restoreCompilationOutput,
  restoreCompilationStatus,
} from "../../utils/index.js";

export class EditorListeners {
  private editor: WriterEditor | null;
  private sectionsManager: any;
  private compilationManager: any;
  private state: any;
  private pdfPreviewManager: any;

  constructor(
    editor: WriterEditor | null,
    sectionsManager: any,
    compilationManager: any,
    state: any,
    pdfPreviewManager?: any,
  ) {
    this.editor = editor;
    this.sectionsManager = sectionsManager;
    this.compilationManager = compilationManager;
    this.state = state;
    this.pdfPreviewManager = pdfPreviewManager;
  }

  /**
   * Setup all editor event listeners
   */
  setupListeners(): void {
    if (!this.editor) return;

    this.setupChangeTracking();
    this.setupKeyboardShortcuts();
    this.setupToolbarButtons();
    this.setupCompilationButtons();
    this.initializeStatusLamps();
  }

  /**
   * Setup change tracking
   */
  private setupChangeTracking(): void {
    if (!this.editor) return;

    this.editor.onChange((content: string, wordCount: number) => {
      const currentSection = this.state.currentSection;

      // Skip tracking changes for compiled sections (read-only)
      const isCompiledSection =
        currentSection &&
        (currentSection.endsWith("/compiled_pdf") ||
          currentSection.endsWith("/compiled_tex"));

      if (isCompiledSection) {
        console.log(
          "[EditorListeners] Skipping change tracking for compiled section:",
          currentSection,
        );
        return;
      }

      this.sectionsManager.setContent(currentSection, content);
      this.state.unsavedSections.add(currentSection);

      // Update word count display
      updateWordCountDisplay(currentSection, wordCount);

      // Schedule auto-save
      scheduleSave(this.editor, this.sectionsManager, this.state);

      // Schedule auto-compile for live PDF preview (skip for compiled sections)
      const isCompiledForPreview =
        currentSection.endsWith("/compiled_pdf") ||
        currentSection.endsWith("/compiled_tex");
      if (this.pdfPreviewManager && !isCompiledForPreview) {
        scheduleAutoCompile(
          this.pdfPreviewManager,
          content,
          currentSection,
        );
      }
    });
  }

  /**
   * Setup keyboard shortcuts
   */
  private setupKeyboardShortcuts(): void {
    document.addEventListener("keydown", (e) => {
      // Ctrl/Cmd + S to save
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        saveSections(this.sectionsManager, this.state);
      }

      // Alt + Enter to compile preview (quick)
      if (e.altKey && !e.shiftKey && e.key === "Enter") {
        e.preventDefault();
        const handlePreviewClick = (window as any).handlePreviewClick;
        if (handlePreviewClick) {
          handlePreviewClick();
          console.log(
            "[EditorListeners] Preview compilation triggered via Alt+Enter",
          );
        }
      }

      // Alt + Shift + Enter to compile full manuscript
      if (e.altKey && e.shiftKey && e.key === "Enter") {
        e.preventDefault();
        // Import handleCompileFull dynamically to avoid circular dependency
        import("../../index.js").then(({ handleCompileFull }) => {
          handleCompileFull(this.compilationManager, this.state, "manuscript", true);
          console.log(
            "[EditorListeners] Full compilation triggered via Alt+Shift+Enter",
          );
        });
      }

      // Ctrl/Cmd + Shift + X to compile (legacy)
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "X") {
        e.preventDefault();
        this.handleCompile();
      }

      // Ctrl+K to focus citation search (only when citations pane visible)
      if (e.ctrlKey && e.key === "k") {
        const citationsView = document.getElementById("citations-view");
        const searchInput = document.getElementById(
          "citations-search-toolbar",
        ) as HTMLInputElement;

        if (
          citationsView &&
          citationsView.style.display !== "none" &&
          searchInput
        ) {
          e.preventDefault();
          searchInput.focus();
          searchInput.select();
          console.log(
            "[EditorListeners] Citation search focused via Ctrl+K",
          );
        }
      }

      // Escape to unfocus citation search
      if (e.key === "Escape") {
        const searchInput = document.getElementById(
          "citations-search-toolbar",
        ) as HTMLInputElement;
        if (searchInput && document.activeElement === searchInput) {
          e.preventDefault();
          searchInput.blur();
          console.log(
            "[EditorListeners] Citation search unfocused via Escape",
          );
        }
      }
    });
  }

  /**
   * Setup toolbar buttons (undo/redo)
   */
  private setupToolbarButtons(): void {
    const undoBtn = document.getElementById("undo-btn");
    if (undoBtn && this.editor) {
      undoBtn.addEventListener("click", () => {
        this.editor!.undo();
      });
    }

    const redoBtn = document.getElementById("redo-btn");
    if (redoBtn && this.editor) {
      redoBtn.addEventListener("click", () => {
        this.editor!.redo();
      });
    }

    // Monaco theme toggle button
    const monacoThemeToggle = document.getElementById("monaco-theme-toggle");
    if (monacoThemeToggle && this.editor) {
      monacoThemeToggle.addEventListener("click", () => {
        if (typeof this.editor!.toggleEditorTheme === "function") {
          this.editor!.toggleEditorTheme();
        } else {
          console.warn("[EditorListeners] toggleEditorTheme method not available on editor");
        }
      });
    }
  }

  /**
   * Setup compilation-related buttons
   */
  private setupCompilationButtons(): void {
    // Setup compile button (full manuscript compilation)
    const compileBtn = document.getElementById("compile-btn-toolbar");
    if (compileBtn) {
      compileBtn.addEventListener("click", () => {
        import("../../index.js").then(({ handleCompileFull }) => {
          handleCompileFull(this.compilationManager, this.state);
        });
      });
    }

    // Setup git commit button
    const commitBtn = document.getElementById("git-commit-btn");
    if (commitBtn) {
      commitBtn.addEventListener("click", () => {
        showCommitModal(this.state);
      });
    }

    // Setup confirm commit button (in modal)
    const confirmCommitBtn = document.getElementById("confirm-commit-btn");
    if (confirmCommitBtn) {
      confirmCommitBtn.addEventListener("click", async () => {
        await handleGitCommit(this.state);
      });
    }

    // Setup minimize compilation output button
    const minimizeBtn = document.getElementById("minimize-compilation-output");
    if (minimizeBtn) {
      minimizeBtn.addEventListener("click", () => {
        minimizeCompilationOutput();
      });
    }

    // Setup close compilation output button
    const closeBtn = document.getElementById("close-compilation-output");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => {
        hideCompilationProgress();
        // Also hide minimized status
        const minimizedStatus = document.getElementById(
          "minimized-compilation-status",
        );
        if (minimizedStatus) {
          minimizedStatus.style.display = "none";
        }
      });
    }

    // Setup minimized compilation status button (click to restore)
    const minimizedStatus = document.getElementById(
      "minimized-compilation-status",
    );
    if (minimizedStatus) {
      minimizedStatus.addEventListener("click", () => {
        restoreCompilationOutput();
      });
    }
  }

  /**
   * Initialize status lamps with default state
   */
  private initializeStatusLamps(): void {
    // Preview lamp: idle by default
    statusLamp.setPreviewStatus("idle");
    // Full compile lamp: idle by default
    statusLamp.setFullCompileStatus("idle");

    // Restore last compilation status from localStorage
    restoreCompilationStatus();
  }

  /**
   * @deprecated Use handleCompileFull instead
   * Handle preview compilation (legacy)
   */
  private async handleCompile(): Promise<void> {
    if (!this.pdfPreviewManager) {
      showToast("PDF preview not initialized", "error");
      return;
    }

    if (this.pdfPreviewManager.isCompiling()) {
      showToast("Compilation already in progress", "warning");
      return;
    }

    try {
      const sections = this.sectionsManager.getAll();
      const sectionArray = Object.entries(sections).map(([name, content]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        content: content as unknown as string,
      }));

      showToast("Starting preview compilation...", "info");
      await this.pdfPreviewManager.compile(sectionArray);
    } catch (error) {
      showToast(
        "Compilation error: " +
          (error instanceof Error ? error.message : "Unknown error"),
        "error",
      );
    }
  }
}
