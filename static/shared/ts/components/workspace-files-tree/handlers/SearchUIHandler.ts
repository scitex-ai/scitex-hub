/**
 * Search UI Handler
 *
 * Always-visible search input for the workspace files tree.
 * Ctrl+K focuses it; Escape clears and blurs.
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
   * Render the search box (call once during init).
   * The box is always visible at the top of the container.
   */
  render(): void {
    if (this.searchBox) return;

    this.searchBox = document.createElement("div");
    this.searchBox.className = "wft-search-box";
    this.searchBox.innerHTML = `
      <div class="wft-search-input-wrapper">
        <i class="fas fa-search wft-search-icon"></i>
        <input type="text" class="wft-search-input" placeholder="Filter files..." />
        <kbd class="wft-search-kbd">Ctrl K</kbd>
        <button class="wft-search-clear" title="Clear (Esc)" style="display: none;">
          <i class="fas fa-times"></i>
        </button>
      </div>
    `;

    // Insert at the bottom of the container
    this.container.appendChild(this.searchBox);

    this.input = this.searchBox.querySelector("input") as HTMLInputElement;
    const clearBtn = this.searchBox.querySelector(
      ".wft-search-clear",
    ) as HTMLButtonElement;
    const kbd = this.searchBox.querySelector(".wft-search-kbd") as HTMLElement;

    // Handle input changes with debounce
    let debounceTimer: number | null = null;
    this.input.addEventListener("input", () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(() => {
        const val = this.input!.value;
        this.callbacks.setSearchQuery(val);
        // Toggle clear button and kbd visibility
        clearBtn.style.display = val ? "flex" : "none";
        kbd.style.display = val ? "none" : "flex";
      }, 150);
    });

    // Handle keyboard events
    this.input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        this.clear();
      } else if (e.key === "Enter") {
        e.preventDefault();
        const matches = this.searchHandler.getMatchingItems();
        if (matches.length > 0) {
          this.callbacks.selectFile(matches[0].path);
          this.clear();
        }
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        this.container.focus();
      }
    });

    // Hide kbd on focus, show on blur if empty
    this.input.addEventListener("focus", () => {
      kbd.style.display = "none";
    });
    this.input.addEventListener("blur", () => {
      if (!this.input!.value) {
        kbd.style.display = "flex";
      }
    });

    // Clear button
    clearBtn.addEventListener("click", () => {
      this.clear();
      this.input!.focus();
    });
  }

  /**
   * Focus the search input (triggered by Ctrl+K)
   */
  show(): void {
    if (!this.searchBox) this.render();
    this.input?.focus();
    this.input?.select();
  }

  /**
   * Clear search and blur
   */
  private clear(): void {
    if (this.input) {
      this.input.value = "";
      this.input.blur();
    }
    this.callbacks.clearSearch();
    const clearBtn = this.searchBox?.querySelector(
      ".wft-search-clear",
    ) as HTMLElement | null;
    const kbd = this.searchBox?.querySelector(
      ".wft-search-kbd",
    ) as HTMLElement | null;
    if (clearBtn) clearBtn.style.display = "none";
    if (kbd) kbd.style.display = "flex";
    this.container.focus();
  }

  /**
   * Hide/remove search box (for cleanup)
   */
  hide(): void {
    this.clear();
  }

  /**
   * Check if search input is focused
   */
  isVisible(): boolean {
    return document.activeElement === this.input;
  }
}
