/**

 * SciTeX Unified Search Implementation
 *
 * This file implements the unified search system for SciTeX Scholar that aggregates
 * results from multiple academic sources (PubMed, Google Scholar, arXiv, Semantic Scholar)
 * and the SciTeX Index. Results are deduplicated, merged, and ranked intelligently.
 *
 * @version 1.0.0
 */

// Window interface for global configuration

console.log(
  "[DEBUG] apps/scholar_app/static/scholar_app/ts/search/scitex-search.ts loaded",
);
declare global {
  interface Window {
    SCHOLAR_CONFIG?: {
      urls?: {
        search?: string;
      };
    };
    saveSourcePreferences?: () => void;
  }
}

// Export to make this an ES module
export {};

/**
 * Search log manager for status panel
 */
class SearchLogManager {
  private logElement: HTMLElement | null = null;
  private pulseDot: HTMLElement | null = null;

  constructor() {
    this.logElement = document.getElementById("searchLog");
    this.pulseDot = document.getElementById("searchPulseDot");
    this.setupKeyboardShortcuts();
  }

  private setupKeyboardShortcuts(): void {
    if (!this.logElement) return;

    // Make log element focusable
    this.logElement.setAttribute("tabindex", "0");

    // Ctrl+A to select all text in log when focused
    this.logElement.addEventListener("keydown", (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "a") {
        e.preventDefault();
        this.selectAllText();
      }
    });
  }

  selectAllText(): void {
    if (!this.logElement) return;
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(this.logElement);
    selection?.removeAllRanges();
    selection?.addRange(range);
  }

  clear(): void {
    if (this.logElement) {
      this.logElement.textContent = "";
    }
  }

  log(message: string): void {
    if (this.logElement) {
      const timestamp = new Date().toLocaleTimeString("en-US", {
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
      this.logElement.textContent += `[${timestamp}] ${message}\n`;
      this.logElement.scrollTop = this.logElement.scrollHeight;
    }
  }

  showSearching(): void {
    if (this.pulseDot) this.pulseDot.style.display = "inline-block";
  }

  hideSearching(): void {
    if (this.pulseDot) this.pulseDot.style.display = "none";
  }

  updateSourceStatus(
    sourceName: string,
    status: "searching" | "success" | "error" | "idle",
    count?: number | string,
  ): void {
    const item = document.querySelector(
      `.source-progress-item[data-source="${sourceName}"]`,
    ) as HTMLElement | null;
    if (!item) return;

    const spinner = item.querySelector(".spinner-border") as HTMLElement | null;
    const countEl = item.querySelector(".count") as HTMLElement | null;

    // Reset classes
    item.classList.remove("searching", "success", "error");

    switch (status) {
      case "searching":
        item.classList.add("searching");
        if (spinner) spinner.style.display = "inline-block";
        if (countEl) countEl.textContent = "...";
        break;
      case "success":
        item.classList.add("success");
        if (spinner) spinner.style.display = "none";
        if (countEl) countEl.textContent = count?.toString() || "0";
        break;
      case "error":
        item.classList.add("error");
        if (spinner) spinner.style.display = "none";
        if (countEl) countEl.textContent = "ERR";
        break;
      case "idle":
        if (spinner) spinner.style.display = "none";
        if (countEl) countEl.textContent = "-";
        break;
    }
  }

  resetAllSources(): void {
    const items = document.querySelectorAll(".source-progress-item");
    items.forEach((item) => {
      const el = item as HTMLElement;
      el.classList.remove("searching", "success", "error");
      const spinner = el.querySelector(".spinner-border") as HTMLElement | null;
      const count = el.querySelector(".count") as HTMLElement | null;
      if (spinner) spinner.style.display = "none";
      if (count) count.textContent = "-";
    });
  }
}

const searchLog = new SearchLogManager();

/**
 * Search result interface
 */
interface SearchResult {
  id?: string;
  title?: string;
  authors?: string;
  year?: string | number;
  journal?: string;
  abstract?: string;
  citations?: number;
  pmid?: string;
  doi?: string;
  arxivId?: string;
  externalUrl?: string;
  source?: string;
  pdf_url?: string;
  is_open_access?: boolean;
  impact_factor?: number | string;
}

/**
 * Source configuration
 */
interface SourceConfig {
  name: string;
  endpoint: string;
  maxResults: number;
}

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", function () {
  console.log("[SciTeX Search] Initializing unified search system...");

  const searchForm = document.getElementById(
    "literatureSearchForm",
  ) as HTMLFormElement | null;
  const searchInput = document.querySelector(
    'input[name="q"]',
  ) as HTMLInputElement | null;
  const searchButton = document.getElementById(
    "searchButton",
  ) as HTMLButtonElement | null;
  const progressiveResults = document.getElementById(
    "progressiveResults",
  ) as HTMLElement | null;

  if (!searchForm || !searchInput) {
    console.log(
      "[SciTeX Search] Search form not found, skipping initialization",
    );
    return;
  }

  // Intercept form submission
  searchForm.addEventListener("submit", function (e: Event) {
    e.preventDefault();
    const query = searchInput.value.trim();

    // Save current source preferences (defined in scholar-index-main.ts)
    if (typeof (window as any).saveSourcePreferences === "function") {
      (window as any).saveSourcePreferences();
    }

    // Hide regular results container entirely
    const resultsContainer = document.getElementById("scitex-results-container");
    if (resultsContainer) resultsContainer.style.display = "none";
    document.querySelectorAll(".result-card").forEach((card) => {
      (card as HTMLElement).style.display = "none";
    });
    const emptyState = document.getElementById("searchEmptyState");
    if (emptyState) emptyState.style.display = "none";

    // Show progressive interface
    const progressiveLoadingStatus = document.getElementById(
      "progressiveLoadingStatus",
    ) as HTMLElement | null;
    if (progressiveLoadingStatus)
      progressiveLoadingStatus.style.display = "block";

    if (progressiveResults) {
      progressiveResults.style.display = "block";
      progressiveResults.innerHTML = "";
    }

    // Reset progress indicators
    document.querySelectorAll(".progress-source").forEach((source) => {
      const badge = source.querySelector(".badge") as HTMLElement | null;
      const spinner = source.querySelector(
        ".spinner-border",
      ) as HTMLElement | null;
      const count = source.querySelector(".count") as HTMLElement | null;

      if (badge) badge.className = "badge bg-secondary";
      if (spinner) spinner.style.display = "inline-block";
      if (count) count.textContent = "0";
    });

    // Start unified search
    startUnifiedSearch(query);
  });

  console.log("[SciTeX Search] Initialization complete");
});

// Track active searches for completion detection
let activeSearches = 0;
let totalResults = 0;

/**
 * Start unified search across all sources
 */
function startUnifiedSearch(query: string): void {
  console.log("[SciTeX Search] Starting unified search for:", query);

  // Initialize search log
  searchLog.clear();
  searchLog.resetAllSources();
  searchLog.showSearching();
  searchLog.log(`Starting search: "${query}"`);
  totalResults = 0;

  // Get selected sources
  const selectedCheckboxes = document.querySelectorAll(
    ".source-toggle:checked",
  ) as NodeListOf<HTMLInputElement>;
  const selectedSourceValues = Array.from(selectedCheckboxes).map(
    (cb) => cb.value,
  );

  // All source configurations
  const allSources: SourceConfig[] = [
    { name: "pubmed", endpoint: "/scholar/api/search/pubmed/", maxResults: 50 },
    { name: "arxiv", endpoint: "/scholar/api/search/arxiv/", maxResults: 50 },
    {
      name: "semantic",
      endpoint: "/scholar/api/search/semantic/",
      maxResults: 25,
    },
    {
      name: "crossref",
      endpoint: "/scholar/api/search/crossref/",
      maxResults: 50,
    },
    {
      name: "crossref_local",
      endpoint: "/scholar/api/search/crossref-local/",
      maxResults: 100,
    },
    {
      name: "openalex",
      endpoint: "/scholar/api/search/openalex/",
      maxResults: 50,
    },
  ];

  // Filter to selected sources
  const sourcesToSearch = allSources.filter((source) =>
    selectedSourceValues.includes(source.name),
  );

  if (sourcesToSearch.length === 0) {
    searchLog.log("✗ No sources selected");
    searchLog.hideSearching();
    alert("Please select at least one search source.");
    resetProgressIndicators();
    return;
  }

  searchLog.log(`Querying ${sourcesToSearch.length} sources in parallel...`);
  activeSearches = sourcesToSearch.length;

  // Search each source in parallel
  sourcesToSearch.forEach((source) => {
    searchLog.updateSourceStatus(source.name, "searching");
    searchSource(source, query);
  });

  // Mark unselected sources as idle
  allSources.forEach((source) => {
    if (!selectedSourceValues.includes(source.name)) {
      searchLog.updateSourceStatus(source.name, "idle");
    }
  });
}

/**
 * Check if all searches completed
 */
function checkSearchCompletion(): void {
  activeSearches--;
  if (activeSearches <= 0) {
    searchLog.hideSearching();
    searchLog.log(`✓ Search complete. Total: ${totalResults} results`);
  }
}

/**
 * Search a single source
 */
function searchSource(source: SourceConfig, query: string): void {
  const url = `${source.endpoint}?q=${encodeURIComponent(query)}&max_results=${source.maxResults}`;
  const startTime = Date.now();

  searchLog.log(`→ ${source.name}: Fetching...`);

  fetch(url)
    .then((response) => response.json())
    .then((data: any) => {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

      if (data.status === "success") {
        const count = data.count || (data.results ? data.results.length : 0);
        totalResults += count;

        // Update status panel
        searchLog.updateSourceStatus(source.name, "success", count);
        searchLog.log(`✓ ${source.name}: ${count} results (${elapsed}s)`);

        // Add results
        if (data.results && Array.isArray(data.results)) {
          data.results.forEach((result: SearchResult) => {
            addResultToProgressive(result);
          });
        }
      } else {
        searchLog.updateSourceStatus(source.name, "error");
        searchLog.log(`✗ ${source.name}: ${data.error || "Unknown error"}`);
      }

      checkSearchCompletion();
    })
    .catch((error: Error) => {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      searchLog.updateSourceStatus(source.name, "error");
      searchLog.log(`✗ ${source.name}: ${error.message} (${elapsed}s)`);
      checkSearchCompletion();
    });
}

/**
 * Add a result to the progressive results container
 */
function addResultToProgressive(result: SearchResult): void {
  const progressiveResults = document.getElementById(
    "progressiveResults",
  ) as HTMLElement | null;
  if (!progressiveResults) {
    console.warn("[SciTeX Search] Progressive results container not found");
    return;
  }

  const resultCard = createResultCard(result);
  progressiveResults.appendChild(resultCard);

  // Animate
  resultCard.style.opacity = "0";
  resultCard.style.transform = "translateY(20px)";
  setTimeout(() => {
    resultCard.style.transition = "all 0.3s ease";
    resultCard.style.opacity = "1";
    resultCard.style.transform = "translateY(0)";
  }, 50);
}

/**
 * Create a result card element matching the existing UI style
 */
function createResultCard(result: SearchResult): HTMLElement {
  const cardDiv = document.createElement("div");
  cardDiv.className = "result-card";
  cardDiv.setAttribute("data-paper-id", result.id || "");
  cardDiv.setAttribute("data-title", result.title || "");
  cardDiv.setAttribute("data-authors", result.authors || "");
  cardDiv.setAttribute("data-year", (result.year || "").toString());
  cardDiv.setAttribute("data-journal", result.journal || "");
  cardDiv.setAttribute("data-doi", result.doi || "");

  // Build meta info
  const metaParts: string[] = [];
  if (result.authors) {
    metaParts.push(`<span class="authors">${result.authors}</span>`);
  }
  // Journal + IF as single warning badge
  if (result.journal) {
    const ifText = result.impact_factor ? ` (IF ${result.impact_factor})` : "";
    metaParts.push(`<span class="journal-badge">${result.journal}${ifText}</span>`);
  }
  if (result.citations && result.citations > 0) {
    metaParts.push(`<span class="citations">${result.citations}</span>`);
  }
  // Source badge
  if (result.source) {
    metaParts.push(`<span class="source-badge">${result.source.toUpperCase()}</span>`);
  }

  // Truncate abstract
  let snippet = result.abstract || "";
  if (snippet.length > 150) {
    snippet = snippet.substring(0, 150) + "...";
  }
  if (!snippet) snippet = "...";

  // External URL
  const externalUrl = result.externalUrl || (result.doi ? `https://doi.org/${result.doi}` : "#");

  cardDiv.innerHTML = `
    <div class="result-checkbox">
      <input type="checkbox" class="paper-select" />
    </div>
    <div class="result-content">
      <div class="result-title">
        <a href="${externalUrl}" target="_blank" rel="noopener">${result.title || "Unknown Title"}</a>
      </div>
      <div class="result-meta">
        ${metaParts.join(" · ")}
      </div>
      <div class="result-snippet">${snippet}</div>
    </div>
    <div class="result-right">
      <span class="year-badge">${result.year || "—"}</span>
      <div class="result-actions">
        <button type="button" title="Copy citation" class="cite-btn"><i class="fas fa-quote-left"></i></button>
        <button type="button" title="Save to library" class="save-btn"><i class="fas fa-bookmark"></i></button>
        <button type="button" title="Open external" class="external-btn" onclick="window.open('${externalUrl}', '_blank')"><i class="fas fa-external-link-alt"></i></button>
      </div>
    </div>
  `;

  return cardDiv;
}

/**
 * Reset progress indicators
 */
function resetProgressIndicators(): void {
  searchLog.resetAllSources();
  searchLog.hideSearching();

  // Legacy support for old progress-source elements
  document.querySelectorAll(".progress-source").forEach((source) => {
    const badge = source.querySelector(".badge") as HTMLElement | null;
    const spinner = source.querySelector(
      ".spinner-border",
    ) as HTMLElement | null;
    const count = source.querySelector(".count") as HTMLElement | null;

    if (badge) badge.className = "badge bg-light";
    if (spinner) spinner.style.display = "none";
    if (count) count.textContent = "-";
  });
}

// Note: saveSourcePreferences function is defined in scholar-index-main.ts
// This file assumes it's available in the global scope
