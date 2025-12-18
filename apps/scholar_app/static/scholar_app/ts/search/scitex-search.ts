/**
 * SciTeX Unified Search Implementation
 *
 * Coordinates the unified search system for SciTeX Scholar that aggregates
 * results from multiple academic sources (PubMed, Google Scholar, arXiv, etc.)
 *
 * @version 2.0.0 - Refactored for modularity
 */

import { searchHistory } from "./SearchHistoryManager";
import { searchLog } from "./SearchLogManager";
import { SearchResult, SourceConfig } from "./types";
import { addResultToProgressive, toggleSelectAll } from "./result-card";
import {
  updateToolbarState,
  getSelectedPapers,
  generateBibtexEntry,
} from "./results-toolbar";

console.log("[DEBUG] scitex-search.ts loaded (refactored)");

// Re-export for backwards compatibility
export {};

// Track active searches for completion detection
let activeSearches = 0;
let totalResults = 0;
let currentSearchQuery = "";

/**
 * Create results header with toolbar buttons
 */
function createResultsHeader(query: string): string {
  return `
    <div class="results-header" id="progressiveResultsHeader">
      <div class="results-info">
        <span class="results-count" id="progressiveResultsText">Searching for "${query}"...</span>
      </div>
      <div class="results-toolbar">
        <button type="button" class="toolbar-btn" id="abstractToggleBtn" data-mode="truncated" title="Toggle abstract display">
          Abstract: truncated
        </button>
        <button type="button" class="toolbar-btn" id="saveSelectedBtn" title="Save selected to library" disabled>
          <i class="fas fa-save"></i> Save
        </button>
        <button type="button" class="toolbar-btn" id="openUrlsBtn" title="Open selected in new tabs" disabled>
          <i class="fas fa-external-link-alt"></i> Open URLs
        </button>
        <button type="button" class="toolbar-btn toolbar-btn--primary" id="exportSelectedBibtex" title="Download BibTeX for selected" disabled>
          <i class="fas fa-download"></i> BibTeX
        </button>
        <button type="button" class="toolbar-btn toolbar-btn--pdf" id="downloadSelectedPdfs" title="Download PDFs for selected (Open Access only)" disabled>
          <i class="fas fa-file-pdf"></i> PDFs
        </button>
      </div>
    </div>
  `;
}

/**
 * Update results count in header
 */
function updateResultsCount(
  count: number,
  query: string,
  sourcesInfo?: string
): void {
  const textEl =
    document.getElementById("progressiveResultsText") ||
    document.getElementById("searchResultsText");
  if (textEl) {
    const sourceText = sourcesInfo ? ` from ${sourcesInfo}` : "";
    textEl.textContent = `${count} result${count !== 1 ? "s" : ""} for "${query}"${sourceText}`;
  }
}

/**
 * Setup keyboard shortcuts for search results
 */
function setupKeyboardShortcuts(): void {
  document.addEventListener("keydown", (e: KeyboardEvent) => {
    // Ctrl+A / Cmd+A to select all cards (only when not in input/textarea)
    if ((e.ctrlKey || e.metaKey) && e.key === "a") {
      const activeEl = document.activeElement;
      const isInInput =
        activeEl?.tagName === "INPUT" || activeEl?.tagName === "TEXTAREA";

      const hasResults = document.querySelectorAll(".result-card").length > 0;
      if (hasResults && !isInInput) {
        e.preventDefault();

        const allCards = document.querySelectorAll(".result-card");
        const selectedCards = document.querySelectorAll(
          ".result-card .paper-select:checked"
        );
        const allSelected =
          allCards.length === selectedCards.length && allCards.length > 0;

        toggleSelectAll(!allSelected);
      }
    }
  });
}

/**
 * Setup toolbar button handlers
 */
function setupToolbarHandlers(): void {
  // Abstract toggle button
  document
    .getElementById("abstractToggleBtn")
    ?.addEventListener("click", function (this: HTMLElement) {
      const modes = ["truncated", "full", "none"];
      const currentMode = this.dataset.mode || "truncated";
      const nextIndex = (modes.indexOf(currentMode) + 1) % modes.length;
      const nextMode = modes[nextIndex];
      this.dataset.mode = nextMode;
      this.textContent =
        "Abstract: " + (nextMode === "none" ? "no" : nextMode);

      document.querySelectorAll(".result-snippet").forEach((el) => {
        const snippetEl = el as HTMLElement;
        if (nextMode === "none") {
          snippetEl.style.display = "none";
        } else if (nextMode === "full") {
          snippetEl.style.display = "block";
          snippetEl.classList.add("expanded");
          snippetEl.dataset.expanded = "true";
        } else {
          snippetEl.style.display = "block";
          snippetEl.classList.remove("expanded");
          snippetEl.dataset.expanded = "false";
        }
      });
    });

  // Save Selected button
  document
    .getElementById("saveSelectedBtn")
    ?.addEventListener("click", function () {
      const papers = getSelectedPapers();
      if (papers.length === 0) {
        alert("No papers selected. Click on papers to select them.");
        return;
      }
      const saved = JSON.parse(
        localStorage.getItem("scitex_saved_papers") || "[]"
      );
      const newPapers = papers.filter(
        (p) => !saved.some((s: { title: string }) => s.title === p.title)
      );
      saved.push(...newPapers);
      localStorage.setItem("scitex_saved_papers", JSON.stringify(saved));
      alert(
        `Saved ${newPapers.length} paper(s) to library. (${papers.length - newPapers.length} already saved)`
      );
    });

  // Open URLs button
  document
    .getElementById("openUrlsBtn")
    ?.addEventListener("click", function () {
      const papers = getSelectedPapers();
      if (papers.length === 0) {
        alert("No papers selected. Click on papers to select them.");
        return;
      }
      if (papers.length > 10) {
        if (
          !confirm(
            `Open ${papers.length} URLs? This may be blocked by your browser.`
          )
        )
          return;
      }
      papers.forEach((paper, i) => {
        if (paper.url && paper.url !== "#") {
          setTimeout(() => window.open(paper.url, "_blank"), i * 100);
        }
      });
    });

  // BibTeX export button
  document
    .getElementById("exportSelectedBibtex")
    ?.addEventListener("click", function () {
      const papers = getSelectedPapers();
      if (papers.length === 0) {
        alert("No papers selected. Click on papers to select them.");
        return;
      }

      const bibtexContent = papers
        .map((p) => generateBibtexEntry(p, true))
        .join("\n\n");
      const blob = new Blob([bibtexContent], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `scitex_export_${new Date().toISOString().slice(0, 10)}.bib`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });

  // PDF download buttons
  setupPdfDownloadHandlers();

  // Fixed action bar handlers
  setupActionBarHandlers();
}

/**
 * Setup PDF download button handlers
 */
function setupPdfDownloadHandlers(): void {
  const handlePdfDownload = async (btn: HTMLButtonElement) => {
    if (window.pdfDownloadManager) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Downloading...';

      const result = await window.pdfDownloadManager.downloadSelected();

      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-file-pdf"></i> PDFs';

      alert(`Downloaded: ${result.success}, Failed: ${result.failed}`);
    } else {
      alert("PDF download not available");
    }
  };

  document
    .getElementById("downloadSelectedPdfs")
    ?.addEventListener("click", function () {
      handlePdfDownload(this as HTMLButtonElement);
    });

  document
    .getElementById("actionDownloadPdfs")
    ?.addEventListener("click", function () {
      handlePdfDownload(this as HTMLButtonElement);
    });
}

/**
 * Setup fixed selection action bar handlers
 */
function setupActionBarHandlers(): void {
  // Save Selected
  document
    .getElementById("actionSaveSelected")
    ?.addEventListener("click", function () {
      const papers = getSelectedPapers();
      if (papers.length === 0) return;
      const saved = JSON.parse(
        localStorage.getItem("scitex_saved_papers") || "[]"
      );
      const newPapers = papers.filter(
        (p) => !saved.some((s: { title: string }) => s.title === p.title)
      );
      saved.push(...newPapers);
      localStorage.setItem("scitex_saved_papers", JSON.stringify(saved));
      alert(
        `Saved ${newPapers.length} paper(s) to library. (${papers.length - newPapers.length} already saved)`
      );
    });

  // Export BibTeX
  document
    .getElementById("actionExportBibtex")
    ?.addEventListener("click", function () {
      const papers = getSelectedPapers();
      if (papers.length === 0) return;

      const bibtexContent = papers
        .map((p) => generateBibtexEntry(p, false))
        .join("\n\n");
      const blob = new Blob([bibtexContent], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `scitex_export_${new Date().toISOString().slice(0, 10)}.bib`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });

  // Open URLs
  document
    .getElementById("actionOpenUrls")
    ?.addEventListener("click", function () {
      const papers = getSelectedPapers();
      if (papers.length === 0) return;
      if (papers.length > 10) {
        if (
          !confirm(
            `Open ${papers.length} URLs? This may be blocked by your browser.`
          )
        )
          return;
      }
      papers.forEach((paper, i) => {
        if (paper.url && paper.url !== "#") {
          setTimeout(() => window.open(paper.url, "_blank"), i * 100);
        }
      });
    });

  // Clear Selection
  document
    .getElementById("actionClearSelection")
    ?.addEventListener("click", function () {
      toggleSelectAll(false);
    });
}

/**
 * Reset progress indicators
 */
function resetProgressIndicators(): void {
  searchLog.resetAllSources();
  searchLog.hideSearching();

  document.querySelectorAll(".progress-source").forEach((source) => {
    const badge = source.querySelector(".badge") as HTMLElement | null;
    const spinner = source.querySelector(".spinner-border") as HTMLElement | null;
    const count = source.querySelector(".count") as HTMLElement | null;

    if (badge) badge.className = "badge bg-light";
    if (spinner) spinner.style.display = "none";
    if (count) count.textContent = "-";
  });
}

/**
 * Check if all searches completed
 */
function checkSearchCompletion(): void {
  activeSearches--;
  updateResultsCount(totalResults, currentSearchQuery);
  if (activeSearches <= 0) {
    searchLog.hideSearching();
    searchLog.log(`✓ Search complete. Total: ${totalResults} results`);
  }
}

/**
 * Search a single source
 */
function searchSource(source: SourceConfig, query: string): void {
  const ignoreCacheToggle = document.getElementById(
    "ignoreCacheToggle"
  ) as HTMLInputElement | null;
  const ignoreCache = ignoreCacheToggle?.checked ? "&ignore_cache=true" : "";
  const cacheNote = ignoreCacheToggle?.checked ? " (no cache)" : "";

  const url = `${source.endpoint}?q=${encodeURIComponent(query)}&max_results=${source.maxResults}${ignoreCache}`;
  const startTime = Date.now();

  searchLog.log(`→ ${source.name}: Fetching${cacheNote}...`);

  fetch(url)
    .then((response) => response.json())
    .then((data: any) => {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

      if (data.status === "success") {
        const count = data.count || (data.results ? data.results.length : 0);
        totalResults += count;
        const cachedNote = data.cached ? " [cached]" : "";

        searchLog.updateSourceStatus(source.name, "success", count);

        let logMessage = `✓ ${source.name}: ${count} results (${elapsed}s)${cachedNote}`;

        const guidance =
          data.result_guidance?.per_source_limits?.[source.name] ||
          data.result_guidance;
        if (guidance?.reason) {
          const reason = guidance.reason;
          const requested = guidance.requested;
          const configuredMax = guidance.configured_max;

          if (reason && (count < requested || count < configuredMax)) {
            logMessage += `\n  ℹ️  ${reason}`;
          }

          if (configuredMax && configuredMax !== requested) {
            logMessage += `\n  📊 Config: max=${configuredMax}, requested=${requested}`;
          }

          if (
            guidance.rate_limit_info &&
            guidance.rate_limit_info !== "Unknown"
          ) {
            logMessage += `\n  🛡️  ${guidance.rate_limit_info}`;
          }
        }

        searchLog.log(logMessage);

        if (data.results && Array.isArray(data.results)) {
          data.results.forEach((result: SearchResult) => {
            addResultToProgressive(result);
          });
        }

        // Log deduplication info
        if (activeSearches === 1 && data.result_guidance?.deduplication) {
          const dedup = data.result_guidance.deduplication;
          if (dedup.removed > 0) {
            setTimeout(() => {
              searchLog.log(
                `\n📌 Deduplication: ${dedup.removed} duplicate(s) removed`
              );
              searchLog.log(`   ${dedup.explanation}`);
            }, 100);
          }
        }

        // Log rate limiting info
        if (activeSearches === 1 && data.result_guidance?.rate_limiting) {
          const rateLimitInfo = data.result_guidance.rate_limiting;
          setTimeout(() => {
            searchLog.log(
              `\n🛡️  Rate Limiting: ${rateLimitInfo.explanation}`
            );
            if (rateLimitInfo.details) {
              searchLog.log(
                `   Remaining: ${rateLimitInfo.details.remaining}/${rateLimitInfo.details.limit} requests`
              );
            }
          }, 200);
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
 * Start unified search across all sources
 */
function startUnifiedSearch(query: string): void {
  console.log("[SciTeX Search] Starting unified search for:", query);

  currentSearchQuery = query;

  searchLog.clear();
  searchLog.resetAllSources();
  searchLog.showSearching();
  searchLog.log(`Starting search: "${query}"`);
  totalResults = 0;

  const selectedCheckboxes = document.querySelectorAll(
    ".source-toggle:checked"
  ) as NodeListOf<HTMLInputElement>;
  const selectedSourceValues = Array.from(selectedCheckboxes).map(
    (cb) => cb.value
  );

  const allSources: SourceConfig[] = [
    { name: "pubmed", endpoint: "/scholar/api/search/pubmed/", maxResults: 50 },
    { name: "arxiv", endpoint: "/scholar/api/search/arxiv/", maxResults: 50 },
    { name: "semantic", endpoint: "/scholar/api/search/semantic/", maxResults: 25 },
    { name: "crossref", endpoint: "/scholar/api/search/crossref/", maxResults: 50 },
    { name: "crossref_local", endpoint: "/scholar/api/search/crossref-local/", maxResults: 100 },
    { name: "openalex", endpoint: "/scholar/api/search/openalex/", maxResults: 50 },
  ];

  const sourcesToSearch = allSources.filter((source) =>
    selectedSourceValues.includes(source.name)
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

  sourcesToSearch.forEach((source) => {
    searchLog.updateSourceStatus(source.name, "searching");
    searchSource(source, query);
  });

  allSources.forEach((source) => {
    if (!selectedSourceValues.includes(source.name)) {
      searchLog.updateSourceStatus(source.name, "idle");
    }
  });
}

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", function () {
  console.log("[SciTeX Search] Initializing unified search system...");

  const searchForm = document.getElementById(
    "literatureSearchForm"
  ) as HTMLFormElement | null;
  const searchInput = document.querySelector(
    'input[name="q"]'
  ) as HTMLInputElement | null;
  const progressiveResults = document.getElementById(
    "progressiveResults"
  ) as HTMLElement | null;

  if (!searchForm || !searchInput) {
    console.log(
      "[SciTeX Search] Search form not found, skipping initialization"
    );
    return;
  }

  // Attach search history to input
  searchHistory.attachToInput(searchInput);

  // Intercept form submission
  searchForm.addEventListener("submit", function (e: Event) {
    e.preventDefault();
    const query = searchInput.value.trim();

    if (query) {
      searchHistory.addQuery(query);
    }

    if (typeof window.saveSourcePreferences === "function") {
      window.saveSourcePreferences();
    }

    // Hide regular results container
    const resultsContainer = document.getElementById("scitex-results-container");
    if (resultsContainer) resultsContainer.style.display = "none";
    document.querySelectorAll(".result-card").forEach((card) => {
      (card as HTMLElement).style.display = "none";
    });
    const emptyState = document.getElementById("searchEmptyState");
    if (emptyState) emptyState.style.display = "none";

    // Show progressive interface
    const progressiveLoadingStatus = document.getElementById(
      "progressiveLoadingStatus"
    ) as HTMLElement | null;
    if (progressiveLoadingStatus)
      progressiveLoadingStatus.style.display = "block";

    if (progressiveResults) {
      progressiveResults.style.display = "block";
      progressiveResults.innerHTML = "";
      const headerHtml = createResultsHeader(query);
      progressiveResults.insertAdjacentHTML("beforeend", headerHtml);
      setupToolbarHandlers();
    }

    // Reset progress indicators
    document.querySelectorAll(".progress-source").forEach((source) => {
      const badge = source.querySelector(".badge") as HTMLElement | null;
      const spinner = source.querySelector(".spinner-border") as HTMLElement | null;
      const count = source.querySelector(".count") as HTMLElement | null;

      if (badge) badge.className = "badge bg-secondary";
      if (spinner) spinner.style.display = "inline-block";
      if (count) count.textContent = "0";
    });

    startUnifiedSearch(query);
  });

  setupKeyboardShortcuts();

  console.log("[SciTeX Search] Initialization complete");
});
