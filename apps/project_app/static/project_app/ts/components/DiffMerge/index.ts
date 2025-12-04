/**
 * DiffMerge Component - Orchestrator
 *
 * Handles file comparison and merging functionality with:
 * - Drag-and-drop file uploads
 * - Repository file selection
 * - Direct text input
 * - Live diff rendering
 * - Merge operations
 *
 * Refactored from 716 lines to modular architecture.
 * Original: DiffMerge_backup.ts
 */

import { DiffMergeConfig, Side } from "./types.ts";
import { DragDropHandler } from "./DragDropHandler.ts";
import { FileOperations } from "./FileOperations.ts";
import { FileBrowser } from "./FileBrowser.ts";
import { DiffRenderer } from "./DiffRenderer.ts";
import { MergeHandler } from "./MergeHandler.ts";
import { UIManager } from "./UIManager.ts";

class DiffMerge {
  private config: DiffMergeConfig;
  private dragDropHandler: DragDropHandler;
  private fileOperations: FileOperations;
  private fileBrowser: FileBrowser;
  private diffRenderer: DiffRenderer;
  private mergeHandler: MergeHandler;
  private uiManager: UIManager;

  constructor(config: DiffMergeConfig) {
    this.config = config;

    // Initialize components
    this.fileOperations = new FileOperations();

    this.dragDropHandler = new DragDropHandler((file, side) => {
      this.fileOperations.handleFileUpload(file, side);
    });

    this.fileBrowser = new FileBrowser(config, (content, side, filename) => {
      this.fileOperations.setContent(content, side, filename);
    });

    this.diffRenderer = new DiffRenderer(config, () => {
      this.diffRenderer.showMergeButtons();
    });

    this.mergeHandler = new MergeHandler(config);

    this.uiManager = new UIManager({
      onClear: (side) => this.fileOperations.clearSide(side),
      onOpenFileBrowser: (side) => this.fileBrowser.open(side),
      onComputeDiff: () => this.handleComputeDiff(),
      onMerge: (strategy) => this.handleMerge(strategy),
      onDownload: () => this.mergeHandler.downloadMerged(),
      onCopy: () => this.mergeHandler.copyMerged(),
      onContentChange: (side, content) =>
        this.fileOperations.updateContent(side, content),
    });

    this.init();
  }

  /**
   * Initialize all modules
   */
  private init(): void {
    this.dragDropHandler.setup();
    this.fileOperations.setupFileInputs((file, side) => {
      this.fileOperations.handleFileUpload(file, side);
    });
    this.uiManager.setupButtons();
    this.fileBrowser.setupModal();
  }

  /**
   * Handle compute diff
   */
  private handleComputeDiff(): void {
    const leftData = this.fileOperations.getLeftData();
    const rightData = this.fileOperations.getRightData();

    this.diffRenderer.computeDiff(
      leftData.content,
      rightData.content,
      leftData.filename,
      rightData.filename
    );
  }

  /**
   * Handle merge
   */
  private handleMerge(strategy: "left" | "right" | "manual"): void {
    const leftData = this.fileOperations.getLeftData();
    const rightData = this.fileOperations.getRightData();

    this.mergeHandler.merge(leftData.content, rightData.content, strategy);
  }
}

// Make it available globally
(window as any).DiffMerge = DiffMerge;
