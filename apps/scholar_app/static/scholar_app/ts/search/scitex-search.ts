/**
 * SciTeX Unified Search Implementation
 *
 * Coordinates the unified search system for SciTeX Scholar that aggregates
 * results from multiple academic sources (PubMed, Google Scholar, arXiv, etc.)
 *
 * @version 2.1.0 - Backend as single source of truth for limits
 */

import { searchHistory } from "./_SearchHistoryManager";
import { searchLog } from "./_SearchLogManager";
import { SearchResult, SourceConfig } from "./types";
import { addResultToProgressive, toggleSelectAll } from "./_result-card";
import { setupToolbarHandlers } from "./_toolbar-handlers";
import { updateLimitInfo } from "./_limit-info-display";
import { showNoResultsMessage } from "./_no-results";
import { showSearchLoading } from "./_search-loading";
import {
  resetPagination,
  addResultsToPagination,
  renderInitialBatch,
} from "./_pagination";
import {
  showToolbarStatus,
  hideToolbarStatus,
  updateToolbarStatus,
  updateProgressStep,
  updateSearchStats,
  clearSearchStats,
} from "./_toolbar-status";

console.log("[DEBUG] scitex-search.ts loaded (refactored)");

// Track active searches for completion detection
let activeSearches = 0;
let totalSources = 0;
let completedSources = 0;
let totalResults = 0;
let currentSearchQuery = "";
let searchStartTime = 0;

/**
 * Get current search query (for export filename)
 */
export function getCurrentSearchQuery(): string {
  return currentSearchQuery;
}

/**
 * Update results count in header
 */
function updateResultsCount(
  count: number,
  query: string,
  sourcesInfo?: string,
): void {
  const textEl =
    document.getElementById("progressiveResultsText") ||
    document.getElementById("searchResultsText");
  if (textEl) {
    const sourceText = sourcesInfo ? ` from ${sourcesInfo}` : "";
    textEl.textContent = `${count.toLocaleString()} result${count !== 1 ? "s" : ""} for "${query}"${sourceText}`;
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
          ".result-card .paper-select:checked",
        );
        const allSelected =
          allCards.length === selectedCards.length && allCards.length > 0;

        toggleSelectAll(!allSelected);
      }
    }
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
    const spinner = source.querySelector(
      ".spinner-border",
    ) as HTMLElement | null;
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
  completedSources++;
  updateResultsCount(totalResults, currentSearchQuery);
  updateProgressStep(completedSources, totalSources);

  // Update stats as results come in
  const elapsed = Math.floor((Date.now() - searchStartTime) / 1000);
  updateSearchStats(totalResults, elapsed);

  if (activeSearches <= 0) {
    searchLog.hideSearching();
    searchLog.log(
      `✓ Search complete. Total: ${totalResults.toLocaleString()} results`,
    );
    updateToolbarStatus(`${totalResults.toLocaleString()}`, true);

    // Show no results message if empty
    if (totalResults === 0) {
      showNoResultsMessage(currentSearchQuery);
    } else {
      // Select all papers by default after search completes
      toggleSelectAll(true);
    }
  }
}

/**
 * Build URL for search request
 * maxResults=0 means "use server default" (backend as single source of truth)
 */
function buildSearchUrl(
  source: SourceConfig,
  query: string,
  ignoreCache: boolean,
): string {
  const params = new URLSearchParams();
  params.set("q", query);

  // Only send max_results if explicitly set (non-zero)
  // Zero means "use server default" - backend controls the limit
  if (source.maxResults > 0) {
    params.set("max_results", source.maxResults.toString());
  }

  if (ignoreCache) {
    params.set("ignore_cache", "true");
  }

  return `${source.endpoint}?${params.toString()}`;
}

/**
 * Search a single source
 */
// Timeout for search requests (3 minutes)
const SEARCH_TIMEOUT_MS = 180000;

function searchSource(source: SourceConfig, query: string): void {
  const ignoreCacheToggle = document.getElementById(
    "ignoreCacheToggle",
  ) as HTMLInputElement | null;
  const ignoreCache = ignoreCacheToggle?.checked ?? false;
  const cacheNote = ignoreCache ? " (no cache)" : "";

  const url = buildSearchUrl(source, query, ignoreCache);
  const startTime = Date.now();

  searchLog.log(`→ ${source.name}: Fetching${cacheNote}...`);

  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), SEARCH_TIMEOUT_MS);

  fetch(url, { signal: controller.signal })
    .then((response) => {
      clearTimeout(timeoutId);
      return response.tson();
    })
    .then((data: any) => {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

      if (data.status === "success") {
        const count = data.count || (data.results ? data.results.length : 0);
        totalResults += count;
        const cachedNote = data.cached ? " [cached]" : "";

        searchLog.updateSourceStatus(source.name, "success", count);

        let logMessage = `✓ ${source.name}: ${count.toLocaleString()} results (${elapsed}s)${cachedNote}`;

        // Log limit_info_chain - always show limit reasons from each stage
        if (data.limit_info_chain && Array.isArray(data.limit_info_chain)) {
          data.limit_info_chain.forEach((li: any) => {
            // Show capped warning if capped, otherwise show limit info
            if (li.capped && li.capped_reason) {
              logMessage += `\n  ⚠️  ${li.capped_reason}`;
            } else if (li.limit_reason) {
              logMessage += `\n  📊 ${li.limit_reason}`;
            } else if (li.stage && li.returned !== undefined) {
              // Fallback: construct message from available fields
              const availableText = li.total_available
                ? ` of ${li.total_available} available`
                : "";
              const limitText = li.configured_limit
                ? ` (limit=${li.configured_limit})`
                : "";
              logMessage += `\n  📊 ${li.stage}: ${li.returned}${availableText}${limitText}`;
            }
          });
        }

        // Legacy result_guidance support
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

        // Update visible limit info in header
        if (data.limit_info_chain && Array.isArray(data.limit_info_chain)) {
          updateLimitInfo(
            source.name,
            data.limit_info_chain,
            data.total_available,
            count,
          );
        }

        if (data.results && Array.isArray(data.results)) {
          // Store results for pagination and render initial batch
          addResultsToPagination(data.results);
          const rendered = renderInitialBatch(data.results);
          const remaining = data.results.length - rendered;

          if (remaining > 0) {
            searchLog.log(
              `  📊 Showing first ${rendered.toLocaleString()} of ${data.results.length.toLocaleString()} (${remaining.toLocaleString()} more via "Load More")`,
            );
          }
        }

        // Log deduplication info
        if (activeSearches === 1 && data.result_guidance?.deduplication) {
          const dedup = data.result_guidance.deduplication;
          if (dedup.removed > 0) {
            setTimeout(() => {
              searchLog.log(
                `\n📌 Deduplication: ${dedup.removed} duplicate(s) removed`,
              );
              searchLog.log(`   ${dedup.explanation}`);
            }, 100);
          }
        }

        // Log rate limiting info
        if (activeSearches === 1 && data.result_guidance?.rate_limiting) {
          const rateLimitInfo = data.result_guidance.rate_limiting;
          setTimeout(() => {
            searchLog.log(`\n🛡️  Rate Limiting: ${rateLimitInfo.explanation}`);
            if (rateLimitInfo.details) {
              searchLog.log(
                `   Remaining: ${rateLimitInfo.details.remaining}/${rateLimitInfo.details.limit} requests`,
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
      clearTimeout(timeoutId);
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      searchLog.updateSourceStatus(source.name, "error");
      const errorMsg =
        error.name === "AbortError"
          ? `Timeout after ${SEARCH_TIMEOUT_MS / 1000}s`
          : error.message;
      searchLog.log(`✗ ${source.name}: ${errorMsg} (${elapsed}s)`);
      checkSearchCompletion();
    });
}

/**
 * Source configurations
 * maxResults: 0 = use server default (backend controls limit)
 * maxResults: N = request at most N results
 */
const ALL_SOURCES: SourceConfig[] = [
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
  // Local sources: maxResults=0 means backend controls the limit
  {
    name: "crossref_local",
    endpoint: "/scholar/api/search/crossref-local/",
    maxResults: 0,
  },
  {
    name: "openalex",
    endpoint: "/scholar/api/search/openalex/",
    maxResults: 50,
  },
  {
    name: "openalex_local",
    endpoint: "/scholar/api/search/openalex-local/",
    maxResults: 0,
  },
];

/**
 * Start unified search across all sources
 */
function startUnifiedSearch(query: string): void {
  console.log("[SciTeX Search] Starting unified search for:", query);

  currentSearchQuery = query;
  searchStartTime = Date.now();

  searchLog.clear();
  searchLog.resetAllSources();
  searchLog.showSearching();
  searchLog.log(`Starting search: "${query}"`);
  totalResults = 0;
  clearSearchStats();
  resetPagination();

  const selectedCheckboxes = document.querySelectorAll(
    ".source-toggle:checked",
  ) as NodeListOf<HTMLInputElement>;
  const selectedSourceValues = Array.from(selectedCheckboxes).map(
    (cb) => cb.value,
  );

  const sourcesToSearch = ALL_SOURCES.filter((source) =>
    selectedSourceValues.includes(source.name),
  );

  if (sourcesToSearch.length === 0) {
    searchLog.log("✗ No sources selected");
    searchLog.hideSearching();
    hideToolbarStatus();
    alert("Please select at least one search source.");
    resetProgressIndicators();
    return;
  }

  searchLog.log(`Querying ${sourcesToSearch.length} sources in parallel...`);
  activeSearches = sourcesToSearch.length;
  totalSources = sourcesToSearch.length;
  completedSources = 0;
  // Note: showToolbarStatus is called after header is inserted in form submit handler
  updateProgressStep(0, totalSources);

  sourcesToSearch.forEach((source) => {
    searchLog.updateSourceStatus(source.name, "searching");
    searchSource(source, query);
  });

  ALL_SOURCES.forEach((source) => {
    if (!selectedSourceValues.includes(source.name)) {
      searchLog.updateSourceStatus(source.name, "idle");
    }
  });
}

/**
 * Execute the search flow: hide empty state, show quotes, start search
 */
function executeSearch(searchInput: HTMLInputElement): void {
  const query = searchInput.value.trim();
  if (!query) return;

  console.log("[SciTeX Search] Executing search for:", query);

  searchHistory.addQuery(query);

  if (typeof window.saveSourcePreferences === "function") {
    window.saveSourcePreferences();
  }

  // Keep toolbar visible but clear result cards and empty state
  const resultsHeader = document.getElementById("resultsHeader");
  if (resultsHeader) resultsHeader.style.display = "flex";

  document.querySelectorAll(".result-card").forEach((card) => {
    (card as HTMLElement).style.display = "none";
  });
  const emptyState = document.getElementById("searchEmptyState");
  if (emptyState) emptyState.style.display = "none";

  // Show progressive results container with loading quote
  showSearchLoading();

  // Setup handlers on existing toolbar and start timer
  setupToolbarHandlers();
  showToolbarStatus();

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

  startUnifiedSearch(query);
}

// Initialize search system
function initSearch(): void {
  console.log("[SciTeX Search] Initializing unified search system...");

  const searchForm = document.getElementById(
    "literatureSearchForm",
  ) as HTMLFormElement | null;
  const searchInput = document.querySelector(
    'input[name="q"]',
  ) as HTMLInputElement | null;

  if (!searchForm || !searchInput) {
    console.log(
      "[SciTeX Search] Search form not found, skipping initialization",
    );
    return;
  }

  // Input history (Up/Down, Ctrl+P/N) handled globally by shared/ts/utils/input-history.ts

  // Intercept form submission
  searchForm.addEventListener("submit", function (e: Event) {
    e.preventDefault();
    executeSearch(searchInput);
  });

  // Direct click handler on search button (most reliable path for global Enter handler)
  const searchButton = document.getElementById("searchButton");
  if (searchButton) {
    searchButton.addEventListener("click", function (e: Event) {
      e.preventDefault();
      executeSearch(searchInput);
    });
  }

  setupKeyboardShortcuts();

  console.log("[SciTeX Search] Initialization complete");
}

// Handle both pre- and post-DOMContentLoaded module loading
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initSearch);
} else {
  initSearch();
}
