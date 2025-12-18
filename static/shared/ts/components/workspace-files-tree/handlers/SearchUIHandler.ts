/**
 * Search UI Handler
 *
 * Manages the search input box UI for the workspace files tree.
 */

import type { SearchHandler } from "./SearchHandler";

export interface SearchUICallbacks {
  setSearchQuery: (query: string) => void;
  clearSearch: () => void;
  selectFile: (path: string) => void;
}

export class SearchUIHandler {
  private container: HTMLElement;
  private searchHandler: SearchHandler;
  private callbacks: SearchUICallbacks;

  constructor(
    container: HTMLElement,
    searchHandler: SearchHandler,
    callbacks: SearchUICallbacks
  ) {
    this.container = container;
    this.searchHandler = searchHandler;
    this.callbacks = callbacks;
  }

  /**
   * Show search input box (triggered by Ctrl+K)
   */
  show(): void {
    // Check if search input already exists
    let searchBox = this.container.querySelector(
      ".wft-search-box"
    ) as HTMLDivElement;
    if (searchBox) {
      // Focus existing input
      const input = searchBox.querySelector("input");
      input?.focus();
      input?.select();
      return;
    }

    // Create search box
    searchBox = document.createElement("div");
    searchBox.className = "wft-search-box";
    searchBox.innerHTML = `
      <div class="wft-search-input-wrapper">
        <i class="fas fa-search wft-search-icon"></i>
        <input type="text" class="wft-search-input" placeholder="Search files... (Esc to close)" autofocus />
        <button class="wft-search-clear" title="Clear search (Esc)">
          <i class="fas fa-times"></i>
        </button>
      </div>
    `;

    // Insert at top of container
    this.container.insertBefore(searchBox, this.container.firstChild);

    const input = searchBox.querySelector("input") as HTMLInputElement;
    const clearBtn = searchBox.querySelector(
      ".wft-search-clear"
    ) as HTMLButtonElement;

    // Focus and select existing query if any
    input.value = this.searchHandler.getQuery();
    input.focus();
    input.select();

    // Handle input changes with debounce
    let debounceTimer: number | null = null;
    input.addEventListener("input", () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(() => {
        this.callbacks.setSearchQuery(input.value);
      }, 150);
    });

    // Handle keyboard events
    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        this.hide();
      } else if (e.key === "Enter") {
        e.preventDefault();
        // Navigate to first match
        const matches = this.searchHandler.getMatchingItems();
        if (matches.length > 0) {
          this.callbacks.selectFile(matches[0].path);
          this.hide();
        }
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        // Focus the tree for navigation
        this.container.focus();
      }
    });

    // Clear button
    clearBtn.addEventListener("click", () => {
      input.value = "";
      this.callbacks.clearSearch();
      input.focus();
    });
  }

  /**
   * Hide search input box
   */
  hide(): void {
    const searchBox = this.container.querySelector(".wft-search-box");
    if (searchBox) {
      searchBox.remove();
      this.callbacks.clearSearch();
      this.container.focus();
    }
  }

  /**
   * Check if search box is visible
   */
  isVisible(): boolean {
    return !!this.container.querySelector(".wft-search-box");
  }
}
