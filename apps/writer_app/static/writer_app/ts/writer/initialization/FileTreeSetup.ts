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

import { populateSectionDropdownDirect, syncDropdownsFromPath } from "../../utils/index";
import { initializeWriterFilter } from "../../modules/writer-file-filter";
import { PanelSwitcher } from "../ui/PanelSwitcher";
import {
  createFileSelectHandler,
  setupDoctypeChangeWithTree,
  setupDoctypeChangeWithoutTree,
  getDoctypeFolder,
  createWriterTreeConfig,
} from "./handlers/index";
import { initWriterTreeSync, getWriterTreeSync } from "../sync/index";

console.log("[DEBUG] FileTreeSetup.ts loaded (refactored with handlers)");

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

    // Initialize file tree (including demo mode with projectId 0)
    if (this.config.projectId !== null && this.config.projectId !== undefined) {
      const fileTreeContainer = document.getElementById("writer-file-tree");
      if (fileTreeContainer) {
        this.setupWithFileTree(fileTreeContainer, onFileSelectHandler).catch((error) => {
          console.error("[FileTreeSetup] Failed to setup file tree:", error);
        });
      } else {
        this.setupWithoutFileTree(onFileSelectHandler);
      }
    } else {
      // No projectId - still need to populate dropdown
      console.log("[FileTreeSetup] No project, populating dropdown for demo mode");
      populateSectionDropdownDirect(
        "manuscript",
        onFileSelectHandler,
        this.compilationManager,
        this.state,
      );
    }
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
    const docTypeSelector = document.getElementById("doctype-selector") as HTMLSelectElement;
    if (docTypeSelector && savedDoctype) {
      docTypeSelector.value = savedDoctype;
      console.log("[FileTreeSetup] Restored saved doctype:", savedDoctype);
    }

    // Initialize writer filter with current doctype
    const currentDoctype = savedDoctype || "manuscript";
    const writerFilter = initializeWriterFilter(currentDoctype, null);
    console.log("[FileTreeSetup] Initialized writer filter with doctype:", currentDoctype);

    // Get project owner and slug from config
    const projectOwner = this.config.projectOwner || this.config.visitorUsername || this.config.username;
    const projectSlug = this.config.projectSlug;

    if (!projectOwner || !projectSlug) {
      console.warn("[FileTreeSetup] Missing project owner or slug, skipping file tree");
      return;
    }

    // Enhanced file select handler that updates section filter and switches panel
    const enhancedFileSelectHandler = (path: string, item: any): void => {
      const fileName = path.split('/').pop() || '';
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
          console.log("[FileTreeSetup] Extracted section from file path:", section);
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
        console.log("[FileTreeSetup] WorkspaceFilesTree already initialized, skipping duplicate");
        this.setupExistingTree(existingTree, writerFilter, docTypeSelector, currentDoctype, onFileSelectHandler);
        return;
      }

      // Dynamically import and create tree
      const filesTree = await this.createNewTree(projectOwner, projectSlug, enhancedFileSelectHandler);

      // Focus on initial doctype folder
      const initialDoctypeFolder = getDoctypeFolder(currentDoctype);
      if (filesTree.focusDirectory) {
        console.log("[FileTreeSetup] Focusing on doctype folder:", initialDoctypeFolder);
        filesTree.focusDirectory(initialDoctypeFolder);
      }

      console.log("[FileTreeSetup] WorkspaceFilesTree initialized successfully");

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
      console.error("[FileTreeSetup] Failed to initialize WorkspaceFilesTree:", error);
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

    // Focus on the doctype directory
    const initialDoctypeFolder = getDoctypeFolder(currentDoctype);
    if (filesTree.focusDirectory) {
      console.log("[FileTreeSetup] Focusing on doctype folder:", initialDoctypeFolder);
      filesTree.focusDirectory(initialDoctypeFolder);
    }

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
    onFileSelect: (path: string, item: any) => void
  ): Promise<any> {
    const module = await import("/static/shared/ts/components/workspace-files-tree/WorkspaceFilesTree") as any;
    const WorkspaceFilesTree: WorkspaceFilesTreeType = module.WorkspaceFilesTree;

    const treeConfig = createWriterTreeConfig(projectOwner, projectSlug, onFileSelect);
    const filesTree = new WorkspaceFilesTree(treeConfig);

    await filesTree.initialize();
    (window as any).writerFileTree = filesTree;

    // Initialize WriterTreeSync for bidirectional synchronization
    const doctypeSelector = document.getElementById("doctype-selector") as HTMLSelectElement;
    const sectionDropdown = document.getElementById("section-selector-dropdown") as HTMLElement;
    const sectionText = document.getElementById("section-selector-text") as HTMLElement;

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
    console.log("[FileTreeSetup] No file tree container, populating dropdown directly");

    // Restore saved doctype
    const savedDoctype = this.statePersistence.getSavedDoctype();
    const initialDoctype = savedDoctype || "manuscript";

    // Set doctype selector to saved value
    const docTypeSelector = document.getElementById("doctype-selector") as HTMLSelectElement;
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
