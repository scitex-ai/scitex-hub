/**
 * Table Event Handler
 * Manages user interactions and event coordination
 */

import { Table } from "./types.js";
import { statePersistence } from "../state-persistence.js";

export class TableEventHandler {
  private onSearch?: (query: string) => void;
  private onSort?: (sortBy: string) => void;

  /**
   * Set event callbacks
   */
  setEventCallbacks(callbacks: {
    onSearch?: (query: string) => void;
    onSort?: (sortBy: string) => void;
  }): void {
    this.onSearch = callbacks.onSearch;
    this.onSort = callbacks.onSort;
  }

  /**
   * Setup event listeners
   */
  setupEventListeners(): void {
    // Search input (toolbar)
    const searchInput = document.getElementById(
      "tables-search-toolbar",
    ) as HTMLInputElement;
    if (searchInput) {
      searchInput.addEventListener("input", () => this.handleSearch());
    }

    // Sort select (toolbar)
    const sortSelect = document.getElementById(
      "tables-sort-toolbar",
    ) as HTMLSelectElement;
    if (sortSelect) {
      // Restore saved sorting preference
      const savedSort = statePersistence.getSavedTablesSorting?.() || "name";
      if (savedSort) {
        sortSelect.value = savedSort;
        console.log("[TableEventHandler] Restored sorting preference:", savedSort);
      }

      sortSelect.addEventListener("change", () =>
        this.handleSort(sortSelect.value),
      );
    }

    console.log("[TableEventHandler] Event listeners setup complete");
  }

  /**
   * Handle search
   */
  private handleSearch(): void {
    const searchInput = document.getElementById(
      "tables-search-toolbar",
    ) as HTMLInputElement;
    if (!searchInput) return;

    const query = searchInput.value.toLowerCase().trim();
    this.onSearch?.(query);
  }

  /**
   * Handle sort
   */
  private handleSort(sortBy: string): void {
    // Save sorting preference (if available)
    if (typeof (statePersistence as any).saveTablesSorting === 'function') {
      (statePersistence as any).saveTablesSorting(sortBy);
    }

    this.onSort?.(sortBy);
  }

  /**
   * Handle card click - Open table preview modal
   */
  handleCardClick(table: Table): void {
    const tableKey = table.label || table.file_name;
    console.log("[TableEventHandler] Card clicked:", tableKey);

    // Open preview modal if available
    const tablePreviewModal = (window as any).tablePreviewModal;
    if (tablePreviewModal && table.file_hash) {
      tablePreviewModal.openTable(table.file_hash, table.file_name);
    } else {
      console.warn("[TableEventHandler] Table preview modal not available or no file hash");
    }
  }

  /**
   * Handle card double click - Toggle expanded view
   */
  handleCardDoubleClick(card: HTMLElement, table: Table, createExpandedView: (table: Table) => HTMLElement): void {
    const tableKey = table.label || table.file_name;
    console.log("[TableEventHandler] Card double-clicked:", tableKey);

    // Toggle expanded view
    let expandedView = card.querySelector(".table-expanded-view") as HTMLElement;

    if (expandedView) {
      expandedView.remove();
    } else {
      expandedView = createExpandedView(table);
      card.appendChild(expandedView);
    }
  }
}
