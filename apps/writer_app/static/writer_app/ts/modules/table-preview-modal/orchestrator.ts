/**
 * Table Preview Modal Orchestrator
 * Coordinates all table preview modal components
 */

console.log("[DEBUG] table-preview-modal/orchestrator.ts loaded");

import { TableStateManager } from "./table-state.js";
import { TableRenderer } from "./table-renderer.js";
import { TableAPIClient } from "./table-api.js";
import { TableEventManager } from "./table-events.js";
import { TableExporter } from "./table-export.js";

export class TablePreviewModalOrchestrator {
  private stateManager: TableStateManager;
  private renderer: TableRenderer;
  private apiClient: TableAPIClient | null = null;
  private eventManager: TableEventManager;
  private exporter: TableExporter;

  constructor() {
    this.stateManager = new TableStateManager();
    this.renderer = new TableRenderer(this.stateManager);
    this.exporter = new TableExporter();

    // Initialize API client if project ID is available
    const projectId = this.stateManager.getProjectId();
    if (projectId) {
      this.apiClient = new TableAPIClient(projectId);
    }

    // Initialize event manager
    this.eventManager = new TableEventManager(
      this.stateManager,
      this.renderer,
      () => this.handleSave(),
      () => this.handleExport(),
    );

    this.init();
  }

  private init(): void {
    this.eventManager.setupButtonListeners();
    this.eventManager.setupModalCloseListener();
    console.log(
      "[TablePreviewModalOrchestrator] Initialized with project:",
      this.stateManager.getProjectId(),
    );
  }

  async openTable(fileHash: string, fileName: string): Promise<void> {
    if (!this.apiClient) {
      console.error("[TablePreviewModalOrchestrator] No project ID available");
      alert("Error: No project ID found");
      return;
    }

    // Reset state
    this.stateManager.setCurrentFileHash(fileHash);
    this.stateManager.reset();
    this.renderer.updateModifiedBadge();

    // Update modal title
    const titleEl = document.getElementById("table-preview-title");
    if (titleEl) {
      titleEl.textContent = fileName;
    }

    // Show modal
    const modal = document.getElementById("tablePreviewModal");
    if (modal) {
      const bsModal = new (window as any).bootstrap.Modal(modal);
      bsModal.show();
    }

    // Load data
    await this.loadTableData(fileHash);
  }

  private async loadTableData(fileHash: string): Promise<void> {
    const container = document.getElementById("table-preview-container");
    if (!container || !this.apiClient) return;

    // Show loading
    this.renderer.showLoading(container);

    try {
      const tableData = await this.apiClient.loadTableData(fileHash);
      this.stateManager.setCurrentTable(tableData);
      this.renderer.render(container);
      this.eventManager.attachTableEventListeners();
      this.renderer.updateDimensionsBadge();
    } catch (error) {
      console.error("[TablePreviewModalOrchestrator] Error loading table:", error);
      this.renderer.showError(
        error instanceof Error ? error.message : "Network error while loading table",
      );
    }
  }

  private async handleSave(): Promise<void> {
    const table = this.stateManager.getCurrentTable();
    const fileHash = this.stateManager.getCurrentFileHash();

    if (!table || !fileHash || !this.apiClient) return;

    // Apply modifications to table data
    this.stateManager.applyModifications();

    try {
      await this.apiClient.saveTableData(fileHash, table.data, table.columns);
      alert("Table saved successfully!");

      // Reset modification state
      this.stateManager.clearModifiedCells();
      this.stateManager.clearRenamedColumns();
      this.stateManager.setModified(false);
      this.renderer.updateModifiedBadge();

      // Reload data to get updated thumbnail
      await this.loadTableData(fileHash);
    } catch (error) {
      console.error("[TablePreviewModalOrchestrator] Error saving table:", error);
      this.renderer.showError(
        error instanceof Error ? error.message : "Network error while saving table",
      );
    }
  }

  private handleExport(): void {
    const table = this.stateManager.getCurrentTable();
    if (!table) return;

    this.exporter.exportToCSV(table);
  }
}
