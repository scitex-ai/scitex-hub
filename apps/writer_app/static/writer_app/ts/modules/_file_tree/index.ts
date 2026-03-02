/**
 * Writer File Tree Module - Orchestrator
 * Handles file tree browsing and navigation
 *
 * Refactored from 649 lines to modular architecture.
 * Original: file_tree_backup.ts
 */

import { ApiClient } from "@/utils/api";
import { getWriterFilter, WriterFileFilter } from "../_writer-file-filter";
import { FileTreeNode, FileTreeOptions } from "./types";
import { TreeRenderer } from "./TreeRenderer";
import { DirectoryManager } from "./DirectoryManager";
import { FileSelector } from "./FileSelector";
import { TexFileDropdown } from "./TexFileDropdown";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/_file_tree/index.ts loaded",
);

export type { FileTreeNode, FileTreeOptions };

export class FileTreeManager {
  private apiClient: ApiClient;
  private projectId: number;
  private container: HTMLElement;
  private filter: WriterFileFilter;
  private treeData: FileTreeNode[] = [];

  // Component modules
  private treeRenderer: TreeRenderer;
  private directoryManager: DirectoryManager;
  private fileSelector: FileSelector;
  private texFileDropdown: TexFileDropdown;

  constructor(options: FileTreeOptions) {
    this.apiClient = new ApiClient();
    this.projectId = options.projectId;
    this.container = options.container;
    this.filter = getWriterFilter();

    // Initialize modules
    this.directoryManager = new DirectoryManager(this.treeData, () =>
      this.render(),
    );

    this.fileSelector = new FileSelector(this.container, options.onFileSelect);

    this.treeRenderer = new TreeRenderer(
      this.filter,
      this.directoryManager.getExpandedDirs(),
      {
        onToggleDirectory: (path) =>
          this.directoryManager.toggleDirectory(path),
        onFileSelect: (filePath, fileName) =>
          this.fileSelector.selectFile(filePath, fileName),
      },
    );

    this.texFileDropdown = new TexFileDropdown(
      options.texFileDropdownId,
      (sectionId, sectionName) =>
        this.fileSelector.selectFile(sectionId, sectionName),
    );

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
      this.directoryManager.updateTreeData(this.treeData);
      console.log("[FileTree] Loaded", this.treeData.length, "root items");

      // Populate section dropdown for manuscript type (default)
      await this.texFileDropdown.populate("manuscript");

      this.render();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to load file tree";
      console.error("[FileTree] Error:", message);
      this.treeRenderer.renderError(message, this.container);
    }
  }

  /**
   * Render file tree in the container
   */
  private render(): void {
    this.treeRenderer.render(this.treeData, this.container);
  }

  /**
   * Refresh file tree
   */
  async refresh(): Promise<void> {
    await this.load();
  }

  /**
   * Set file selection callback
   */
  onFileSelect(callback: (filePath: string, fileName: string) => void): void {
    this.fileSelector.setCallback(callback);
  }

  /**
   * Update for document type
   */
  updateForDocType(docType: string): void {
    console.log("[FileTree] Switching to document type:", docType);
    this.filter.updateFilter(docType, null);
    this.texFileDropdown.populate(docType);
    this.render();
  }

  /**
   * Update for section
   */
  updateForSection(section: string | null): void {
    console.log("[FileTree] Switching to section:", section);
    this.filter.updateFilter(this.filter.currentDocType, section);

    if (section) {
      this.focusOnSection(section);
    }

    this.render();
  }

  /**
   * Focus on a specific section
   */
  private focusOnSection(section: string): void {
    const texFiles = this.texFileDropdown.extractTexFiles(this.treeData);
    const sectionFileName = `${section}.tex`;
    const matchingFile = texFiles.find((file) => file.name === sectionFileName);

    if (matchingFile) {
      console.log("[FileTree] Focusing on section file:", matchingFile.path);
      this.foldExceptTarget(matchingFile.path);
      this.fileSelector.focusOnTarget(matchingFile.path, true);
    } else {
      console.warn("[FileTree] Section file not found:", sectionFileName);
    }
  }

  /**
   * Fold all directories except those containing target file
   */
  public foldExceptTarget(targetPath: string): void {
    this.directoryManager.foldExceptTarget(targetPath);
  }

  /**
   * Focus on a specific file path
   */
  public focusOnTarget(path: string, highlight: boolean = true): void {
    this.directoryManager.expandParentDirectories(path);
    this.fileSelector.focusOnTarget(path, highlight);
  }

  /**
   * Populate TeX file dropdown
   */
  public async populateTexFileDropdown(
    docType: string = "manuscript",
  ): Promise<void> {
    await this.texFileDropdown.populate(docType);
  }
}
