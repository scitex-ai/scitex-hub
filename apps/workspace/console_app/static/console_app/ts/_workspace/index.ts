/**
 * Workspace Orchestrator
 * Main coordinator for the Code Workspace - wires all managers together
 */

import { MonacoManager } from "./editor/MonacoManager";
import { ScratchManager } from "./editor/ScratchManager";
import { PTYManager } from "./terminal/PTYManager";
import { RunManager } from "./terminal/RunManager";
import { FileTreeManager } from "./files/FileTreeManager";
import { FileOperations } from "./files/FileOperations";
import { FileTabManager } from "./files/FileTabManager";
import { FileStateManager } from "./files/FileStateManager";
import { FileCommandHandler } from "./files/FileCommandHandler";
import { GitStatusManager } from "./git/GitStatusManager";
import { GitOperations } from "./git/GitOperations";
import { CommitManager } from "./git/CommitManager";
import { UIComponents } from "./ui/UIComponents";
import { ModalManager } from "./ui/ModalManager";
import { ShortcutsManager } from "./ui/ShortcutsManager";
import { ToolbarManager } from "./ui/ToolbarManager";
import { VisitorManager } from "./auth/VisitorManager";
import { JobsPanelManager } from "./jobs/JobsPanelManager";
import type { EditorConfig, OpenFile } from "./core/types";

export class WorkspaceOrchestrator {
  private config: EditorConfig;

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
  private toolbarManager: ToolbarManager;

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
    this.commitManager = new CommitManager(
      config,
      this.gitOperations,
      this.gitStatusManager,
    );

    // Initialize specialized managers
    this.scratchManager = new ScratchManager(config, this.monacoManager);
    this.runManager = new RunManager(config);
    this.shortcutsManager = new ShortcutsManager(this.modalManager);
    this.jobsPanelManager = new JobsPanelManager();

    // Create shared openFiles map
    const openFilesMap = new Map<string, OpenFile>();

    // Initialize file managers with shared map
    this.fileTabManager = new FileTabManager(
      openFilesMap,
      () => {},
      () => {},
    );
    this.fileStateManager = new FileStateManager(
      this.monacoManager,
      this.fileOperations,
      this.fileTabManager,
      this.gitStatusManager,
      openFilesMap,
    );

    // Update FileTabManager callbacks
    this.fileTabManager.setCallbacks(
      this.fileStateManager.switchToFile.bind(this.fileStateManager),
      this.fileStateManager.closeTab.bind(this.fileStateManager),
    );

    // Set rename callback for file tabs
    this.fileTabManager.setRenameCallback(
      async (oldPath: string, newPath: string) => {
        await this.fileCommandHandler.renameFile(oldPath, newPath);
      },
    );

    // Set new file callback for + button (inline input workflow)
    this.fileTabManager.setNewFileCallback(async (fileName: string) => {
      await this.fileCommandHandler.createFileWithName(fileName);
    });

    this.fileTreeManager = new FileTreeManager(
      config,
      this.fileStateManager.handleFileClick.bind(this.fileStateManager),
    );

    this.uiComponents = new UIComponents(
      config,
      this.handleContextMenuAction.bind(this),
    );

    this.fileCommandHandler = new FileCommandHandler(
      this.fileOperations,
      this.fileTreeManager,
      this.fileStateManager,
      this.uiComponents,
      this.visitorManager,
    );

    // Toolbar manager handles all button clicks and keyboard shortcuts
    this.toolbarManager = new ToolbarManager(
      this.ptyManager,
      this.fileStateManager,
      this.fileTabManager,
      this.fileCommandHandler,
      this.monacoManager,
      this.commitManager,
      this.shortcutsManager,
      this.runCurrentFile.bind(this),
    );

    // Start initialization
    this.init().catch((err) => {
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
    this.toolbarManager.attachAll();
    this.setupFileSearch();
    this.uiComponents.initializeAll();
    this.listenForRunFileEvent();

    // Initialize project ID for tab persistence
    this.fileTabManager.initializeProjectId();

    // Parallel async initialization
    const startTime = performance.now();

    try {
      await Promise.all([
        this.fileTreeManager.loadFileTree().catch((err) => {
          console.error("[WorkspaceOrchestrator] File tree failed:", err);
        }),
        this.scratchManager.initialize(this.fileStateManager).catch((err) => {
          console.error("[WorkspaceOrchestrator] Scratch buffer failed:", err);
        }),
        this.ptyManager.initialize().catch((err) => {
          console.error("[WorkspaceOrchestrator] PTY failed:", err);
        }),
      ]);

      // Restore previously opened tabs from localStorage
      await this.restoreSavedTabs();

      const endTime = performance.now();
      console.log(
        `[WorkspaceOrchestrator] Initialized in ${Math.round(endTime - startTime)}ms`,
      );

      this.setupThemeListeners();
    } catch (err) {
      console.error("[WorkspaceOrchestrator] Critical error:", err);
    }
  }

  private async restoreSavedTabs(): Promise<void> {
    const savedState = this.fileTabManager.getSavedTabState();
    if (!savedState || savedState.openFiles.length === 0) {
      return;
    }

    console.log(
      "[WorkspaceOrchestrator] Restoring",
      savedState.openFiles.length,
      "tabs",
    );

    for (const filePath of savedState.openFiles) {
      try {
        await this.fileStateManager.loadFile(filePath);
      } catch (err) {
        console.warn(
          `[WorkspaceOrchestrator] Failed to restore tab: ${filePath}`,
          err,
        );
      }
    }

    if (
      savedState.currentFile &&
      this.fileStateManager.isFileOpen(savedState.currentFile)
    ) {
      await this.fileStateManager.switchToFile(savedState.currentFile);
    }
  }

  private setupThemeListeners(): void {
    document.addEventListener("theme-changed", (event: Event) => {
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

  /** Setup file search functionality */
  private setupFileSearch(): void {
    const searchInput = document.getElementById(
      "file-search-input",
    ) as HTMLInputElement;
    const clearBtn = document.getElementById(
      "file-search-clear",
    ) as HTMLButtonElement;

    if (!searchInput) return;

    let debounceTimer: number | null = null;
    searchInput.addEventListener("input", () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(() => {
        const query = searchInput.value;
        this.fileTreeManager.setSearchQuery(query);
      }, 150);
    });

    clearBtn?.addEventListener("click", () => {
      searchInput.value = "";
      this.fileTreeManager.clearSearch();
      searchInput.focus();
    });

    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        searchInput.value = "";
        this.fileTreeManager.clearSearch();
        searchInput.blur();
      }
      if (e.key === "Enter") {
        e.preventDefault();
        const treeContainer = document.getElementById("file-tree");
        if (treeContainer) {
          const firstItem = treeContainer.querySelector(
            ".wft-item",
          ) as HTMLElement;
          if (firstItem) {
            firstItem.click();
            searchInput.blur();
          }
        }
      }
    });
  }

  /** Listen for run-file events dispatched from the file tree context menu */
  private listenForRunFileEvent(): void {
    document.addEventListener("run-file", ((e: CustomEvent) => {
      const filePath = e.detail?.path;
      if (!filePath) return;
      const terminal = this.ptyManager.getTerminal();
      if (!terminal) {
        alert("Terminal not available. Please wait for it to initialize.");
        return;
      }
      this.runManager.runFile(filePath, terminal, async () => {});
    }) as EventListener);
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

    if (currentFile === "*scratch*") {
      const editor = this.monacoManager.getEditor();
      if (editor) {
        await this.runManager.runScratchBuffer(editor.getValue(), terminal);
      }
      return;
    }

    await this.runManager.runFile(currentFile, terminal, () =>
      this.fileStateManager.saveCurrentFile(),
    );
  }
}

// Note: Initialization is handled by workspace.ts
