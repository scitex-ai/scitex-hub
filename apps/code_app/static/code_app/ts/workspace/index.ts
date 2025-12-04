/**
 * Workspace Orchestrator
 * Main coordinator for the Code Workspace - wires all managers together
 */

import { MonacoManager } from "./editor/MonacoManager.ts";
import { ScratchManager } from "./editor/ScratchManager.ts";
import { PTYManager } from "./terminal/PTYManager.ts";
import { RunManager } from "./terminal/RunManager.ts";
import { FileTreeManager } from "./files/FileTreeManager.ts";
import { FileOperations } from "./files/FileOperations.ts";
import { FileTabManager } from "./files/FileTabManager.ts";
import { FileStateManager } from "./files/FileStateManager.ts";
import { FileCommandHandler } from "./files/FileCommandHandler.ts";
import { GitStatusManager } from "./git/GitStatusManager.ts";
import { GitOperations } from "./git/GitOperations.ts";
import { CommitManager } from "./git/CommitManager.ts";
import { UIComponents } from "./ui/UIComponents.ts";
import { ModalManager } from "./ui/ModalManager.ts";
import { ShortcutsManager } from "./ui/ShortcutsManager.ts";
import { VisitorManager } from "./auth/VisitorManager.ts";
import { JobsPanelManager } from "./jobs/JobsPanelManager.ts";
import type { EditorConfig, OpenFile } from "./core/types.ts";

export class WorkspaceOrchestrator {
  private config: EditorConfig;

  // Emacs chord state for C-x prefix
  private emacsChordState: { ctrlXPressed: boolean; timeout: number | null } = {
    ctrlXPressed: false,
    timeout: null,
  };

  // Core Managers
  private monacoManager: MonacoManager;
  private ptyManager: PTYManager;
  private fileTreeManager: FileTreeManager;
  private fileOperations: FileOperations;
  private fileTabManager: FileTabManager;
  private fileStateManager: FileStateManager;
  private fileCommandHandler: FileCommandHandler;

  // Git Managers
  private gitStatusManager: GitStatusManager;
  private gitOperations: GitOperations;
  private commitManager: CommitManager;

  // UI Managers
  private uiComponents: UIComponents;
  private modalManager: ModalManager;
  private shortcutsManager: ShortcutsManager;

  // Specialized Managers
  private visitorManager: VisitorManager;
  private scratchManager: ScratchManager;
  private runManager: RunManager;
  private jobsPanelManager: JobsPanelManager;

  constructor(config: EditorConfig) {
    this.config = config;

    // Initialize core managers
    this.monacoManager = new MonacoManager(config);
    this.ptyManager = new PTYManager(config);
    this.fileOperations = new FileOperations(config);
    this.modalManager = new ModalManager();
    this.visitorManager = new VisitorManager(config);

    // Initialize git managers
    this.gitStatusManager = new GitStatusManager(config);
    this.gitOperations = new GitOperations(config);
    this.commitManager = new CommitManager(config, this.gitOperations, this.gitStatusManager);

    // Initialize specialized managers
    this.scratchManager = new ScratchManager(config, this.monacoManager);
    this.runManager = new RunManager(config);
    this.shortcutsManager = new ShortcutsManager(this.modalManager);
    this.jobsPanelManager = new JobsPanelManager();

    // Create shared openFiles map
    const openFilesMap = new Map<string, OpenFile>();

    // Initialize file managers with shared map
    this.fileTabManager = new FileTabManager(openFilesMap, () => {}, () => {});
    this.fileStateManager = new FileStateManager(
      this.monacoManager,
      this.fileOperations,
      this.fileTabManager,
      this.gitStatusManager,
      openFilesMap
    );

    // Update FileTabManager callbacks
    this.fileTabManager.setCallbacks(
      this.fileStateManager.switchToFile.bind(this.fileStateManager),
      this.fileStateManager.closeTab.bind(this.fileStateManager)
    );

    // Set rename callback for file tabs
    this.fileTabManager.setRenameCallback(async (oldPath: string, newPath: string) => {
      await this.fileCommandHandler.renameFile(oldPath, newPath);
    });

    // Set new file callback for + button (inline input workflow)
    this.fileTabManager.setNewFileCallback(async (fileName: string) => {
      await this.fileCommandHandler.createFileWithName(fileName);
    });

    this.fileTreeManager = new FileTreeManager(
      config,
      this.fileStateManager.handleFileClick.bind(this.fileStateManager)
    );

    this.uiComponents = new UIComponents(config, this.handleContextMenuAction.bind(this));

    this.fileCommandHandler = new FileCommandHandler(
      this.fileOperations,
      this.fileTreeManager,
      this.fileStateManager,
      this.uiComponents,
      this.visitorManager
    );

    // Start initialization
    this.init().catch(err => {
      console.error("[WorkspaceOrchestrator] Initialization failed:", err);
    });
  }

  private async init(): Promise<void> {
    console.log("[WorkspaceOrchestrator] Initializing...");

    if (!this.config.currentProject) {
      this.uiComponents.showNoProjectMessage();
      return;
    }

    // Synchronous DOM setup
    this.attachEventListeners();
    this.setupFileSearch();
    this.uiComponents.initializeAll();

    // Parallel async initialization
    const startTime = performance.now();

    try {
      await Promise.all([
        this.fileTreeManager.loadFileTree().catch(err => {
          console.error("[WorkspaceOrchestrator] File tree failed:", err);
        }),
        this.scratchManager.initialize(this.fileStateManager).catch(err => {
          console.error("[WorkspaceOrchestrator] Scratch buffer failed:", err);
        }),
        this.ptyManager.initialize().catch(err => {
          console.error("[WorkspaceOrchestrator] PTY failed:", err);
        }),
      ]);

      const endTime = performance.now();
      console.log(`[WorkspaceOrchestrator] Initialized in ${Math.round(endTime - startTime)}ms`);

      this.setupThemeListeners();
    } catch (err) {
      console.error("[WorkspaceOrchestrator] Critical error:", err);
    }
  }

  private setupThemeListeners(): void {
    document.addEventListener('theme-changed', (event: Event) => {
      const customEvent = event as CustomEvent<{ theme: string }>;
      const theme = customEvent.detail.theme;

      if (this.monacoManager) this.monacoManager.updateTheme(theme);
      if (this.ptyManager) this.ptyManager.updateTheme();
    });
  }

  private handleContextMenuAction(action: string, target: string | null): void {
    this.fileCommandHandler.handleContextMenuAction(action, target);
  }

  public async createFileInFolder(folderPath: string): Promise<void> {
    await this.fileCommandHandler.createFileInFolder(folderPath);
  }

  public async createFolderInFolder(parentPath: string): Promise<void> {
    await this.fileCommandHandler.createFolderInFolder(parentPath);
  }

  private attachEventListeners(): void {
    // Save button
    document.getElementById("btn-save")?.addEventListener("click", () => {
      this.fileStateManager.saveCurrentFile();
    });

    // New file button (handled by FileTabManager's updateTabs method)
    // The + button click is already handled in FileTabManager

    // Delete button
    document.getElementById("btn-delete")?.addEventListener("click", () => {
      const currentFile = this.fileStateManager.getCurrentFile();
      if (currentFile && currentFile !== "*scratch*") {
        this.fileCommandHandler.deleteFile(currentFile);
      }
    });

    // Commit button
    document.getElementById("btn-commit")?.addEventListener("click", () => {
      this.commitManager.showCommitModal();
    });

    // Run button
    document.getElementById("btn-run")?.addEventListener("click", () => {
      this.runCurrentFile();
    });

    // Keybinding mode selector
    const keybindingMode = document.getElementById("keybinding-mode") as HTMLSelectElement;
    keybindingMode?.addEventListener("change", (e) => {
      this.monacoManager.setKeybindingMode((e.target as HTMLSelectElement).value);
    });

    // Monaco theme toggle
    document.getElementById("monaco-theme-toggle")?.addEventListener("click", () => {
      this.monacoManager.toggleEditorTheme();
    });

    // Shortcuts buttons
    document.getElementById("btn-editor-shortcuts")?.addEventListener("click", () => {
      this.shortcutsManager.showEditorShortcuts();
    });

    document.getElementById("btn-terminal-shortcuts")?.addEventListener("click", () => {
      this.shortcutsManager.showTerminalShortcuts();
    });

    // Keyboard shortcuts
    this.attachKeyboardShortcuts();

    console.log("[WorkspaceOrchestrator] Event listeners attached");
  }

  private attachKeyboardShortcuts(): void {
    // Use capture phase (true) for Emacs chords to intercept BEFORE Monaco handles them
    document.addEventListener("keydown", (e) => {
      const keybindingMode = (document.getElementById("keybinding-mode") as HTMLSelectElement)?.value || "emacs";
      const isEmacs = keybindingMode === "emacs";

      // Handle Emacs C-x prefix chord
      if (isEmacs && e.ctrlKey && e.key === "x" && !e.shiftKey && !e.altKey) {
        e.preventDefault();
        e.stopPropagation(); // Prevent Monaco from seeing this
        this.startEmacsChord();
        console.log("[Emacs] C-x prefix started");
        return;
      }

      // Handle Emacs C-x C-f (new file) and C-x C-s (save)
      // MUST run in capture phase to intercept before Monaco's C-f handler
      if (isEmacs && this.emacsChordState.ctrlXPressed && e.ctrlKey) {
        if (e.key === "f") {
          e.preventDefault();
          e.stopPropagation(); // Prevent Monaco from handling C-f as cursor movement
          this.clearEmacsChord();
          console.log("[Emacs] C-x C-f triggered - showing inline new file input");
          this.fileTabManager.triggerNewFileInput();
          return;
        }
        if (e.key === "s") {
          e.preventDefault();
          e.stopPropagation(); // Prevent Monaco from handling C-s
          this.clearEmacsChord();
          console.log("[Emacs] C-x C-s triggered - saving file");
          this.fileStateManager.saveCurrentFile();
          return;
        }
        // Any other key after C-x clears the chord
        this.clearEmacsChord();
      }

      // Ctrl+S: Save (all modes)
      if (e.ctrlKey && e.key === "s") {
        e.preventDefault();
        this.fileStateManager.saveCurrentFile();
      }

      // Ctrl+N: New file (non-Emacs modes, as Emacs uses C-n for cursor down)
      if (!isEmacs && e.ctrlKey && e.key === "n") {
        e.preventDefault();
        this.fileTabManager.triggerNewFileInput();
      }

      // Ctrl+Tab: Next file tab
      if (e.ctrlKey && e.key === "Tab" && !e.shiftKey) {
        e.preventDefault();
        this.fileTabManager.switchToNextTab();
      }

      // Ctrl+Shift+T: New terminal tab
      if (e.ctrlKey && e.shiftKey && e.key === "T") {
        e.preventDefault();
        this.ptyManager.createNewTerminal();
      }

      // Ctrl+PageDown/PageUp: Terminal tabs
      if (e.ctrlKey && e.key === "PageDown") {
        e.preventDefault();
        this.ptyManager.switchToNextTab();
      }
      if (e.ctrlKey && e.key === "PageUp") {
        e.preventDefault();
        this.ptyManager.switchToPrevTab();
      }

      // Ctrl+K: Focus file search input
      if (e.ctrlKey && e.key === "k") {
        e.preventDefault();
        this.focusFileSearch();
      }
    }, true); // Capture phase to intercept before Monaco
  }

  /** Focus the file search input */
  private focusFileSearch(): void {
    const searchInput = document.getElementById("file-search-input") as HTMLInputElement;
    if (searchInput) {
      searchInput.focus();
      searchInput.select();
    }
  }

  /** Setup file search functionality */
  private setupFileSearch(): void {
    const searchInput = document.getElementById("file-search-input") as HTMLInputElement;
    const clearBtn = document.getElementById("file-search-clear") as HTMLButtonElement;

    if (!searchInput) return;

    // Debounce search input
    let debounceTimer: number | null = null;
    searchInput.addEventListener("input", () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(() => {
        const query = searchInput.value;
        this.fileTreeManager.setSearchQuery(query);
      }, 150);
    });

    // Clear button
    clearBtn?.addEventListener("click", () => {
      searchInput.value = "";
      this.fileTreeManager.clearSearch();
      searchInput.focus();
    });

    // Escape to clear and blur
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        searchInput.value = "";
        this.fileTreeManager.clearSearch();
        searchInput.blur();
      }
      // Enter to select first match (if any)
      if (e.key === "Enter") {
        e.preventDefault();
        // Focus tree for keyboard navigation
        const treeContainer = document.getElementById("file-tree");
        if (treeContainer) {
          const firstItem = treeContainer.querySelector(".wft-item") as HTMLElement;
          if (firstItem) {
            firstItem.click();
            searchInput.blur();
          }
        }
      }
    });
  }

  private startEmacsChord(): void {
    this.emacsChordState.ctrlXPressed = true;
    // Clear any existing timeout
    if (this.emacsChordState.timeout) {
      window.clearTimeout(this.emacsChordState.timeout);
    }
    // Set timeout to clear chord state after 2 seconds
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

  private async runCurrentFile(): Promise<void> {
    const currentFile = this.fileStateManager.getCurrentFile();
    const terminal = this.ptyManager.getTerminal();

    if (!terminal) {
      alert("Terminal not available. Please wait for it to initialize.");
      return;
    }

    if (!currentFile) {
      console.warn("[WorkspaceOrchestrator] No file to run");
      return;
    }

    // Handle scratch buffer
    if (currentFile === "*scratch*") {
      const editor = this.monacoManager.getEditor();
      if (editor) {
        await this.runManager.runScratchBuffer(editor.getValue(), terminal);
      }
      return;
    }

    // Run regular file
    await this.runManager.runFile(
      currentFile,
      terminal,
      () => this.fileStateManager.saveCurrentFile()
    );
  }
}

// Note: Initialization is handled by workspace.ts
