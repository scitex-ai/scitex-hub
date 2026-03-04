/**
 * Limit Info Display Module
 *
 * Displays limit/cap reasons in the search results UI so users
 * understand why they see a limited number of results.
 */
// Render limit for browser performance (matches scitex-search.ts)
export const RENDER_LIMIT = 100;
/**
 * Format number with commas (e.g., 10000 -> 10,000)
 */
export function formatNumber(n) {
    return n.toLocaleString();
}
/**
 * Update limit info as tooltip on source item (not visible text)
 */
export function updateLimitInfo(sourceName, limitInfoChain, totalAvailable, resultCount) {
    // Build tooltip text from limit info chain
    const tooltipParts = [];
    for (const li of limitInfoChain) {
        if (li.limit_reason) {
            tooltipParts.push(li.limit_reason);
        }
        else if (li.capped && li.capped_reason) {
            tooltipParts.push(li.capped_reason);
        }
        else if (li.total_available && li.returned < li.total_available) {
            tooltipParts.push(`${li.stage}: ${formatNumber(li.returned)} of ${formatNumber(li.total_available)} (limit=${li.configured_limit || "?"})`);
        }
    }
    // Add frontend render limit info if applicable
    if (resultCount && resultCount > RENDER_LIMIT) {
        tooltipParts.push(`Browser: Showing ${RENDER_LIMIT} of ${formatNumber(resultCount)} fetched`);
    }
    // Update tooltip on source item in sidebar
    const sourceItem = document.querySelector(`.source-item[data-source="${sourceName}"]`);
    if (sourceItem && tooltipParts.length > 0) {
        sourceItem.title = tooltipParts.join("\n");
    }
    // Hide the visible limit info element (details now in tooltips)
    const limitInfoEl = document.getElementById("resultsLimitInfo");
    if (limitInfoEl) {
        limitInfoEl.style.display = "none";
    }
}
/**
 * Clear limit info display
 */
export function clearLimitInfo() {
    const limitInfoEl = document.getElementById("resultsLimitInfo");
    if (limitInfoEl) {
        limitInfoEl.innerHTML = "";
        limitInfoEl.style.display = "none";
    }
}
//# sourceMappingURL=limit-info-display.ts.map
