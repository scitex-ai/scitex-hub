/**
 * Table Data Manager
 * Handles data loading, state management, and API interactions
 */

import { Table } from "./types.js";

export class TableDataManager {
  private tables: Table[] = [];
  private filteredTables: Table[] = [];
  private isLoaded: boolean = false;
  private projectId: string | null = null;

  constructor() {
    this.initProjectId();
  }

  /**
   * Initialize project ID from window config
   */
  private initProjectId(): void {
    const writerConfig = (window as any).WRITER_CONFIG;
    if (writerConfig?.projectId) {
      this.projectId = String(writerConfig.projectId);
      console.log("[TableDataManager] Initialized with project:", this.projectId);
    }
  }

  /**
   * Get project ID
   */
  getProjectId(): string | null {
    return this.projectId;
  }

  /**
   * Get all tables
   */
  getTables(): Table[] {
    return this.tables;
  }

  /**
   * Get filtered tables
   */
  getFilteredTables(): Table[] {
    return this.filteredTables;
  }

  /**
   * Set filtered tables
   */
  setFilteredTables(tables: Table[]): void {
    this.filteredTables = tables;
  }

  /**
   * Check if tables are loaded
   */
  getIsLoaded(): boolean {
    return this.isLoaded;
  }

  /**
   * Load tables from API
   */
  async loadTables(): Promise<boolean> {
    if (this.isLoaded) {
      console.log("[TableDataManager] Already loaded, skipping");
      return true;
    }

    if (!this.projectId) {
      console.error("[TableDataManager] No project ID available");
      return false;
    }

    try {
      const apiUrl = `/writer/api/project/${this.projectId}/tables/`;
      console.log("[TableDataManager] Fetching from:", apiUrl);

      const response = await fetch(apiUrl);
      const data = await response.json();

      if (data.success && data.tables) {
        this.tables = data.tables;
        this.filteredTables = [...this.tables];
        this.isLoaded = true;

        console.log(`[TableDataManager] Loaded ${this.tables.length} tables`);
        return true;
      } else {
        console.warn("[TableDataManager] No tables found");
        return false;
      }
    } catch (error) {
      console.error("[TableDataManager] Error loading tables:", error);
      return false;
    }
  }

  /**
   * Filter tables by search query
   */
  filterTables(query: string): void {
    if (!query) {
      this.filteredTables = [...this.tables];
    } else {
      const lowerQuery = query.toLowerCase();
      this.filteredTables = this.tables.filter(
        (table) =>
          (table.label || table.file_name).toLowerCase().includes(lowerQuery) ||
          table.file_name.toLowerCase().includes(lowerQuery) ||
          table.caption?.toLowerCase().includes(lowerQuery) ||
          table.location?.toLowerCase().includes(lowerQuery),
      );
    }
  }

  /**
   * Sort filtered tables
   */
  sortTables(sortBy: string): void {
    console.log("[TableDataManager] Sorting by:", sortBy);

    switch (sortBy) {
      case "name":
        this.filteredTables.sort((a, b) => {
          const aName = a.label || a.file_name;
          const bName = b.label || b.file_name;
          return aName.localeCompare(bName);
        });
        break;
      case "name-desc":
        this.filteredTables.sort((a, b) => {
          const aName = a.label || a.file_name;
          const bName = b.label || b.file_name;
          return bName.localeCompare(aName);
        });
        break;
      case "size":
        this.filteredTables.sort((a, b) => (b.file_size || 0) - (a.file_size || 0));
        break;
      case "size-desc":
        this.filteredTables.sort((a, b) => (a.file_size || 0) - (b.file_size || 0));
        break;
      case "recent":
        this.filteredTables.sort((a, b) => (b.last_modified || 0) - (a.last_modified || 0));
        break;
      default:
        this.filteredTables.sort((a, b) => {
          const aName = a.label || a.file_name;
          const bName = b.label || b.file_name;
          return aName.localeCompare(bName);
        });
    }
  }

  /**
   * Reset loaded state to allow reload
   */
  resetLoadedState(): void {
    this.isLoaded = false;
  }
}
