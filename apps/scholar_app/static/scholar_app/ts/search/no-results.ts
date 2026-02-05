/**
 * No Results Message Module
 *
 * Shows helpful feedback when search returns no results.
 */

import { hideSearchLoading } from "./search-loading";

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Show no results message with query and suggestions
 */
export function showNoResultsMessage(query: string): void {
  const progressiveResults = document.getElementById("progressiveResults");
  if (!progressiveResults) return;

  // Stop loading animation and clear content
  hideSearchLoading();
  progressiveResults.innerHTML = "";

  const noResultsHtml = `
    <div class="no-results-message" style="
      text-align: center;
      padding: 2rem 1rem;
      color: var(--text-muted, #6c8ba0);
    ">
      <i class="fas fa-search" style="font-size: 2.5rem; margin-bottom: 1rem; opacity: 0.4; display: block;"></i>
      <h5 style="color: var(--text-primary, #d4e1e8); margin-bottom: 0.5rem; font-size: 1.1rem;">No results found</h5>
      <p style="margin-bottom: 1.25rem; font-size: 0.9rem;">
        Your search for "<strong style="color: var(--workspace-icon-primary, #059669);">${escapeHtml(query)}</strong>" did not match any papers.
      </p>
      <div style="text-align: left; max-width: 320px; margin: 0 auto; font-size: 0.85rem; background: var(--workspace-bg-secondary, #151515); padding: 0.75rem 1rem; border-radius: 6px; border: 1px solid var(--workspace-border-default, #3a3a3a);">
        <p style="margin-bottom: 0.5rem; font-weight: 500; color: var(--text-secondary, #9ca3af);">Suggestions:</p>
        <ul style="margin: 0; padding-left: 1.25rem; line-height: 1.6; color: var(--text-muted, #6c8ba0);">
          <li>Check your spelling</li>
          <li>Try more general keywords</li>
          <li>Try different keywords</li>
          <li>Remove filters like -ymin, -cmin, -ifmin</li>
        </ul>
      </div>
    </div>
  `;

  progressiveResults.innerHTML = noResultsHtml;
}

/**
 * Clear no results message
 */
export function clearNoResultsMessage(): void {
  const noResultsEl = document.querySelector(".no-results-message");
  if (noResultsEl) {
    noResultsEl.remove();
  }
}
