/**
 * Pagination Module for Search Results
 *
 * Handles "Load More" functionality for large result sets.
 * Results are fetched in full but rendered in batches to prevent browser freeze.
 */
import { addResultToProgressive } from "./result-card";
import { searchLog } from "./SearchLogManager";
import { RENDER_LIMIT } from "./limit-info-display";
// Pagination state
let allFetchedResults = [];
let currentlyRendered = 0;
/**
 * Reset pagination state (call at start of new search)
 */
export function resetPagination() {
    allFetchedResults = [];
    currentlyRendered = 0;
    const container = document.getElementById("loadMoreContainer");
    if (container)
        container.remove();
}
/**
 * Add results to the pagination pool
 */
export function addResultsToPagination(results) {
    allFetchedResults = allFetchedResults.concat(results);
}
/**
 * Render initial batch of results
 * @returns Number of results rendered
 */
export function renderInitialBatch(results) {
    const resultsToRender = results.slice(0, RENDER_LIMIT);
    const remaining = results.length - RENDER_LIMIT;
    resultsToRender.forEach((result) => {
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
export function getRemainingCount() {
    return allFetchedResults.length - currentlyRendered;
}
/**
 * Show "Load More" button for pagination
 */
export function showLoadMoreButton() {
    const progressiveResults = document.getElementById("progressiveResults");
    if (!progressiveResults)
        return;
    // Remove existing button if present
    const existingBtn = document.getElementById("loadMoreContainer");
    if (existingBtn)
        existingBtn.remove();
    const remaining = allFetchedResults.length - currentlyRendered;
    if (remaining <= 0)
        return;
    const loadMoreHtml = `
    <div id="loadMoreContainer" class="load-more-container" style="text-align: center; padding: 1rem; margin-top: 1rem;">
      <button id="loadMoreBtn" class="btn btn-outline-primary" type="button">
        Load More (${remaining.toLocaleString()} remaining)
      </button>
    </div>
  `;
    progressiveResults.insertAdjacentHTML("beforeend", loadMoreHtml);
    const loadMoreBtn = document.getElementById("loadMoreBtn");
    loadMoreBtn?.addEventListener("click", loadMoreResults);
}
/**
 * Load more results (pagination)
 */
export function loadMoreResults() {
    const nextBatch = allFetchedResults.slice(currentlyRendered, currentlyRendered + RENDER_LIMIT);
    nextBatch.forEach((result) => {
        addResultToProgressive(result);
    });
    currentlyRendered += nextBatch.length;
    // Remove old button and show new one if more results remain
    const container = document.getElementById("loadMoreContainer");
    if (container)
        container.remove();
    const remaining = allFetchedResults.length - currentlyRendered;
    if (remaining > 0) {
        showLoadMoreButton();
    }
    searchLog.log(`📄 Loaded ${nextBatch.length.toLocaleString()} more (${currentlyRendered.toLocaleString()}/${allFetchedResults.length.toLocaleString()} shown)`);
}
// EOF
//# sourceMappingURL=pagination.ts.map
