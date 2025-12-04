/**
 * Writer File Tree Module - Main Entry Point (Orchestrator)
 * Handles file tree browsing and navigation
 *
 * Refactored from 649 lines to modular architecture.
 * Original: file_tree_backup.ts
 */

import { ApiClient } from "@/utils/api";
import { getWriterFilter, WriterFileFilter } from "./writer-file-filter.js";
import { FileTreeNode, FileTreeOptions } from "./file-tree/types.js";
import { TreeRenderer } from "./file-tree/tree-renderer.js";
import { DirectoryManager } from "./file-tree/directory-manager.js";
import { FileSelector } from "./file-tree/file-selector.js";
import { SectionDropdownManager } from "./file-tree/section-dropdown.js";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/file_tree.ts loaded",
);

export class FileTreeManager {
  private apiClient: ApiClient;
  private projectId: number;
  private container: HTMLElement;
  private texFileDropdownId?: string;
  private filter: WriterFileFilter;
  private treeData: FileTreeNode[] = [];

  // Delegated components
  private renderer: TreeRenderer;
  private directoryManager: DirectoryManager;
  private fileSelector: FileSelector;
  private dropdownManager: SectionDropdownManager;

  constructor(options: FileTreeOptions) {
    this.apiClient = new ApiClient();
    this.projectId = options.projectId;
    this.container = options.container;
    this.texFileDropdownId = options.texFileDropdownId;
    this.filter = getWriterFilter();

    // Initialize components
    this.directoryManager = new DirectoryManager(this.container);
    this.fileSelector = new FileSelector(this.container, options.onFileSelect);
    this.dropdownManager = new SectionDropdownManager();

    this.renderer = new TreeRenderer(
      this.container,
      this.filter,
      this.directoryManager.getExpandedDirs(),
    );

    // Connect renderer callbacks
    this.renderer.setOnFileSelect((path, name) => {
      this.fileSelector.selectFile(path, name);
    });

    this.renderer.setOnDirectoryToggle((path) => {
      this.directoryManager.toggleDirectory(path);
      this.load();
    });

    console.log("[FileTree] Initialized for project", this.projectId);
  }

  /**
   * Load and render file tree
   */
  async load(): Promise<void> {
    try {
      console.log("[FileTree] Loading file tree...");

      const response = await this.apiClient.get<{ tree: FileTreeNode[] }>(
        `/writer/api/project/${this.projectId}/file-tree/`,
      );

      if (!response.success || !response.data) {
        throw new Error(response.error || "Failed to load file tree");
      }

      this.treeData = response.data.tree;
      console.log("[FileTree] Loaded", this.treeData.length, "root items");

      // Populate section dropdown for manuscript type (default)
      if (this.texFileDropdownId) {
        await this.dropdownManager.populateTexFileDropdown(
          this.texFileDropdownId,
          "manuscript",
          (path, name) => this.fileSelector.selectFile(path, name),
        );
      }

      this.renderer.render(this.treeData, this.directoryManager.getExpandedDirs());
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to load file tree";
      console.error("[FileTree] Error:", message);
      this.renderer.renderError(message);
    }
  }

  /**
   * Refresh file tree
   */
  async refresh(): Promise<void> {
    console.log("[FileTree] Refreshing...");
    await this.load();
  }

  /**
   * Set file selection callback
   */
  onFileSelect(callback: (filePath: string, fileName: string) => void): void {
    this.fileSelector.onFileSelect(callback);
  }

  /**
   * Update sections dropdown for a new document type
   */
  updateForDocType(docType: string): void {
    console.log("[FileTree] Updating sections for document type:", docType);
    this.filter.setDoctype(docType);

    if (this.texFileDropdownId) {
      this.dropdownManager.populateTexFileDropdown(
        this.texFileDropdownId,
        docType,
        (path, name) => this.fileSelector.selectFile(path, name),
      );
    }

    this.load();
  }

  /**
   * Update filter for a new section
   */
  updateForSection(section: string | null): void {
    console.log("[FileTree] Updating filter for section:", section);
    this.filter.setSection(section);

    this.load().then(() => {
      if (section) {
        this.focusOnSection(section);
      }
    });
  }

  /**
   * Focus on a section file in the tree
   */
  private focusOnSection(section: string): void {
    const currentDoctype = this.filter.getState().doctype;
    const expectedPath = this.filter.getExpectedFilePath(currentDoctype, section);

    console.log("[FileTree] Attempting to focus on section file:", expectedPath);
    this.directoryManager.focusOnTarget(
      this.container,
      expectedPath,
      this.treeData,
      () => this.renderer.render(this.treeData, this.directoryManager.getExpandedDirs()),
    );
  }

  /**
   * Fold all directories except those in the path to target
   */
  public foldExceptTarget(targetPath: string): void {
    this.directoryManager.foldExceptTarget(targetPath);
    this.load().then(() => {
      console.log("[FileTree] Folded all except target:", targetPath);
    });
  }

  /**
   * Focus on a target file in the tree
   */
  public focusOnTarget(path: string, highlight: boolean = true): void {
    this.directoryManager.focusOnTarget(
      this.container,
      path,
      this.treeData,
      () => this.renderer.render(this.treeData, this.directoryManager.getExpandedDirs()),
      highlight,
    );
    console.log("[FileTree] Focused on target:", path);
  }

  /**
   * Populate the section dropdown selector
   */
  public async populateTexFileDropdown(
    docType: string = "manuscript",
  ): Promise<void> {
    if (!this.texFileDropdownId) return;

    await this.dropdownManager.populateTexFileDropdown(
      this.texFileDropdownId,
      docType,
      (path, name) => this.fileSelector.selectFile(path, name),
    );
  }
}

// Re-export types for backward compatibility
export type { FileTreeNode, FileTreeOptions };
