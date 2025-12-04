/**
 * Tables Panel Orchestrator
 * Lightweight coordinator for tables panel modules
 */

console.log("[DEBUG] tables-panel.ts loaded");

import { Table } from "./tables-panel/types.js";
import { TableDataManager } from "./tables-panel/TableDataManager.js";
import { TableRenderer } from "./tables-panel/TableRenderer.js";
import { TableUploadHandler } from "./tables-panel/TableUploadHandler.js";
import { TableDragHandler } from "./tables-panel/TableDragHandler.js";
import { TableUIManager } from "./tables-panel/TableUIManager.js";
import { TableEventHandler } from "./tables-panel/TableEventHandler.js";
import { statePersistence } from "./state-persistence.js";

// Re-export Table type for external use
export type { Table };

export class TablesPanel {
  private dataManager: TableDataManager;
  private renderer: TableRenderer;
  private uploadHandler: TableUploadHandler;
  private dragHandler: TableDragHandler;
  private uiManager: TableUIManager;
  private eventHandler: TableEventHandler;

  constructor() {
    this.dataManager = new TableDataManager();
    this.renderer = new TableRenderer();
    this.uploadHandler = new TableUploadHandler(this.dataManager.getProjectId());
    this.dragHandler = new TableDragHandler();
    this.uiManager = new TableUIManager();
    this.eventHandler = new TableEventHandler();

    this.init();
  }

  /**
   * Initialize the panel
   */
  private init(): void {
    // Setup renderer event handlers
    this.renderer.setEventHandlers({
      onCardClick: (table) => this.eventHandler.handleCardClick(table),
      onCardDoubleClick: (card, table) =>
        this.eventHandler.handleCardDoubleClick(
          card,
          table,
          (t) => this.renderer.createExpandedView(t)
        ),
      onCheckboxChange: () => this.updateCountDisplay(),
      onDragStart: (event, table) => this.dragHandler.handleDragStart(event, table),
      onDragEnd: (event) => this.dragHandler.handleDragEnd(event),
    });

    // Setup event handler callbacks
    this.eventHandler.setEventCallbacks({
      onSearch: (query) => this.handleSearch(query),
      onSort: (sortBy) => this.handleSort(sortBy),
    });

    // Setup upload handler callback
    this.uploadHandler.setOnUploadSuccess(() => this.handleUploadSuccess());

    // Setup event listeners
    this.eventHandler.setupEventListeners();
    this.uploadHandler.setupDropZone();

    console.log("[TablesPanel] Initialized with project:", this.dataManager.getProjectId());
  }

  /**
   * Load tables from API
   */
  async loadTables(): Promise<void> {
    if (this.dataManager.getIsLoaded()) {
      console.log("[TablesPanel] Already loaded, skipping");
      return;
    }

    this.uiManager.showLoading();

    const success = await this.dataManager.loadTables();

    if (success) {
      // Apply saved sort or default to name
      const savedSort = statePersistence.getSavedTablesSorting?.() || "name";
      this.handleSort(savedSort);
    } else {
      this.uiManager.showEmptyState();
    }
  }

  /**
   * Handle search
   */
  private handleSearch(query: string): void {
    this.dataManager.filterTables(query);
    this.renderTables();
    console.log(`[TablesPanel] Search: "${query}" -> ${this.dataManager.getFilteredTables().length} results`);
  }

  /**
   * Handle sort
   */
  private handleSort(sortBy: string): void {
    this.dataManager.sortTables(sortBy);
    this.renderTables();
  }

  /**
   * Handle upload success
   */
  private async handleUploadSuccess(): Promise<void> {
    this.dataManager.resetLoadedState();
    await this.loadTables();
  }

  /**
   * Render tables
   */
  private renderTables(): void {
    const filteredTables = this.dataManager.getFilteredTables();

    // Hide all empty states
    this.uiManager.hideAllStates();

    // Update count display
    this.updateCountDisplay();

    if (filteredTables.length === 0) {
      const searchInput = document.getElementById(
        "tables-search-toolbar",
      ) as HTMLInputElement;
      if (searchInput && searchInput.value.trim()) {
        this.uiManager.showNoResults();
      } else {
        this.uiManager.showEmptyState();
      }
      return;
    }

    this.renderer.renderTables(filteredTables);
  }

  /**
   * Update count display
   */
  private updateCountDisplay(): void {
    const selectedCount = this.renderer.getSelectedCards().size;
    const totalCount = this.dataManager.getFilteredTables().length;
    this.uiManager.updateCountDisplay(selectedCount, totalCount);
  }
}

// Initialize and expose globally
const tablesPanel = new TablesPanel();
(window as any).tablesPanel = tablesPanel;

console.log("[TablesPanel] Module initialized and exposed globally");
