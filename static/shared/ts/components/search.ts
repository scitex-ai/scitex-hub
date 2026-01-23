/**
 * Global Search TypeScript
 * Handles global search, autocomplete, and search modal functionality
 */

interface SearchSuggestion {
  type?: string;
  url: string;
  icon?: string;
  title: string;
  subtitle?: string;
}

interface AutocompleteResponse {
  suggestions: SearchSuggestion[];
}

function initializeSearch(): void {
  // Global search functionality with autocomplete
  const globalSearch = document.getElementById("global-search") as HTMLInputElement;

  if (globalSearch) {
    // Submit on Enter
    globalSearch.addEventListener("keypress", function (e: KeyboardEvent) {
      if (e.key === "Enter") {
        const query = this.value.trim();
        if (query) {
          window.location.href = `/search/?q=${encodeURIComponent(query)}`;
        }
      }
    });

    // Autocomplete (debounced)
    let autocompleteTimeout: number;
    globalSearch.addEventListener("input", function (this: HTMLInputElement) {
      clearTimeout(autocompleteTimeout);
      const query = this.value.trim();

      if (query.length < 2) {
        hideAutocomplete();
        return;
      }

      autocompleteTimeout = window.setTimeout(async () => {
        try {
          const response = await fetch(
            `/search/api/autocomplete/?q=${encodeURIComponent(query)}`,
          );
          const data: AutocompleteResponse = await response.json();
          showAutocomplete(data.suggestions);
        } catch (err) {
          console.error("Autocomplete error:", err);
        }
      }, 300); // 300ms debounce
    });
  }

  // Autocomplete UI helpers - GitHub-style grouped results
  function showAutocomplete(suggestions: SearchSuggestion[]): void {
    let dropdown = document.getElementById("search-autocomplete") as HTMLElement;

    if (!dropdown) {
      dropdown = document.createElement("div");
      dropdown.id = "search-autocomplete";
      dropdown.style.cssText = `
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: var(--bg-page);
        border: 1px solid var(--border-default);
        border-radius: 6px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        max-height: 500px;
        overflow-y: auto;
        z-index: 1000;
        margin-top: 8px;
      `;
      const searchContainer = document.querySelector(".header-search");
      if (searchContainer) {
        searchContainer.appendChild(dropdown);
      }
    }

    if (suggestions.length === 0) {
      hideAutocomplete();
      return;
    }

    // Group suggestions by type
    const grouped: Record<string, SearchSuggestion[]> = suggestions.reduce(
      (acc, item) => {
        const type = item.type || "other";
        if (!acc[type]) acc[type] = [];
        acc[type].push(item);
        return acc;
      },
      {} as Record<string, SearchSuggestion[]>
    );

    // Render grouped results
    let html = "";
    const typeLabels: Record<string, string> = {
      users: "Owners",
      repositories: "Repositories",
      other: "Other",
    };

    Object.keys(grouped).forEach((type) => {
      const label = typeLabels[type] || type;
      html += `
        <div style="padding: 8px 12px 4px; font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;">
          ${label}
        </div>
      `;

      grouped[type].forEach((s) => {
        html += `
          <a href="${s.url}" class="search-result-item" style=" display: flex; align-items: center; gap: 12px; padding: 8px 12px; color: var(--text-primary); text-decoration: none; border-bottom: 1px solid var(--border-muted); " onmouseover="this.style.background='var(--bg-muted)'" onmouseout="this.style.background='transparent'">
            <span style="font-size: 16px; opacity: 0.7;">${s.icon || "📄"}</span>
            <div style="flex: 1; min-width: 0;">
              <div style="font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${s.title}</div>
              ${s.subtitle ? `<div style="font-size: 12px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${s.subtitle}</div>` : ""}
            </div>
            <div style="font-size: 12px; color: var(--text-muted); white-space: nowrap;">Jump to</div>
          </a>
        `;
      });
    });

    dropdown.innerHTML = html;
    dropdown.style.display = "block";
  }

  function hideAutocomplete(): void {
    const dropdown = document.getElementById("search-autocomplete");
    if (dropdown) {
      dropdown.style.display = "none";
    }
  }

  // Close autocomplete on click outside
  document.addEventListener("click", function (e: MouseEvent) {
    const target = e.target as HTMLElement;
    if (!document.querySelector(".header-search")?.contains(target)) {
      hideAutocomplete();
    }
  });

  // Search Modal Management
  const searchModal = document.getElementById("search-modal") as HTMLElement;
  const searchModalInput = document.getElementById("search-modal-input") as HTMLInputElement;
  const searchModalResults = document.getElementById("search-modal-results") as HTMLElement;
  const globalSearchInput = document.getElementById("global-search") as HTMLInputElement;

  // Open modal when clicking header search or pressing "/"
  function openSearchModal(): void {
    if (searchModal) {
      searchModal.style.display = "block";
      document.body.style.overflow = "hidden";
      setTimeout(() => {
        if (searchModalInput) {
          searchModalInput.focus();
        }
      }, 100);
    }
  }

  // Close modal
  function closeSearchModal(): void {
    if (searchModal) {
      searchModal.style.display = "none";
      document.body.style.overflow = "";
      if (searchModalInput) {
        searchModalInput.value = "";
      }
      if (searchModalResults) {
        searchModalResults.innerHTML = "";
      }
    }
  }

  // Click on header search input
  if (globalSearchInput) {
    globalSearchInput.addEventListener("click", function (e: MouseEvent) {
      e.preventDefault();
      openSearchModal();
    });
  }

  // Search keyboard shortcuts: only "/" to open global modal
  // Note: Ctrl+K is reserved for page-specific search (browse, profile, etc.)
  document.addEventListener("keydown", function (e: KeyboardEvent) {
    // "/" to open modal (only if not in an input/textarea)
    if (
      e.key === "/" &&
      !["INPUT", "TEXTAREA"].includes((document.activeElement as HTMLElement)?.tagName)
    ) {
      e.preventDefault();
      openSearchModal();
    }

    // Close modal on Escape
    if (
      e.key === "Escape" &&
      searchModal &&
      searchModal.style.display === "block"
    ) {
      closeSearchModal();
    }
  });

  // Close modal when clicking backdrop
  if (searchModal) {
    searchModal.addEventListener("click", function (e: MouseEvent) {
      const target = e.target as HTMLElement;
      if (
        target.classList.contains("search-modal-backdrop") ||
        target.classList.contains("search-modal")
      ) {
        closeSearchModal();
      }
    });
  }

  // Search modal input handler
  if (searchModalInput) {
    let searchTimeout: number;
    searchModalInput.addEventListener("input", function (this: HTMLInputElement) {
      clearTimeout(searchTimeout);
      const query = this.value.trim();

      if (query.length < 2) {
        if (searchModalResults) {
          searchModalResults.innerHTML = "";
        }
        return;
      }

      searchTimeout = window.setTimeout(async () => {
        try {
          const response = await fetch(
            `/search/api/autocomplete/?q=${encodeURIComponent(query)}`,
          );
          const data: AutocompleteResponse = await response.json();
          showModalResults(data.suggestions || []);
        } catch (err) {
          console.error("Search error:", err);
        }
      }, 200);
    });
  }

  // Show results in modal
  function showModalResults(suggestions: SearchSuggestion[]): void {
    if (!searchModalResults) return;

    if (suggestions.length === 0) {
      searchModalResults.innerHTML =
        '<div style="padding: 24px; text-align: center; color: var(--text-muted);">No results found</div>';
      return;
    }

    // Group suggestions by type
    const grouped: Record<string, SearchSuggestion[]> = suggestions.reduce(
      (acc, item) => {
        const type = item.type || "other";
        if (!acc[type]) acc[type] = [];
        acc[type].push(item);
        return acc;
      },
      {} as Record<string, SearchSuggestion[]>
    );

    // Render grouped results
    let html = "";
    const typeLabels: Record<string, string> = {
      users: "Owners",
      repositories: "Repositories",
      other: "Other",
    };

    Object.keys(grouped).forEach((type) => {
      const label = typeLabels[type] || type;
      html += `
        <div class="search-modal-section-header">${label}</div>
      `;

      grouped[type].forEach((s) => {
        html += `
          <a href="${s.url}" class="search-modal-result-item">
            <span class="search-modal-result-icon">${s.icon || "📄"}</span>
            <div class="search-modal-result-content">
              <div class="search-modal-result-title">${s.title}</div>
              ${s.subtitle ? `<div class="search-modal-result-subtitle">${s.subtitle}</div>` : ""}
            </div>
            <div class="search-modal-result-action">Jump to</div>
          </a>
        `;
      });
    });

    searchModalResults.innerHTML = html;
  }
}

// Initialize immediately if DOM is ready, otherwise wait
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeSearch);
} else {
  initializeSearch();
}
