/**
 * Search UI Handler
 *
 * Hidden by default. Ctrl+K or context menu "Filter" toggles visibility.
 * Escape clears and hides.
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
  private searchBox: HTMLDivElement | null = null;
  private input: HTMLInputElement | null = null;

  constructor(
    container: HTMLElement,
    searchHandler: SearchHandler,
    callbacks: SearchUICallbacks,
  ) {
    this.container = container;
    this.searchHandler = searchHandler;
    this.callbacks = callbacks;
  }

  /**
   * Build the search box DOM (hidden by default).
   */
  render(): void {
    if (this.searchBox) return;

    this.searchBox = document.createElement("div");
    this.searchBox.className = "wft-search-box wft-search-hidden";
    this.searchBox.innerHTML = `
      <div class="wft-search-input-wrapper">
        <i class="fas fa-search wft-search-icon"></i>
        <input type="text" class="wft-search-input" placeholder="Filter files..." />
        <button class="wft-search-clear" title="Clear (Esc)" style="display: none;">
          <i class="fas fa-times"></i>
        </button>
      </div>
    `;

    this.container.appendChild(this.searchBox);

    this.input = this.searchBox.querySelector("input") as HTMLInputElement;
    const clearBtn = this.searchBox.querySelector(
      ".wft-search-clear",
    ) as HTMLButtonElement;

    // Handle input changes with debounce
    let debounceTimer: number | null = null;
    this.input.addEventListener("input", () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(() => {
        const val = this.input!.value;
        this.callbacks.setSearchQuery(val);
        clearBtn.style.display = val ? "flex" : "none";
      }, 150);
    });

    // Handle keyboard events
    this.input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        this.hideBox();
      } else if (e.key === "Enter") {
        e.preventDefault();
        const matches = this.searchHandler.getMatchingItems();
        if (matches.length > 0) {
          this.callbacks.selectFile(matches[0].path);
          this.hideBox();
        }
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        this.container.focus();
      }
    });

    // Clear button
    clearBtn.addEventListener("click", () => {
      this.input!.value = "";
      this.callbacks.clearSearch();
      clearBtn.style.display = "none";
      this.input!.focus();
    });
  }

  /**
   * Toggle search box visibility (triggered by Ctrl+K or context menu)
   */
  show(): void {
    if (!this.searchBox) this.render();
    if (this.searchBox!.classList.contains("wft-search-hidden")) {
      this.searchBox!.classList.remove("wft-search-hidden");
      this.input?.focus();
      this.input?.select();
    } else {
      this.hideBox();
    }
  }

  /**
   * Hide the search box and clear filter
   */
  private hideBox(): void {
    if (this.input) {
      this.input.value = "";
      this.input.blur();
    }
    this.callbacks.clearSearch();
    if (this.searchBox) {
      this.searchBox.classList.add("wft-search-hidden");
      const clearBtn = this.searchBox.querySelector(
        ".wft-search-clear",
      ) as HTMLElement | null;
      if (clearBtn) clearBtn.style.display = "none";
    }
    this.container.focus();
  }

  /**
   * Hide/remove search box (for cleanup)
   */
  hide(): void {
    this.hideBox();
  }

  /**
   * Check if search box is visible
   */
  isVisible(): boolean {
    return (
      !!this.searchBox &&
      !this.searchBox.classList.contains("wft-search-hidden")
    );
  }
}
