/**
 * Result Card Module
 *
 * Handles creation and interaction of search result cards:
 * - Card HTML generation
 * - Selection state management
 * - Click/keyboard handlers
 */
import { updateToolbarState } from "./results-toolbar";
// Debounce toolbar updates to avoid O(n²) DOM queries when adding many cards
let toolbarUpdateTimeout = null;
function debouncedToolbarUpdate() {
    if (toolbarUpdateTimeout)
        clearTimeout(toolbarUpdateTimeout);
    toolbarUpdateTimeout = setTimeout(() => {
        updateToolbarState();
        toolbarUpdateTimeout = null;
    }, 100); // Update at most every 100ms
}
/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
/**
 * Create a result card element
 */
export function createResultCard(result) {
    const cardDiv = document.createElement("div");
    cardDiv.className = "result-card";
    cardDiv.setAttribute("data-paper-id", result.id || "");
    cardDiv.setAttribute("data-title", result.title || "");
    cardDiv.setAttribute("data-authors", result.authors || "");
    cardDiv.setAttribute("data-year", (result.year || "").toString());
    cardDiv.setAttribute("data-journal", result.journal || "");
    cardDiv.setAttribute("data-doi", result.doi || "");
    // Build meta info
    const metaParts = [];
    if (result.authors) {
        metaParts.push(`<span class="authors">${escapeHtml(result.authors)}</span>`);
    }
    // Journal + IF as single warning badge
    if (result.journal) {
        const ifText = result.impact_factor ? ` (IF ${result.impact_factor})` : "";
        metaParts.push(`<span class="journal-badge">${escapeHtml(result.journal)}${ifText}</span>`);
    }
    if (result.citations && result.citations > 0) {
        const formattedCitations = result.citations.toLocaleString();
        metaParts.push(`<span class="citations">${formattedCitations}</span>`);
    }
    // Source badge
    if (result.source) {
        metaParts.push(`<span class="source-badge">${result.source.toUpperCase()}</span>`);
    }
    // PDF status badge
    const isOpenAccess = result.is_open_access ||
        result.source === "arxiv" ||
        result.source === "pmc" ||
        result.source === "biorxiv" ||
        result.source === "doaj" ||
        result.source === "plos";
    const pdfBadgeData = `data-status="unknown" data-doi="${result.doi || ""}" data-arxiv-id="${result.arxivId || ""}" data-pmid="${result.pmid || ""}" data-is-open-access="${isOpenAccess}" data-source="${result.source || ""}" data-pdf-url="${result.pdf_url || ""}"`;
    metaParts.push(`<span class="pdf-status-badge" ${pdfBadgeData} title="PDF status"><i class="fas fa-file-pdf"></i><span class="pdf-status-text">PDF</span></span>`);
    // Abstract
    const fullAbstract = result.abstract || "";
    const hasAbstract = fullAbstract.length > 0;
    // External URL
    const externalUrl = result.externalUrl || (result.doi ? `https://doi.org/${result.doi}` : "#");
    // Build ranking reasons for "why this rank?" hint
    const rankReasons = [];
    if (result.title)
        rankReasons.push("title");
    if (hasAbstract)
        rankReasons.push("abstract");
    if (result.citations && result.citations >= 100)
        rankReasons.push("high citations");
    else if (result.citations && result.citations >= 10)
        rankReasons.push("citations");
    const currentYear = new Date().getFullYear();
    const resultYear = parseInt(String(result.year)) || 0;
    if (resultYear >= currentYear - 2)
        rankReasons.push("recent");
    if (result.impact_factor && parseFloat(String(result.impact_factor)) >= 5)
        rankReasons.push("high IF");
    const rankHint = rankReasons.length > 0 ? `Matches: ${rankReasons.join(" • ")}` : "";
    cardDiv.innerHTML = `
    <div class="result-checkbox">
      <input type="checkbox" class="paper-select" />
    </div>
    <div class="result-content">
      <div class="result-title">
        <a href="${externalUrl}" target="_blank" rel="noopener">${escapeHtml(result.title || "Unknown Title")}</a>
      </div>
      <div class="result-meta">
        ${metaParts.join(" · ")}
      </div>
      <div class="result-snippet ${hasAbstract ? "expandable" : ""}" data-full-abstract="${escapeHtml(fullAbstract)}" data-expanded="false">${hasAbstract ? escapeHtml(fullAbstract) : "..."}</div>
      ${rankHint ? `<div class="result-rank-hint">${rankHint}</div>` : ""}
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
    // Setup abstract expansion handler
    const snippetEl = cardDiv.querySelector(".result-snippet.expandable");
    if (snippetEl) {
        snippetEl.addEventListener("click", (e) => {
            e.stopPropagation(); // Prevent card selection
            const isExpanded = snippetEl.dataset.expanded === "true";
            snippetEl.dataset.expanded = isExpanded ? "false" : "true";
            snippetEl.classList.toggle("expanded", !isExpanded);
        });
    }
    return cardDiv;
}
/**
 * Update card visual state based on selection
 */
export function updateCardSelectedState(card, selected) {
    if (selected) {
        card.classList.add("selected");
    }
    else {
        card.classList.remove("selected");
    }
    updateToolbarState();
}
/**
 * Setup selection handlers for a result card
 */
export function setupCardSelectionHandlers(card) {
    const checkbox = card.querySelector(".paper-select");
    // Click on card body toggles selection (not on checkbox or links)
    card.addEventListener("click", (e) => {
        const target = e.target;
        // Ignore clicks on checkbox, links, and buttons
        if (target.matches("input, a, button") ||
            target.closest("a, button, .result-actions")) {
            return;
        }
        if (checkbox) {
            // Ctrl+click for multi-select, otherwise toggle
            if (!e.ctrlKey && !e.metaKey) {
                // Single click without ctrl - just toggle this card
                checkbox.checked = !checkbox.checked;
            }
            else {
                // Ctrl+click - toggle without deselecting others
                checkbox.checked = !checkbox.checked;
            }
            updateCardSelectedState(card, checkbox.checked);
        }
    });
    // Right-click to deselect
    card.addEventListener("contextmenu", (e) => {
        // Only handle right-click if card is selected
        if (checkbox && checkbox.checked) {
            e.preventDefault();
            checkbox.checked = false;
            updateCardSelectedState(card, false);
        }
    });
    // Checkbox change handler
    if (checkbox) {
        checkbox.addEventListener("change", () => {
            updateCardSelectedState(card, checkbox.checked);
        });
    }
}
/**
 * Add a result to the progressive results container with animation
 */
export function addResultToProgressive(result) {
    const progressiveResults = document.getElementById("progressiveResults");
    if (!progressiveResults) {
        console.warn("[SciTeX Search] Progressive results container not found");
        return;
    }
    const resultCard = createResultCard(result);
    progressiveResults.appendChild(resultCard);
    // Setup selection handlers
    setupCardSelectionHandlers(resultCard);
    // Update toolbar state (debounced to avoid O(n²) queries)
    debouncedToolbarUpdate();
    // Animation disabled for performance - 1997 setTimeout calls was causing 75+ second lag
    // Cards now appear instantly
}
/**
 * Select or deselect all result cards
 */
export function toggleSelectAll(selectAll) {
    document.querySelectorAll(".result-card").forEach((card) => {
        const checkbox = card.querySelector(".paper-select");
        if (checkbox) {
            checkbox.checked = selectAll;
            updateCardSelectedState(card, selectAll);
        }
    });
    updateToolbarState();
}
//# sourceMappingURL=result-card.ts.map
