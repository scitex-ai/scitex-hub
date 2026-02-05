/**
 * Pagination Module for Search Results
 *
 * Handles "Load More" functionality for large result sets.
 * Results are fetched in full but rendered in batches to prevent browser freeze.
 */

import { SearchResult } from "./types";
import { addResultToProgressive } from "./result-card";
import { searchLog } from "./SearchLogManager";
import { RENDER_LIMIT } from "./limit-info-display";

// Pagination state
let allFetchedResults: SearchResult[] = [];
let currentlyRendered = 0;
let isLoading = false;
let infiniteScrollObserver: IntersectionObserver | null = null;

/**
 * Reset pagination state (call at start of new search)
 */
export function resetPagination(): void {
  allFetchedResults = [];
  currentlyRendered = 0;
  isLoading = false;
  if (infiniteScrollObserver) {
    infiniteScrollObserver.disconnect();
    infiniteScrollObserver = null;
  }
  const container = document.getElementById("loadMoreContainer");
  if (container) container.remove();
}

/**
 * Add results to the pagination pool
 */
export function addResultsToPagination(results: SearchResult[]): void {
  allFetchedResults = allFetchedResults.concat(results);
}

/**
 * Render initial batch of results
 * @returns Number of results rendered
 */
export function renderInitialBatch(results: SearchResult[]): number {
  const resultsToRender = results.slice(0, RENDER_LIMIT);
  const remaining = results.length - RENDER_LIMIT;

  resultsToRender.forEach((result: SearchResult) => {
    addResultToProgressive(result);
  });
  currentlyRendered += resultsToRender.length;

  if (remaining > 0) {
    showLoadMoreButton();
  }

  return resultsToRender.length;
}

/**
 * Get count of remaining unrendered results
 */
export function getRemainingCount(): number {
  return allFetchedResults.length - currentlyRendered;
}

/**
 * Get all fetched results (for export all)
 */
export function getAllFetchedResults(): SearchResult[] {
  return allFetchedResults;
}

/**
 * Show "Load More" trigger for infinite scroll pagination
 * Auto-loads when scrolling near the trigger element
 */
export function showLoadMoreButton(): void {
  const progressiveResults = document.getElementById("progressiveResults");
  if (!progressiveResults) return;

  // Remove existing trigger if present
  const existingBtn = document.getElementById("loadMoreContainer");
  if (existingBtn) existingBtn.remove();

  const remaining = allFetchedResults.length - currentlyRendered;
  if (remaining <= 0) return;

  // Create invisible trigger element for infinite scroll
  const loadMoreHtml = `
    <div id="loadMoreContainer" class="load-more-container" style="text-align: center; padding: 1rem; margin-top: 0.5rem;">
      <div id="loadMoreTrigger" class="load-more-trigger" style="color: var(--text-muted); font-size: 0.85rem;">
        <i class="fas fa-spinner fa-spin" style="margin-right: 0.5rem;"></i>
        Loading more... (${remaining.toLocaleString()} remaining)
      </div>
    </div>
  `;
  progressiveResults.insertAdjacentHTML("beforeend", loadMoreHtml);

  // Setup IntersectionObserver for infinite scroll
  setupInfiniteScroll();
}

/**
 * Setup IntersectionObserver for infinite scroll
 */
function setupInfiniteScroll(): void {
  const trigger = document.getElementById("loadMoreTrigger");
  if (!trigger) return;

  // Disconnect previous observer if exists
  if (infiniteScrollObserver) {
    infiniteScrollObserver.disconnect();
  }

  // Create observer that triggers when trigger is 200px from viewport
  infiniteScrollObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && !isLoading) {
          loadMoreResults();
        }
      });
    },
    {
      root: null, // viewport
      rootMargin: "200px", // trigger 200px before reaching
      threshold: 0,
    },
  );

  infiniteScrollObserver.observe(trigger);
}

/**
 * Load more results (pagination)
 */
export function loadMoreResults(): void {
  if (isLoading) return;
  isLoading = true;

  const nextBatch = allFetchedResults.slice(
    currentlyRendered,
    currentlyRendered + RENDER_LIMIT,
  );

  nextBatch.forEach((result: SearchResult) => {
    addResultToProgressive(result);
  });
  currentlyRendered += nextBatch.length;

  // Remove old trigger
  const container = document.getElementById("loadMoreContainer");
  if (container) container.remove();

  isLoading = false;

  const remaining = allFetchedResults.length - currentlyRendered;
  if (remaining > 0) {
    // Show new trigger for next batch
    showLoadMoreButton();
  } else {
    // All loaded - disconnect observer
    if (infiniteScrollObserver) {
      infiniteScrollObserver.disconnect();
      infiniteScrollObserver = null;
    }
  }

  searchLog.log(
    `📄 Loaded ${nextBatch.length.toLocaleString()} more (${currentlyRendered.toLocaleString()}/${allFetchedResults.length.toLocaleString()} shown)`,
  );
}

// EOF
