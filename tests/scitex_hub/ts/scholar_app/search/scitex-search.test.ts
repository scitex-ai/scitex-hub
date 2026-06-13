/**
 * Tests for apps/scholar_app/static/scholar_app/ts/search/scitex-search.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/apps/scholar_app/static/scholar_app/ts/search/scitex-search';

describe('scitex-search', () => {
    beforeEach(() => {
        // Setup before each test
    });

    afterEach(() => {
        // Cleanup after each test
    });

    it.todo('should be implemented');
});

// =============================================================================
// Source Code Reference (auto-generated, do not edit below this line)
// =============================================================================
// Source: apps/scholar_app/static/scholar_app/ts/search/scitex-search.ts
// =============================================================================

// /**
//
//  * SciTeX Unified Search Implementation
//  *
//  * This file implements the unified search system for SciTeX Scholar that aggregates
//  * results from multiple academic sources (PubMed, Google Scholar, arXiv, Semantic Scholar)
//  * and the SciTeX Index. Results are deduplicated, merged, and ranked intelligently.
//  *
//  * @version 1.0.0
//  */
//
// // Window interface for global configuration
//
// console.log(
//   "[DEBUG] apps/scholar_app/static/scholar_app/ts/search/scitex-search.ts loaded",
// );
// declare global {
//   interface Window {
//     SCHOLAR_CONFIG?: {
//       urls?: {
//         search?: string;
//       };
//     };
//     saveSourcePreferences?: () => void;
//     pdfDownloadManager?: {
//       downloadSelected: () => Promise<{ success: number; failed: number }>;
//       initializeBadge: (badge: HTMLElement) => Promise<void>;
//     };
//   }
// }
//
// // Export to make this an ES module
// export {};
//
// /**
//  * Search history manager with arrow key navigation
//  */
// class SearchHistoryManager {
//   private history: string[] = [];
//   private historyIndex: number = -1;
//   private currentInput: string = "";
//   private maxHistory: number = 50;
//   private storageKey: string = "scitex_search_history";
//   private inputElement: HTMLInputElement | null = null;
//
//   constructor() {
//     this.loadFromStorage();
//   }
//
//   private loadFromStorage(): void {
//     try {
//       const stored = localStorage.getItem(this.storageKey);
//       if (stored) {
//         this.history = JSON.parse(stored);
//       }
//     } catch (e) {
//       console.warn("[SearchHistory] Failed to load history:", e);
//       this.history = [];
//     }
//   }
//
//   private saveToStorage(): void {
//     try {
//       localStorage.setItem(this.storageKey, JSON.stringify(this.history));
//     } catch (e) {
//       console.warn("[SearchHistory] Failed to save history:", e);
//     }
//   }
//
//   addQuery(query: string): void {
//     if (!query.trim()) return;
//
//     // Remove duplicates
//     const index = this.history.indexOf(query);
//     if (index !== -1) {
//       this.history.splice(index, 1);
//     }
//
//     // Add to front
//     this.history.unshift(query);
//
//     // Limit history size
//     if (this.history.length > this.maxHistory) {
//       this.history = this.history.slice(0, this.maxHistory);
//     }
//
//     this.saveToStorage();
//     this.historyIndex = -1;
//   }
//
//   attachToInput(input: HTMLInputElement): void {
//     this.inputElement = input;
//
//     input.addEventListener("keydown", (e: KeyboardEvent) => {
//       if (e.key === "ArrowUp") {
//         e.preventDefault();
//         this.navigateHistory(1);
//       } else if (e.key === "ArrowDown") {
//         e.preventDefault();
//         this.navigateHistory(-1);
//       } else if (e.key !== "Enter") {
//         // Reset index when typing (not Enter)
//         this.historyIndex = -1;
//         this.currentInput = input.value;
//       }
//     });
//   }
//
//   private navigateHistory(direction: number): void {
//     if (!this.inputElement || this.history.length === 0) return;
//
//     // Save current input if starting navigation
//     if (this.historyIndex === -1) {
//       this.currentInput = this.inputElement.value;
//     }
//
//     // Calculate new index
//     const newIndex = this.historyIndex + direction;
//
//     if (newIndex < -1) {
//       // Below history, show current input
//       this.historyIndex = -1;
//       this.inputElement.value = this.currentInput;
//     } else if (newIndex >= this.history.length) {
//       // At end of history, stay there
//       return;
//     } else if (newIndex === -1) {
//       // Back to current input
//       this.historyIndex = -1;
//       this.inputElement.value = this.currentInput;
//     } else {
//       // Navigate in history
//       this.historyIndex = newIndex;
//       this.inputElement.value = this.history[this.historyIndex];
//     }
//
//     // Move cursor to end
//     this.inputElement.setSelectionRange(
//       this.inputElement.value.length,
//       this.inputElement.value.length
//     );
//   }
//
//   getHistory(): string[] {
//     return [...this.history];
//   }
//
//   clearHistory(): void {
//     this.history = [];
//     this.historyIndex = -1;
//     this.saveToStorage();
//   }
// }
//
// // Global search history instance
// const searchHistory = new SearchHistoryManager();
//
// /**
//  * Search log manager for status panel
//  */
// class SearchLogManager {
//   private logElement: HTMLElement | null = null;
//   private pulseDot: HTMLElement | null = null;
//
//   constructor() {
//     this.logElement = document.getElementById("searchLog");
//     this.pulseDot = document.getElementById("searchPulseDot");
//     this.setupKeyboardShortcuts();
//   }
//
//   private setupKeyboardShortcuts(): void {
//     if (!this.logElement) return;
//
//     // Make log element focusable
//     this.logElement.setAttribute("tabindex", "0");
//
//     // Ctrl+A to select all text in log when focused
//     this.logElement.addEventListener("keydown", (e: KeyboardEvent) => {
//       if ((e.ctrlKey || e.metaKey) && e.key === "a") {
//         e.preventDefault();
//         this.selectAllText();
//       }
//     });
//   }
//
//   selectAllText(): void {
//     if (!this.logElement) return;
//     const selection = window.getSelection();
//     const range = document.createRange();
//     range.selectNodeContents(this.logElement);
//     selection?.removeAllRanges();
//     selection?.addRange(range);
//   }
//
//   clear(): void {
//     if (this.logElement) {
//       this.logElement.textContent = "";
//     }
//   }
//
//   log(message: string): void {
//     if (this.logElement) {
//       const timestamp = new Date().toLocaleTimeString("en-US", {
//         hour12: false,
//         hour: "2-digit",
//         minute: "2-digit",
//         second: "2-digit",
//       });
//       this.logElement.textContent += `[${timestamp}] ${message}\n`;
//       this.logElement.scrollTop = this.logElement.scrollHeight;
//     }
//   }
//
//   showSearching(): void {
//     if (this.pulseDot) this.pulseDot.style.display = "inline-block";
//   }
//
//   hideSearching(): void {
//     if (this.pulseDot) this.pulseDot.style.display = "none";
//   }
//
//   updateSourceStatus(
//     sourceName: string,
//     status: "searching" | "success" | "error" | "idle",
//     count?: number | string,
//   ): void {
//     // Find source item (now integrated into source-item elements)
//     const item = document.querySelector(
//       `.source-item[data-source="${sourceName}"]`,
//     ) as HTMLElement | null;
//     if (!item) return;
//
//     const spinner = item.querySelector(".spinner-border") as HTMLElement | null;
//     const countEl = item.querySelector(".count") as HTMLElement | null;
//
//     // Update LED indicator
//     const led = document.querySelector(
//       `.search-led[data-source="${sourceName}"]`,
//     ) as HTMLElement | null;
//     if (led) led.dataset.status = status;
//
//     // Reset classes
//     item.classList.remove("searching", "success", "error");
//
//     switch (status) {
//       case "searching":
//         item.classList.add("searching");
//         if (spinner) spinner.style.display = "inline-block";
//         if (countEl) countEl.textContent = "...";
//         break;
//       case "success":
//         item.classList.add("success");
//         if (spinner) spinner.style.display = "none";
//         if (countEl) countEl.textContent = count?.toString() || "0";
//         break;
//       case "error":
//         item.classList.add("error");
//         if (spinner) spinner.style.display = "none";
//         if (countEl) countEl.textContent = "ERR";
//         break;
//       case "idle":
//         if (spinner) spinner.style.display = "none";
//         if (countEl) countEl.textContent = "";
//         break;
//     }
//   }
//
//   resetAllSources(): void {
//     // Reset source items (integrated status)
//     const items = document.querySelectorAll(".source-item[data-source]");
//     items.forEach((item) => {
//       const el = item as HTMLElement;
//       el.classList.remove("searching", "success", "error");
//       const spinner = el.querySelector(".spinner-border") as HTMLElement | null;
//       const count = el.querySelector(".count") as HTMLElement | null;
//       if (spinner) spinner.style.display = "none";
//       if (count) count.textContent = "";
//     });
//
//     // Reset all LED indicators
//     const leds = document.querySelectorAll(".search-led");
//     leds.forEach((led) => {
//       (led as HTMLElement).dataset.status = "idle";
//     });
//   }
// }
//
// const searchLog = new SearchLogManager();
//
// /**
//  * Search result interface
//  */
// interface SearchResult {
//   id?: string;
//   title?: string;
//   authors?: string;
//   year?: string | number;
//   journal?: string;
//   abstract?: string;
//   citations?: number;
//   pmid?: string;
//   doi?: string;
//   arxivId?: string;
//   externalUrl?: string;
//   source?: string;
//   pdf_url?: string;
//   is_open_access?: boolean;
//   impact_factor?: number | string;
// }
//
// /**
//  * Source configuration
//  */
// interface SourceConfig {
//   name: string;
//   endpoint: string;
//   maxResults: number;
// }
//
// /**
//  * Create results header with toolbar buttons
//  */
// function createResultsHeader(query: string): string {
//   return `
//     <div class="results-header" id="progressiveResultsHeader">
//       <div class="results-info">
//         <span class="results-count" id="progressiveResultsText">Searching for "${query}"...</span>
//       </div>
//       <div class="results-toolbar">
//         <button type="button" class="toolbar-btn" id="abstractToggleBtn" data-mode="truncated" title="Toggle abstract display">
//           Abstract: truncated
//         </button>
//         <button type="button" class="toolbar-btn" id="saveSelectedBtn" title="Save selected to library" disabled>
//           <i class="fas fa-save"></i> Save
//         </button>
//         <button type="button" class="toolbar-btn" id="openUrlsBtn" title="Open selected in new tabs" disabled>
//           <i class="fas fa-external-link-alt"></i> Open URLs
//         </button>
//         <button type="button" class="toolbar-btn toolbar-btn--primary" id="exportSelectedBibtex" title="Download BibTeX for selected" disabled>
//           <i class="fas fa-download"></i> BibTeX
//         </button>
//         <button type="button" class="toolbar-btn toolbar-btn--pdf" id="downloadSelectedPdfs" title="Download PDFs for selected (Open Access only)" disabled>
//           <i class="fas fa-file-pdf"></i> PDFs
//         </button>
//       </div>
//     </div>
//   `;
// }
//
// /**
//  * Update results count in header
//  */
// function updateResultsCount(count: number, query: string, sourcesInfo?: string): void {
//   // Try progressive header first (used during search), then static header
//   const textEl = document.getElementById("progressiveResultsText") || document.getElementById("searchResultsText");
//   if (textEl) {
//     const sourceText = sourcesInfo ? ` from ${sourcesInfo}` : "";
//     textEl.textContent = `${count} result${count !== 1 ? "s" : ""} for "${query}"${sourceText}`;
//   }
// }
//
// /**
//  * Get selected papers data from result cards
//  */
// function getSelectedPapers(): Array<{
//   title: string;
//   url: string;
//   authors: string;
//   journal: string;
//   year: string;
//   abstract: string;
//   doi: string;
//   source: string;
// }> {
//   const selected: Array<{
//     title: string;
//     url: string;
//     authors: string;
//     journal: string;
//     year: string;
//     abstract: string;
//     doi: string;
//     source: string;
//   }> = [];
//
//   document.querySelectorAll(".result-card").forEach((card) => {
//     const checkbox = card.querySelector(".paper-select") as HTMLInputElement | null;
//     if (checkbox && checkbox.checked) {
//       const titleEl = card.querySelector(".result-title a") as HTMLAnchorElement | null;
//       const metaEl = card.querySelector(".result-meta") as HTMLElement | null;
//       const snippetEl = card.querySelector(".result-snippet") as HTMLElement | null;
//       const yearEl = card.querySelector(".year-badge") as HTMLElement | null;
//       const cardEl = card as HTMLElement;
//
//       selected.push({
//         title: titleEl?.textContent?.trim() || "Unknown",
//         url: titleEl?.href || "",
//         authors: metaEl?.querySelector(".authors")?.textContent?.trim() || "",
//         journal: metaEl?.querySelector(".journal-badge")?.textContent?.trim() || "",
//         year: yearEl?.textContent?.trim() || "",
//         abstract: snippetEl?.dataset?.fullAbstract || snippetEl?.textContent?.trim() || "",
//         doi: cardEl.dataset?.doi || "",
//         source: metaEl?.querySelector(".source-badge")?.textContent?.trim() || "",
//       });
//     }
//   });
//   return selected;
// }
//
// /**
//  * Generate BibTeX key from paper data
//  */
// function generateBibtexKey(paper: { authors: string; year: string; title: string }): string {
//   const firstAuthor = (paper.authors || "unknown").split(",")[0].split(" ").pop() || "unknown";
//   const year = paper.year || "XXXX";
//   const titleWord = (paper.title || "untitled").split(" ")[0].toLowerCase().replace(/[^a-z]/g, "");
//   return `${firstAuthor.toLowerCase()}${year}${titleWord}`;
// }
//
// /**
//  * Update toolbar button states based on selection
//  */
// function updateToolbarState(): void {
//   const selectedCount = document.querySelectorAll(".result-card .paper-select:checked").length;
//
//   // Update legacy toolbar buttons
//   const buttons = ["saveSelectedBtn", "openUrlsBtn", "exportSelectedBibtex", "downloadSelectedPdfs"];
//   buttons.forEach((id) => {
//     const btn = document.getElementById(id) as HTMLButtonElement | null;
//     if (btn) btn.disabled = selectedCount === 0;
//   });
//
//   // Update fixed selection action bar
//   const actionBar = document.getElementById("selectionActionBar");
//   const countEl = document.getElementById("selectedCount");
//   if (actionBar) {
//     if (selectedCount > 0) {
//       actionBar.classList.add("visible");
//       if (countEl) countEl.textContent = String(selectedCount);
//     } else {
//       actionBar.classList.remove("visible");
//     }
//   }
// }
//
// /**
//  * Select or deselect all result cards
//  */
// function toggleSelectAll(selectAll: boolean): void {
//   document.querySelectorAll(".result-card").forEach((card) => {
//     const checkbox = card.querySelector(".paper-select") as HTMLInputElement | null;
//     if (checkbox) {
//       checkbox.checked = selectAll;
//       updateCardSelectedState(card as HTMLElement, selectAll);
//     }
//   });
//   updateToolbarState();
// }
//
// /**
//  * Setup keyboard shortcuts for search results
//  */
// function setupKeyboardShortcuts(): void {
//   document.addEventListener("keydown", (e: KeyboardEvent) => {
//     // Ctrl+A / Cmd+A to select all cards (only when not in input/textarea)
//     if ((e.ctrlKey || e.metaKey) && e.key === "a") {
//       const activeEl = document.activeElement;
//       const isInInput = activeEl?.tagName === "INPUT" || activeEl?.tagName === "TEXTAREA";
//
//       // Only handle if we have results and not focused on input
//       const hasResults = document.querySelectorAll(".result-card").length > 0;
//       if (hasResults && !isInInput) {
//         e.preventDefault();
//
//         // Toggle: if all selected, deselect all; otherwise select all
//         const allCards = document.querySelectorAll(".result-card");
//         const selectedCards = document.querySelectorAll(".result-card .paper-select:checked");
//         const allSelected = allCards.length === selectedCards.length && allCards.length > 0;
//
//         toggleSelectAll(!allSelected);
//       }
//     }
//   });
// }
//
// /**
//  * Setup toolbar button handlers
//  */
// function setupToolbarHandlers(): void {
//   // Abstract toggle button
//   document.getElementById("abstractToggleBtn")?.addEventListener("click", function (this: HTMLElement) {
//     const modes = ["truncated", "full", "none"];
//     const currentMode = this.dataset.mode || "truncated";
//     const nextIndex = (modes.indexOf(currentMode) + 1) % modes.length;
//     const nextMode = modes[nextIndex];
//     this.dataset.mode = nextMode;
//     this.textContent = "Abstract: " + (nextMode === "none" ? "no" : nextMode);
//
//     document.querySelectorAll(".result-snippet").forEach((el) => {
//       const snippetEl = el as HTMLElement;
//       if (nextMode === "none") {
//         snippetEl.style.display = "none";
//       } else if (nextMode === "full") {
//         snippetEl.style.display = "block";
//         snippetEl.classList.add("expanded");
//         snippetEl.dataset.expanded = "true";
//       } else {
//         snippetEl.style.display = "block";
//         snippetEl.classList.remove("expanded");
//         snippetEl.dataset.expanded = "false";
//       }
//     });
//   });
//
//   // Save Selected button
//   document.getElementById("saveSelectedBtn")?.addEventListener("click", function () {
//     const papers = getSelectedPapers();
//     if (papers.length === 0) {
//       alert("No papers selected. Click on papers to select them.");
//       return;
//     }
//     const saved = JSON.parse(localStorage.getItem("scitex_saved_papers") || "[]");
//     const newPapers = papers.filter((p) => !saved.some((s: { title: string }) => s.title === p.title));
//     saved.push(...newPapers);
//     localStorage.setItem("scitex_saved_papers", JSON.stringify(saved));
//     alert(`Saved ${newPapers.length} paper(s) to library. (${papers.length - newPapers.length} already saved)`);
//   });
//
//   // Open URLs button
//   document.getElementById("openUrlsBtn")?.addEventListener("click", function () {
//     const papers = getSelectedPapers();
//     if (papers.length === 0) {
//       alert("No papers selected. Click on papers to select them.");
//       return;
//     }
//     if (papers.length > 10) {
//       if (!confirm(`Open ${papers.length} URLs? This may be blocked by your browser.`)) return;
//     }
//     papers.forEach((paper, i) => {
//       if (paper.url && paper.url !== "#") {
//         setTimeout(() => window.open(paper.url, "_blank"), i * 100);
//       }
//     });
//   });
//
//   // BibTeX export button
//   document.getElementById("exportSelectedBibtex")?.addEventListener("click", function () {
//     const papers = getSelectedPapers();
//     if (papers.length === 0) {
//       alert("No papers selected. Click on papers to select them.");
//       return;
//     }
//
//     const bibtexEntries = papers.map((paper) => {
//       const key = generateBibtexKey(paper);
//       const authors = paper.authors || "Unknown";
//       const title = paper.title || "Unknown";
//       const journal = paper.journal?.replace(/\s*\(IF.*\)/, "") || "";
//       const year = paper.year || "";
//       const doi = paper.doi || "";
//       const abstract = paper.abstract || "";
//
//       let entry = `@article{${key},\n`;
//       entry += `  author = {${authors}},\n`;
//       entry += `  title = {${title}},\n`;
//       if (journal) entry += `  journal = {${journal}},\n`;
//       if (year) entry += `  year = {${year}},\n`;
//       if (doi) entry += `  doi = {${doi}},\n`;
//       if (abstract) entry += `  abstract = {${abstract.substring(0, 500)}${abstract.length > 500 ? "..." : ""}},\n`;
//       entry += `}`;
//       return entry;
//     });
//
//     const bibtexContent = bibtexEntries.join("\n\n");
//     const blob = new Blob([bibtexContent], { type: "text/plain" });
//     const url = URL.createObjectURL(blob);
//     const a = document.createElement("a");
//     a.href = url;
//     a.download = `scitex_export_${new Date().toISOString().slice(0, 10)}.bib`;
//     document.body.appendChild(a);
//     a.click();
//     document.body.removeChild(a);
//     URL.revokeObjectURL(url);
//   });
//
//   // === Fixed Selection Action Bar Handlers ===
//
//   // Action bar: Save Selected
//   document.getElementById("actionSaveSelected")?.addEventListener("click", function () {
//     const papers = getSelectedPapers();
//     if (papers.length === 0) return;
//     const saved = JSON.parse(localStorage.getItem("scitex_saved_papers") || "[]");
//     const newPapers = papers.filter((p) => !saved.some((s: { title: string }) => s.title === p.title));
//     saved.push(...newPapers);
//     localStorage.setItem("scitex_saved_papers", JSON.stringify(saved));
//     alert(`Saved ${newPapers.length} paper(s) to library. (${papers.length - newPapers.length} already saved)`);
//   });
//
//   // Action bar: Export BibTeX
//   document.getElementById("actionExportBibtex")?.addEventListener("click", function () {
//     const papers = getSelectedPapers();
//     if (papers.length === 0) return;
//
//     const bibtexEntries = papers.map((paper) => {
//       const key = generateBibtexKey(paper);
//       let entry = `@article{${key},\n`;
//       entry += `  author = {${paper.authors || "Unknown"}},\n`;
//       entry += `  title = {${paper.title || "Unknown"}},\n`;
//       if (paper.journal) entry += `  journal = {${paper.journal.replace(/\s*\(IF.*\)/, "")}},\n`;
//       if (paper.year) entry += `  year = {${paper.year}},\n`;
//       if (paper.doi) entry += `  doi = {${paper.doi}},\n`;
//       entry += `}`;
//       return entry;
//     });
//
//     const bibtexContent = bibtexEntries.join("\n\n");
//     const blob = new Blob([bibtexContent], { type: "text/plain" });
//     const url = URL.createObjectURL(blob);
//     const a = document.createElement("a");
//     a.href = url;
//     a.download = `scitex_export_${new Date().toISOString().slice(0, 10)}.bib`;
//     document.body.appendChild(a);
//     a.click();
//     document.body.removeChild(a);
//     URL.revokeObjectURL(url);
//   });
//
//   // Action bar: Open URLs
//   document.getElementById("actionOpenUrls")?.addEventListener("click", function () {
//     const papers = getSelectedPapers();
//     if (papers.length === 0) return;
//     if (papers.length > 10) {
//       if (!confirm(`Open ${papers.length} URLs? This may be blocked by your browser.`)) return;
//     }
//     papers.forEach((paper, i) => {
//       if (paper.url && paper.url !== "#") {
//         setTimeout(() => window.open(paper.url, "_blank"), i * 100);
//       }
//     });
//   });
//
//   // Action bar: Clear Selection
//   document.getElementById("actionClearSelection")?.addEventListener("click", function () {
//     toggleSelectAll(false);
//   });
//
//   // Action bar: Download PDFs button
//   document.getElementById("actionDownloadPdfs")?.addEventListener("click", async function () {
//     if (window.pdfDownloadManager) {
//       const btn = this as HTMLButtonElement;
//       btn.disabled = true;
//       btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Downloading...';
//
//       const result = await window.pdfDownloadManager.downloadSelected();
//
//       btn.disabled = false;
//       btn.innerHTML = '<i class="fas fa-file-pdf"></i> PDFs';
//
//       alert(`Downloaded: ${result.success}, Failed: ${result.failed}`);
//     } else {
//       alert("PDF download not available");
//     }
//   });
//
//   // Toolbar: Download PDFs button
//   document.getElementById("downloadSelectedPdfs")?.addEventListener("click", async function () {
//     if (window.pdfDownloadManager) {
//       const btn = this as HTMLButtonElement;
//       btn.disabled = true;
//       btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Downloading...';
//
//       const result = await window.pdfDownloadManager.downloadSelected();
//
//       btn.disabled = false;
//       btn.innerHTML = '<i class="fas fa-file-pdf"></i> PDFs';
//
//       alert(`Downloaded: ${result.success}, Failed: ${result.failed}`);
//     } else {
//       alert("PDF download not available");
//     }
//   });
// }
//
// // Initialize on DOM ready
// document.addEventListener("DOMContentLoaded", function () {
//   console.log("[SciTeX Search] Initializing unified search system...");
//
//   const searchForm = document.getElementById(
//     "literatureSearchForm",
//   ) as HTMLFormElement | null;
//   const searchInput = document.querySelector(
//     'input[name="q"]',
//   ) as HTMLInputElement | null;
//   const searchButton = document.getElementById(
//     "searchButton",
//   ) as HTMLButtonElement | null;
//   const progressiveResults = document.getElementById(
//     "progressiveResults",
//   ) as HTMLElement | null;
//
//   if (!searchForm || !searchInput) {
//     console.log(
//       "[SciTeX Search] Search form not found, skipping initialization",
//     );
//     return;
//   }
//
//   // Attach search history to input for arrow key navigation
//   searchHistory.attachToInput(searchInput);
//
//   // Intercept form submission
//   searchForm.addEventListener("submit", function (e: Event) {
//     e.preventDefault();
//     const query = searchInput.value.trim();
//
//     // Add to search history
//     if (query) {
//       searchHistory.addQuery(query);
//     }
//
//     // Save current source preferences (defined in scholar-index-main.ts)
//     if (typeof (window as any).saveSourcePreferences === "function") {
//       (window as any).saveSourcePreferences();
//     }
//
//     // Hide regular results container entirely
//     const resultsContainer = document.getElementById("scitex-results-container");
//     if (resultsContainer) resultsContainer.style.display = "none";
//     document.querySelectorAll(".result-card").forEach((card) => {
//       (card as HTMLElement).style.display = "none";
//     });
//     const emptyState = document.getElementById("searchEmptyState");
//     if (emptyState) emptyState.style.display = "none";
//
//     // Show progressive interface
//     const progressiveLoadingStatus = document.getElementById(
//       "progressiveLoadingStatus",
//     ) as HTMLElement | null;
//     if (progressiveLoadingStatus)
//       progressiveLoadingStatus.style.display = "block";
//
//     if (progressiveResults) {
//       progressiveResults.style.display = "block";
//       progressiveResults.innerHTML = "";
//       // Add results header with toolbar to progressive results
//       const headerHtml = createResultsHeader(query);
//       progressiveResults.insertAdjacentHTML("beforeend", headerHtml);
//       // Setup toolbar handlers after header is created
//       setupToolbarHandlers();
//     }
//
//     // Reset progress indicators
//     document.querySelectorAll(".progress-source").forEach((source) => {
//       const badge = source.querySelector(".badge") as HTMLElement | null;
//       const spinner = source.querySelector(
//         ".spinner-border",
//       ) as HTMLElement | null;
//       const count = source.querySelector(".count") as HTMLElement | null;
//
//       if (badge) badge.className = "badge bg-secondary";
//       if (spinner) spinner.style.display = "inline-block";
//       if (count) count.textContent = "0";
//     });
//
//     // Start unified search
//     startUnifiedSearch(query);
//   });
//
//   // Setup keyboard shortcuts (Ctrl+A for select all)
//   setupKeyboardShortcuts();
//
//   console.log("[SciTeX Search] Initialization complete");
// });
//
// // Track active searches for completion detection
// let activeSearches = 0;
// let totalResults = 0;
// let currentSearchQuery = "";
//
// /**
//  * Start unified search across all sources
//  */
// function startUnifiedSearch(query: string): void {
//   console.log("[SciTeX Search] Starting unified search for:", query);
//
//   // Store query for results count update
//   currentSearchQuery = query;
//
//   // Initialize search log
//   searchLog.clear();
//   searchLog.resetAllSources();
//   searchLog.showSearching();
//   searchLog.log(`Starting search: "${query}"`);
//   totalResults = 0;
//
//   // Get selected sources
//   const selectedCheckboxes = document.querySelectorAll(
//     ".source-toggle:checked",
//   ) as NodeListOf<HTMLInputElement>;
//   const selectedSourceValues = Array.from(selectedCheckboxes).map(
//     (cb) => cb.value,
//   );
//
//   // All source configurations
//   const allSources: SourceConfig[] = [
//     { name: "pubmed", endpoint: "/scholar/api/search/pubmed/", maxResults: 50 },
//     { name: "arxiv", endpoint: "/scholar/api/search/arxiv/", maxResults: 50 },
//     {
//       name: "semantic",
//       endpoint: "/scholar/api/search/semantic/",
//       maxResults: 25,
//     },
//     {
//       name: "crossref",
//       endpoint: "/scholar/api/search/crossref/",
//       maxResults: 50,
//     },
//     {
//       name: "crossref_local",
//       endpoint: "/scholar/api/search/crossref-local/",
//       maxResults: 100,
//     },
//     {
//       name: "openalex",
//       endpoint: "/scholar/api/search/openalex/",
//       maxResults: 50,
//     },
//   ];
//
//   // Filter to selected sources
//   const sourcesToSearch = allSources.filter((source) =>
//     selectedSourceValues.includes(source.name),
//   );
//
//   if (sourcesToSearch.length === 0) {
//     searchLog.log("✗ No sources selected");
//     searchLog.hideSearching();
//     alert("Please select at least one search source.");
//     resetProgressIndicators();
//     return;
//   }
//
//   searchLog.log(`Querying ${sourcesToSearch.length} sources in parallel...`);
//   activeSearches = sourcesToSearch.length;
//
//   // Search each source in parallel
//   sourcesToSearch.forEach((source) => {
//     searchLog.updateSourceStatus(source.name, "searching");
//     searchSource(source, query);
//   });
//
//   // Mark unselected sources as idle
//   allSources.forEach((source) => {
//     if (!selectedSourceValues.includes(source.name)) {
//       searchLog.updateSourceStatus(source.name, "idle");
//     }
//   });
// }
//
// /**
//  * Check if all searches completed
//  */
// function checkSearchCompletion(): void {
//   activeSearches--;
//   // Update results count header as results come in
//   updateResultsCount(totalResults, currentSearchQuery);
//   if (activeSearches <= 0) {
//     searchLog.hideSearching();
//     searchLog.log(`✓ Search complete. Total: ${totalResults} results`);
//   }
// }
//
// /**
//  * Search a single source
//  */
// function searchSource(source: SourceConfig, query: string): void {
//   // Check if ignore cache is enabled
//   const ignoreCacheToggle = document.getElementById("ignoreCacheToggle") as HTMLInputElement | null;
//   const ignoreCache = ignoreCacheToggle?.checked ? "&ignore_cache=true" : "";
//   const cacheNote = ignoreCacheToggle?.checked ? " (no cache)" : "";
//
//   const url = `${source.endpoint}?q=${encodeURIComponent(query)}&max_results=${source.maxResults}${ignoreCache}`;
//   const startTime = Date.now();
//
//   searchLog.log(`→ ${source.name}: Fetching${cacheNote}...`);
//
//   fetch(url)
//     .then((response) => response.json())
//     .then((data: any) => {
//       const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
//
//       if (data.status === "success") {
//         const count = data.count || (data.results ? data.results.length : 0);
//         totalResults += count;
//         const cachedNote = data.cached ? " [cached]" : "";
//
//         // Update status panel
//         searchLog.updateSourceStatus(source.name, "success", count);
//
//         // Build detailed log message with guidance
//         let logMessage = `✓ ${source.name}: ${count} results (${elapsed}s)${cachedNote}`;
//
//         // Add result guidance if available
//         // Handle both unified API format (per_source_limits) and individual endpoint format (direct)
//         const guidance = data.result_guidance?.per_source_limits?.[source.name] || data.result_guidance;
//         if (guidance?.reason) {
//           const reason = guidance.reason;
//           const requested = guidance.requested;
//           const configuredMax = guidance.configured_max;
//
//           // Add explanation if results are limited
//           if (reason && (count < requested || count < configuredMax)) {
//             logMessage += `\n  ℹ️  ${reason}`;
//           }
//
//           // Add configured max info
//           if (configuredMax && configuredMax !== requested) {
//             logMessage += `\n  📊 Config: max=${configuredMax}, requested=${requested}`;
//           }
//
//           // Add rate limit info for individual sources
//           if (guidance.rate_limit_info && guidance.rate_limit_info !== "Unknown") {
//             logMessage += `\n  🛡️  ${guidance.rate_limit_info}`;
//           }
//         }
//
//         searchLog.log(logMessage);
//
//         // Add results
//         if (data.results && Array.isArray(data.results)) {
//           data.results.forEach((result: SearchResult) => {
//             addResultToProgressive(result);
//           });
//         }
//
//         // Log deduplication info when all searches complete
//         if (activeSearches === 1 && data.result_guidance?.deduplication) {
//           const dedup = data.result_guidance.deduplication;
//           if (dedup.removed > 0) {
//             setTimeout(() => {
//               searchLog.log(`\n📌 Deduplication: ${dedup.removed} duplicate(s) removed`);
//               searchLog.log(`   ${dedup.explanation}`);
//             }, 100);
//           }
//         }
//
//         // Log rate limiting info
//         if (activeSearches === 1 && data.result_guidance?.rate_limiting) {
//           const rateLimitInfo = data.result_guidance.rate_limiting;
//           setTimeout(() => {
//             searchLog.log(`\n🛡️  Rate Limiting: ${rateLimitInfo.explanation}`);
//             if (rateLimitInfo.details) {
//               searchLog.log(`   Remaining: ${rateLimitInfo.details.remaining}/${rateLimitInfo.details.limit} requests`);
//             }
//           }, 200);
//         }
//       } else {
//         searchLog.updateSourceStatus(source.name, "error");
//         searchLog.log(`✗ ${source.name}: ${data.error || "Unknown error"}`);
//       }
//
//       checkSearchCompletion();
//     })
//     .catch((error: Error) => {
//       const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
//       searchLog.updateSourceStatus(source.name, "error");
//       searchLog.log(`✗ ${source.name}: ${error.message} (${elapsed}s)`);
//       checkSearchCompletion();
//     });
// }
//
// /**
//  * Add a result to the progressive results container
//  */
// function addResultToProgressive(result: SearchResult): void {
//   const progressiveResults = document.getElementById(
//     "progressiveResults",
//   ) as HTMLElement | null;
//   if (!progressiveResults) {
//     console.warn("[SciTeX Search] Progressive results container not found");
//     return;
//   }
//
//   const resultCard = createResultCard(result);
//   progressiveResults.appendChild(resultCard);
//
//   // Setup selection handlers
//   setupCardSelectionHandlers(resultCard);
//
//   // Update toolbar state (buttons become enabled when results are available)
//   updateToolbarState();
//
//   // Animate
//   resultCard.style.opacity = "0";
//   resultCard.style.transform = "translateY(20px)";
//   setTimeout(() => {
//     resultCard.style.transition = "all 0.3s ease";
//     resultCard.style.opacity = "1";
//     resultCard.style.transform = "translateY(0)";
//   }, 50);
// }
//
// /**
//  * Setup selection handlers for a result card
//  */
// function setupCardSelectionHandlers(card: HTMLElement): void {
//   const checkbox = card.querySelector(".paper-select") as HTMLInputElement | null;
//
//   // Click on card body toggles selection (not on checkbox or links)
//   card.addEventListener("click", (e: MouseEvent) => {
//     const target = e.target as HTMLElement;
//     // Ignore clicks on checkbox, links, and buttons
//     if (
//       target.matches("input, a, button") ||
//       target.closest("a, button, .result-actions")
//     ) {
//       return;
//     }
//
//     if (checkbox) {
//       // Ctrl+click for multi-select, otherwise toggle
//       if (!e.ctrlKey && !e.metaKey) {
//         // Single click without ctrl - just toggle this card
//         checkbox.checked = !checkbox.checked;
//       } else {
//         // Ctrl+click - toggle without deselecting others
//         checkbox.checked = !checkbox.checked;
//       }
//       updateCardSelectedState(card, checkbox.checked);
//     }
//   });
//
//   // Right-click to deselect
//   card.addEventListener("contextmenu", (e: MouseEvent) => {
//     // Only handle right-click if card is selected
//     if (checkbox && checkbox.checked) {
//       e.preventDefault();
//       checkbox.checked = false;
//       updateCardSelectedState(card, false);
//     }
//   });
//
//   // Checkbox change handler
//   if (checkbox) {
//     checkbox.addEventListener("change", () => {
//       updateCardSelectedState(card, checkbox.checked);
//     });
//   }
// }
//
// /**
//  * Update card visual state based on selection
//  */
// function updateCardSelectedState(card: HTMLElement, selected: boolean): void {
//   if (selected) {
//     card.classList.add("selected");
//   } else {
//     card.classList.remove("selected");
//   }
//   // Update toolbar button states
//   updateToolbarState();
// }
//
// /**
//  * Create a result card element matching the existing UI style
//  */
// function createResultCard(result: SearchResult): HTMLElement {
//   const cardDiv = document.createElement("div");
//   cardDiv.className = "result-card";
//   cardDiv.setAttribute("data-paper-id", result.id || "");
//   cardDiv.setAttribute("data-title", result.title || "");
//   cardDiv.setAttribute("data-authors", result.authors || "");
//   cardDiv.setAttribute("data-year", (result.year || "").toString());
//   cardDiv.setAttribute("data-journal", result.journal || "");
//   cardDiv.setAttribute("data-doi", result.doi || "");
//
//   // Build meta info
//   const metaParts: string[] = [];
//   if (result.authors) {
//     metaParts.push(`<span class="authors">${result.authors}</span>`);
//   }
//   // Journal + IF as single warning badge
//   if (result.journal) {
//     const ifText = result.impact_factor ? ` (IF ${result.impact_factor})` : "";
//     metaParts.push(`<span class="journal-badge">${result.journal}${ifText}</span>`);
//   }
//   if (result.citations && result.citations > 0) {
//     const formattedCitations = result.citations.toLocaleString();
//     metaParts.push(`<span class="citations">${formattedCitations}</span>`);
//   }
//   // Source badge
//   if (result.source) {
//     metaParts.push(`<span class="source-badge">${result.source.toUpperCase()}</span>`);
//   }
//
//   // PDF status badge - include is_open_access and source for better detection
//   const isOpenAccess = result.is_open_access || result.source === 'arxiv' || result.source === 'pmc' || result.source === 'biorxiv' || result.source === 'doaj' || result.source === 'plos';
//   const pdfBadgeData = `data-status="unknown" data-doi="${result.doi || ''}" data-arxiv-id="${result.arxivId || ''}" data-pmid="${result.pmid || ''}" data-is-open-access="${isOpenAccess}" data-source="${result.source || ''}" data-pdf-url="${result.pdf_url || ''}"`;
//   metaParts.push(`<span class="pdf-status-badge" ${pdfBadgeData} title="PDF status"><i class="fas fa-file-pdf"></i><span class="pdf-status-text">PDF</span></span>`);
//
//   // Abstract - store full text for expansion
//   const fullAbstract = result.abstract || "";
//   const hasAbstract = fullAbstract.length > 0;
//
//   // External URL
//   const externalUrl = result.externalUrl || (result.doi ? `https://doi.org/${result.doi}` : "#");
//
//   // Escape HTML in abstract to prevent XSS
//   const escapeHtml = (text: string): string => {
//     const div = document.createElement('div');
//     div.textContent = text;
//     return div.innerHTML;
//   };
//
//   // Build ranking reasons for "why this rank?" hint
//   const rankReasons: string[] = [];
//   if (result.title) rankReasons.push("title");
//   if (hasAbstract) rankReasons.push("abstract");
//   if (result.citations && result.citations >= 100) rankReasons.push("high citations");
//   else if (result.citations && result.citations >= 10) rankReasons.push("citations");
//   const currentYear = new Date().getFullYear();
//   const resultYear = parseInt(String(result.year)) || 0;
//   if (resultYear >= currentYear - 2) rankReasons.push("recent");
//   if (result.impact_factor && parseFloat(String(result.impact_factor)) >= 5) rankReasons.push("high IF");
//
//   const rankHint = rankReasons.length > 0 ? `Matches: ${rankReasons.join(" • ")}` : "";
//
//   cardDiv.innerHTML = `
//     <div class="result-checkbox">
//       <input type="checkbox" class="paper-select" />
//     </div>
//     <div class="result-content">
//       <div class="result-title">
//         <a href="${externalUrl}" target="_blank" rel="noopener">${result.title || "Unknown Title"}</a>
//       </div>
//       <div class="result-meta">
//         ${metaParts.join(" · ")}
//       </div>
//       <div class="result-snippet ${hasAbstract ? 'expandable' : ''}" data-full-abstract="${escapeHtml(fullAbstract)}" data-expanded="false">${hasAbstract ? escapeHtml(fullAbstract) : '...'}</div>
//       ${rankHint ? `<div class="result-rank-hint">${rankHint}</div>` : ''}
//     </div>
//     <div class="result-right">
//       <span class="year-badge">${result.year || "—"}</span>
//       <div class="result-actions">
//         <button type="button" title="Copy citation" class="cite-btn"><i class="fas fa-quote-left"></i></button>
//         <button type="button" title="Save to library" class="save-btn"><i class="fas fa-bookmark"></i></button>
//         <button type="button" title="Open external" class="external-btn" onclick="window.open('${externalUrl}', '_blank')"><i class="fas fa-external-link-alt"></i></button>
//       </div>
//     </div>
//   `;
//
//   // Setup abstract expansion handler
//   const snippetEl = cardDiv.querySelector('.result-snippet.expandable') as HTMLElement | null;
//   if (snippetEl) {
//     snippetEl.addEventListener('click', (e: MouseEvent) => {
//       e.stopPropagation(); // Prevent card selection
//       const isExpanded = snippetEl.dataset.expanded === 'true';
//       snippetEl.dataset.expanded = isExpanded ? 'false' : 'true';
//       snippetEl.classList.toggle('expanded', !isExpanded);
//     });
//   }
//
//   return cardDiv;
// }
//
// /**
//  * Reset progress indicators
//  */
// function resetProgressIndicators(): void {
//   searchLog.resetAllSources();
//   searchLog.hideSearching();
//
//   // Legacy support for old progress-source elements
//   document.querySelectorAll(".progress-source").forEach((source) => {
//     const badge = source.querySelector(".badge") as HTMLElement | null;
//     const spinner = source.querySelector(
//       ".spinner-border",
//     ) as HTMLElement | null;
//     const count = source.querySelector(".count") as HTMLElement | null;
//
//     if (badge) badge.className = "badge bg-light";
//     if (spinner) spinner.style.display = "none";
//     if (count) count.textContent = "-";
//   });
// }
//
// // Note: saveSourcePreferences function is defined in scholar-index-main.ts
// // This file assumes it's available in the global scope

// =============================================================================
// End of Source Code
// =============================================================================
