/**
 * File Tree Setup Module (Refactored)
 * Handles file tree and section dropdown initialization
 *
 * Refactored to use handler modules for better maintainability:
 * - FileSelectHandler: Handles file/section selection
 * - DoctypeChangeHandler: Handles doctype dropdown changes
 * - TreeConfiguration: Writer-specific tree config
 * - WriterTreeSync: Bidirectional sync between dropdowns and tree
 */

// Direct imports to avoid circular dependency through barrel re-export
import {
  populateSectionDropdownDirect,
  syncDropdownsFromPath,
} from "../../utils/_section-dropdown/index";
import { initializeWriterFilter } from "../../modules/_writer-file-filter";
import { PanelSwitcher } from "../ui/PanelSwitcher";
import {
  createFileSelectHandler,
  setupDoctypeChangeWithTree,
  setupDoctypeChangeWithoutTree,
  createWriterTreeConfig,
} from "./_handlers/index";
import { initWriterTreeSync, getWriterTreeSync } from "../sync/index";

// Type for WorkspaceFilesTree (loaded dynamically)
interface WorkspaceFilesTreeType {
  new (config: any): any;
}

export class FileTreeSetup {
  private config: any;
  private editor: any;
  private sectionsManager: any;
  private compilationManager: any;
  private state: any;
  private pdfPreviewManager: any;
  private statePersistence: any;
  private panelSwitcher: PanelSwitcher;

  constructor(
    config: any,
    editor: any,
    sectionsManager: any,
    compilationManager: any,
    state: any,
    pdfPreviewManager: any,
    statePersistence: any,
  ) {
    this.config = config;
    this.editor = editor;
    this.sectionsManager = sectionsManager;
    this.compilationManager = compilationManager;
    this.state = state;
    this.pdfPreviewManager = pdfPreviewManager;
    this.statePersistence = statePersistence;
    this.panelSwitcher = new PanelSwitcher();
  }

  /**
   * Initialize file tree or section dropdown
   */
  setup(): void {
    // Create shared file selection handler using the handler module
    const onFileSelectHandler = createFileSelectHandler({
      config: this.config,
      editor: this.editor,
      sectionsManager: this.sectionsManager,
      state: this.state,
      pdfPreviewManager: this.pdfPreviewManager,
    });

    // Register enhanced handler as the global file select handler BEFORE tree init.
    // This ensures that when the shared worktree pane initializes (or is already initialized),
    // it uses the writer's enhanced handler rather than the default open-in-new-tab behavior.
    window.scitexOnFileSelect = (path: string, item: any): void => {
      this.handleFileSelectForWriter(path, item, onFileSelectHandler);
    };

    // Initialize file tree (including demo mode with projectId 0)
    if (this.config.projectId !== null && this.config.projectId !== undefined) {
      // If the shared worktree pane already initialized window.workspaceFilesTree, attach to it.
      if ((window as any).workspaceFilesTree) {
        console.log(
          "[FileTreeSetup] Shared workspaceFilesTree found, attaching writer handler",
        );
        this.attachToSharedTree(
          (window as any).workspaceFilesTree,
          onFileSelectHandler,
        ).catch((error) => {
          console.error(
            "[FileTreeSetup] Failed to attach to shared tree:",
            error,
          );
        });
        return;
      }

      const fileTreeContainer = document.getElementById("writer-file-tree");
      if (fileTreeContainer) {
        this.setupWithFileTree(fileTreeContainer, onFileSelectHandler).catch(
          (error) => {
            console.error("[FileTreeSetup] Failed to setup file tree:", error);
          },
        );
      } else {
        this.setupWithoutFileTree(onFileSelectHandler);
      }
    } else {
      // No projectId - still need to populate dropdown
      console.log(
        "[FileTreeSetup] No project, populating dropdown for demo mode",
      );
      populateSectionDropdownDirect(
        "manuscript",
        onFileSelectHandler,
        this.compilationManager,
        this.state,
      );
    }
  }

  /**
   * Handle file selection with writer-specific logic (tex sync, section filter, panel switch).
   * Extracted so it can be shared between shared-tree and own-tree paths.
   */
  private handleFileSelectForWriter(
    path: string,
    item: any,
    onFileSelectHandler: (sectionId: string, sectionName: string) => void,
  ): void {
    const fileName = path.split("/").pop() || "";
    console.log("[FileTreeSetup] File selected from tree:", path, fileName);

    // Only process .tex and .bib files in the Writer editor.
    // All other formats (PDF, images, etc.) are handled by the shared
    // workspace viewer via its document-level file-select listener.
    if (!path.endsWith(".tex") && !path.endsWith(".bib")) {
      return;
    }

    if (path.endsWith(".tex")) {
      const treeSync = getWriterTreeSync();
      if (treeSync) {
        treeSync.syncDropdownsFromTree(path);
      } else {
        syncDropdownsFromPath(path);
      }

      const writerFilter = (window as any).__writerFilter;
      if (writerFilter) {
        const section = writerFilter.extractSectionFromPath(path);
        if (section) {
          writerFilter.setSection(section);
          const currentDoctype = writerFilter.getState().doctype;
          this.panelSwitcher.autoSwitchForSection(section, currentDoctype);
        }
      }
    }

    onFileSelectHandler(path, fileName);
  }

  /**
   * Attach writer-specific logic to an already-initialized shared WorkspaceFilesTree.
   * Called when three-column layout has already set window.workspaceFilesTree.
   */
  private async attachToSharedTree(
    sharedTree: any,
    onFileSelectHandler: (sectionId: string, sectionName: string) => void,
  ): Promise<void> {
    // Restore saved doctype
    const savedDoctype = this.statePersistence.getSavedDoctype();
    const docTypeSelector = document.getElementById(
      "doctype-selector",
    ) as HTMLSelectElement;
    if (docTypeSelector && savedDoctype) {
      docTypeSelector.value = savedDoctype;
    }

    const currentDoctype = savedDoctype || "manuscript";
    const { initializeWriterFilter } =
      await import("../../modules/_writer-file-filter");
    const writerFilter = initializeWriterFilter(currentDoctype, null);
    // Store on window so handleFileSelectForWriter can access it
    (window as any).__writerFilter = writerFilter;

    // Attach handler to shared tree
    if (typeof sharedTree.setOnFileSelect === "function") {
      sharedTree.setOnFileSelect((path: string, item: any) => {
        this.handleFileSelectForWriter(path, item, onFileSelectHandler);
      });
    }

    // Setup refresh button if present
    this.setupRefreshButton(sharedTree);

    // Setup doctype change handler
    if (docTypeSelector) {
      const { setupDoctypeChangeWithTree } = await import("./_handlers/index");
      setupDoctypeChangeWithTree(docTypeSelector, sharedTree, writerFilter, {
        editor: this.editor,
        sectionsManager: this.sectionsManager,
        state: this.state,
        pdfPreviewManager: this.pdfPreviewManager,
        statePersistence: this.statePersistence,
      });
    }

    // Populate section dropdown
    await populateSectionDropdownDirect(
      currentDoctype,
      onFileSelectHandler,
      this.compilationManager,
      this.state,
    );

    console.log("[FileTreeSetup] Attached writer handler to shared tree");
  }

  /**
   * Setup with file tree container using shared WorkspaceFilesTree component
   */
  private async setupWithFileTree(
    fileTreeContainer: HTMLElement,
    onFileSelectHandler: (sectionId: string, sectionName: string) => void,
  ): Promise<void> {
    // Restore saved doctype
    const savedDoctype = this.statePersistence.getSavedDoctype();
    const docTypeSelector = document.getElementById(
      "doctype-selector",
    ) as HTMLSelectElement;
    if (docTypeSelector && savedDoctype) {
      docTypeSelector.value = savedDoctype;
      console.log("[FileTreeSetup] Restored saved doctype:", savedDoctype);
    }

    // Initialize writer filter with current doctype
    const currentDoctype = savedDoctype || "manuscript";
    const writerFilter = initializeWriterFilter(currentDoctype, null);
    // Store on window so handleFileSelectForWriter can access it
    (window as any).__writerFilter = writerFilter;
    console.log(
      "[FileTreeSetup] Initialized writer filter with doctype:",
      currentDoctype,
    );

    // Get project owner and slug from config
    const projectOwner =
      this.config.projectOwner ||
      this.config.visitorUsername ||
      this.config.username;
    const projectSlug = this.config.projectSlug;

    if (!projectOwner || !projectSlug) {
      console.warn(
        "[FileTreeSetup] Missing project owner or slug, skipping file tree",
      );
      return;
    }

    // Enhanced file select handler that updates section filter and switches panel
    const enhancedFileSelectHandler = (path: string, item: any): void => {
      const fileName = path.split("/").pop() || "";
      console.log("[FileTreeSetup] File selected from tree:", path, fileName);

      // If it's a .tex file, sync dropdowns and update filter
      if (path.endsWith(".tex")) {
        // Use WriterTreeSync for bidirectional sync if available
        const treeSync = getWriterTreeSync();
        if (treeSync) {
          treeSync.syncDropdownsFromTree(path);
        } else {
          // Fallback to legacy sync
          syncDropdownsFromPath(path);
        }

        const section = writerFilter.extractSectionFromPath(path);
        if (section) {
          console.log(
            "[FileTreeSetup] Extracted section from file path:",
            section,
          );
          writerFilter.setSection(section);

          const currentDoctype = writerFilter.getState().doctype;
          this.panelSwitcher.autoSwitchForSection(section, currentDoctype);
        }
      }

      onFileSelectHandler(path, fileName);
    };

    try {
      // Check if WorkspaceFilesTree is already initialized by inline script
      const existingTree = (window as any).writerFileTree;
      if (existingTree) {
        console.log(
          "[FileTreeSetup] WorkspaceFilesTree already initialized, skipping duplicate",
        );
        this.setupExistingTree(
          existingTree,
          writerFilter,
          docTypeSelector,
          currentDoctype,
          onFileSelectHandler,
        );
        return;
      }

      // Dynamically import and create tree
      const filesTree = await this.createNewTree(
        projectOwner,
        projectSlug,
        enhancedFileSelectHandler,
      );

      // Tree is shared across modules - do not auto-navigate on init

      console.log(
        "[FileTreeSetup] WorkspaceFilesTree initialized successfully",
      );

      // Populate section dropdown
      await populateSectionDropdownDirect(
        currentDoctype,
        onFileSelectHandler,
        this.compilationManager,
        this.state,
      );

      // Setup refresh button
      this.setupRefreshButton(filesTree);

      // Setup doctype change handler
      if (docTypeSelector) {
        setupDoctypeChangeWithTree(docTypeSelector, filesTree, writerFilter, {
          editor: this.editor,
          sectionsManager: this.sectionsManager,
          state: this.state,
          pdfPreviewManager: this.pdfPreviewManager,
          statePersistence: this.statePersistence,
        });
      }
    } catch (error) {
      console.error(
        "[FileTreeSetup] Failed to initialize WorkspaceFilesTree:",
        error,
      );
    }
  }

  /**
   * Setup an existing tree instance
   */
  private async setupExistingTree(
    filesTree: any,
    writerFilter: any,
    docTypeSelector: HTMLSelectElement | null,
    currentDoctype: string,
    onFileSelectHandler: (sectionId: string, sectionName: string) => void,
  ): Promise<void> {
    // Setup refresh button
    this.setupRefreshButton(filesTree);

    // Setup doctype change handler
    if (docTypeSelector) {
      setupDoctypeChangeWithTree(docTypeSelector, filesTree, writerFilter, {
        editor: this.editor,
        sectionsManager: this.sectionsManager,
        state: this.state,
        pdfPreviewManager: this.pdfPreviewManager,
        statePersistence: this.statePersistence,
      });
    }

    // Editor->tree sync disabled: tree is shared across modules

    // Populate section dropdown
    await populateSectionDropdownDirect(
      currentDoctype,
      onFileSelectHandler,
      this.compilationManager,
      this.state,
    );
  }

  /**
   * Create a new WorkspaceFilesTree instance
   */
  private async createNewTree(
    projectOwner: string,
    projectSlug: string,
    onFileSelect: (path: string, item: any) => void,
  ): Promise<any> {
    const module =
      (await import("@/components/workspace-files-tree/WorkspaceFilesTree")) as any;
    const WorkspaceFilesTree: WorkspaceFilesTreeType =
      module.WorkspaceFilesTree;

    const treeConfig = createWriterTreeConfig(
      projectOwner,
      projectSlug,
      onFileSelect,
    );
    const filesTree = new WorkspaceFilesTree(treeConfig);

    await filesTree.initialize();
    (window as any).writerFileTree = filesTree;

    // Initialize hidden files toggle
    const toggleModule =
      (await import("@/components/workspace-files-tree/_HiddenFilesToggle")) as any;
    toggleModule.initHiddenFilesToggle(filesTree);

    // Initialize git status toggle
    const gitToggleModule =
      (await import("@/components/workspace-files-tree/_GitStatusToggle")) as any;
    gitToggleModule.initGitStatusToggle(filesTree);

    // Initialize module filter buttons (S C V W)
    const filterButtonsModule =
      (await import("@/components/workspace-files-tree/_ModuleFilterButtons")) as any;
    filterButtonsModule.initModuleFilterButtons(filesTree, "writer");

    // Initialize WriterTreeSync for bidirectional synchronization
    const doctypeSelector = document.getElementById(
      "doctype-selector",
    ) as HTMLSelectElement;
    const sectionDropdown = document.getElementById(
      "section-selector-dropdown",
    ) as HTMLElement;
    const sectionText = document.getElementById(
      "section-selector-text",
    ) as HTMLElement;

    if (doctypeSelector && sectionDropdown && sectionText) {
      initWriterTreeSync({
        doctypeSelector,
        sectionDropdown,
        sectionText,
        treeInstance: filesTree,
      });
      console.log("[FileTreeSetup] WriterTreeSync initialized");
    }

    return filesTree;
  }

  /**
   * Setup refresh button
   */
  private setupRefreshButton(filesTree: any): void {
    const refreshBtn = document.getElementById("refresh-files-btn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => {
        filesTree.refresh();
      });
    }
  }

  /**
   * Setup without file tree container (dropdown only)
   */
  private setupWithoutFileTree(
    onFileSelectHandler: (sectionId: string, sectionName: string) => void,
  ): void {
    console.log(
      "[FileTreeSetup] No file tree container, populating dropdown directly",
    );

    // Restore saved doctype
    const savedDoctype = this.statePersistence.getSavedDoctype();
    const initialDoctype = savedDoctype || "manuscript";

    // Set doctype selector to saved value
    const docTypeSelector = document.getElementById(
      "doctype-selector",
    ) as HTMLSelectElement;
    if (docTypeSelector && savedDoctype) {
      docTypeSelector.value = savedDoctype;
      console.log("[FileTreeSetup] Restored saved doctype:", savedDoctype);
    }

    populateSectionDropdownDirect(
      initialDoctype,
      onFileSelectHandler,
      this.compilationManager,
      this.state,
    );

    // Setup doctype change handler
    if (docTypeSelector) {
      setupDoctypeChangeWithoutTree(docTypeSelector, onFileSelectHandler, {
        editor: this.editor,
        sectionsManager: this.sectionsManager,
        state: this.state,
        pdfPreviewManager: this.pdfPreviewManager,
        statePersistence: this.statePersistence,
        compilationManager: this.compilationManager,
      });
    }
  }
}
