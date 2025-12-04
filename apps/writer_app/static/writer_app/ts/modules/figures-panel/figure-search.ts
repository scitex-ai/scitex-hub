/**
 * Figure Search Module
 * Handles search, sort, and filter functionality
 */

import type { Figure } from "./figures-list.js";
import { statePersistence } from "../state-persistence.js";

export class FigureSearch {
  private onSearchChange?: (filteredFigures: Figure[]) => void;

  constructor() {
    console.log("[FigureSearch] Initialized");
  }

  /**
   * Set search change callback
   */
  setOnSearchChange(callback: (filteredFigures: Figure[]) => void): void {
    this.onSearchChange = callback;
  }

  /**
   * Setup search and sort event listeners
   */
  setupEventListeners(
    searchInputId: string = "figures-search-toolbar",
    sortSelectId: string = "figures-sort-toolbar",
  ): void {
    const searchInput = document.getElementById(searchInputId) as HTMLInputElement;
    const sortSelect = document.getElementById(sortSelectId) as HTMLSelectElement;

    if (searchInput) {
      searchInput.addEventListener("input", () => {
        this.handleSearch(searchInput);
      });
    }

    if (sortSelect) {
      // Restore saved sorting preference
      const savedSort = statePersistence.getSavedFiguresSorting?.() || "name";
      if (savedSort) {
        sortSelect.value = savedSort;
        console.log("[FigureSearch] Restored sorting preference:", savedSort);
      }

      sortSelect.addEventListener("change", () => {
        this.saveSort(sortSelect.value);
      });
    }

    console.log("[FigureSearch] Event listeners setup complete");
  }

  /**
   * Handle search input
   */
  private handleSearch(searchInput: HTMLInputElement): void {
    const query = searchInput.value.toLowerCase().trim();
    console.log(`[FigureSearch] Search query: "${query}"`);
  }

  /**
   * Filter figures based on search query
   */
  filterFigures(figures: Figure[], query: string): Figure[] {
    if (!query || !query.trim()) {
      return [...figures];
    }

    const lowerQuery = query.toLowerCase().trim();

    return figures.filter((figure) => {
      const searchableFields = [
        figure.label || figure.file_name,
        figure.file_name,
        figure.caption,
        figure.location,
        figure.file_type,
        ...(figure.tags || []),
      ];

      return searchableFields.some((field) =>
        field?.toLowerCase().includes(lowerQuery),
      );
    });
  }

  /**
   * Sort figures based on sort option
   */
  sortFigures(figures: Figure[], sortBy: string): Figure[] {
    const sorted = [...figures];

    switch (sortBy) {
      case "name":
        sorted.sort((a, b) => {
          const aName = a.label || a.file_name;
          const bName = b.label || b.file_name;
          return aName.localeCompare(bName);
        });
        break;

      case "name-desc":
        sorted.sort((a, b) => {
          const aName = a.label || a.file_name;
          const bName = b.label || b.file_name;
          return bName.localeCompare(aName);
        });
        break;

      case "size":
        sorted.sort((a, b) => (b.file_size || 0) - (a.file_size || 0));
        break;

      case "size-desc":
        sorted.sort((a, b) => (a.file_size || 0) - (b.file_size || 0));
        break;

      case "recent":
        sorted.sort((a, b) => (b.last_modified || 0) - (a.last_modified || 0));
        break;

      case "type":
        sorted.sort((a, b) => {
          const aType = a.file_type || "";
          const bType = b.file_type || "";
          return aType.localeCompare(bType);
        });
        break;

      case "referenced":
        sorted.sort((a, b) => {
          const aRef = a.reference_count || 0;
          const bRef = b.reference_count || 0;
          return bRef - aRef;
        });
        break;

      default:
        // Default to name sorting
        sorted.sort((a, b) => {
          const aName = a.label || a.file_name;
          const bName = b.label || b.file_name;
          return aName.localeCompare(bName);
        });
    }

    console.log(`[FigureSearch] Sorted ${sorted.length} figures by: ${sortBy}`);
    return sorted;
  }

  /**
   * Save sorting preference
   */
  private saveSort(sortBy: string): void {
    if (typeof (statePersistence as any).saveFiguresSorting === "function") {
      (statePersistence as any).saveFiguresSorting(sortBy);
      console.log("[FigureSearch] Saved sorting preference:", sortBy);
    }
  }

  /**
   * Apply search and sort
   */
  applySearchAndSort(
    figures: Figure[],
    searchQuery: string,
    sortBy: string,
  ): Figure[] {
    let result = this.filterFigures(figures, searchQuery);
    result = this.sortFigures(result, sortBy);
    return result;
  }

  /**
   * Get current search query
   */
  getCurrentSearchQuery(
    searchInputId: string = "figures-search-toolbar",
  ): string {
    const searchInput = document.getElementById(searchInputId) as HTMLInputElement;
    return searchInput?.value.toLowerCase().trim() || "";
  }

  /**
   * Get current sort option
   */
  getCurrentSortOption(
    sortSelectId: string = "figures-sort-toolbar",
  ): string {
    const sortSelect = document.getElementById(sortSelectId) as HTMLSelectElement;
    return sortSelect?.value || "name";
  }

  /**
   * Clear search
   */
  clearSearch(searchInputId: string = "figures-search-toolbar"): void {
    const searchInput = document.getElementById(searchInputId) as HTMLInputElement;
    if (searchInput) {
      searchInput.value = "";
    }
  }
}
