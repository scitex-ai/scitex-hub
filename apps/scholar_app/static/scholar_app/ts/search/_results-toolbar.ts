/**
 * Results Toolbar Module
 *
 * Handles toolbar functionality for search results:
 * - Abstract toggle
 * - Save selected papers
 * - Open URLs
 * - Export BibTeX
 * - Ctrl+C to copy BibTeX
 */

import { PaperData, SearchResult } from "./types";
import { getAllFetchedResults } from "./_pagination";
import { getCurrentSearchQuery } from "./scitex-search";

// Re-export PaperData for backwards compatibility
export type { PaperData };

/**
 * Convert SearchResult to PaperData format
 */
function searchResultToPaperData(result: SearchResult): PaperData {
  const externalUrl =
    result.externalUrl || (result.doi ? `https://doi.org/${result.doi}` : "");
  return {
    title: result.title || "Unknown",
    url: externalUrl,
    authors: result.authors || "",
    journal: result.journal || "",
    year: String(result.year || ""),
    abstract: result.abstract || "",
    doi: result.doi || "",
    source: result.source || "",
    citations: result.citations || 0,
    impactFactor: result.impact_factor
      ? parseFloat(String(result.impact_factor))
      : 0,
  };
}

/**
 * Get all fetched papers as PaperData
 */
export function getAllPapers(): PaperData[] {
  const results = getAllFetchedResults();
  return results.map(searchResultToPaperData);
}

/**
 * Get data from selected paper cards
 */
export function getSelectedPapers(): PaperData[] {
  const selected: PaperData[] = [];
  document.querySelectorAll(".result-card").forEach((card) => {
    // Support both class names: .paper-select (JS-created) and .paper-select-checkbox (HTML template)
    const checkbox = card.querySelector(
      ".paper-select, .paper-select-checkbox",
    ) as HTMLInputElement;
    if (checkbox && checkbox.checked) {
      const cardEl = card as HTMLElement;

      // Support both JS-created cards and HTML template cards
      // JS cards: .result-title a, HTML cards: .result-title-link
      const titleEl = (card.querySelector(".result-title a") ||
        card.querySelector(".result-title-link")) as HTMLAnchorElement;

      // JS cards: .result-meta .authors, HTML cards: .result-authors-inline
      const authors =
        card.querySelector(".result-meta .authors")?.textContent?.trim() ||
        card.querySelector(".result-authors-inline")?.textContent?.trim() ||
        "";

      // JS cards: .journal-badge, HTML cards: .result-journal
      const journal =
        card.querySelector(".journal-badge")?.textContent?.trim() ||
        card.querySelector(".result-journal")?.textContent?.trim() ||
        "";

      // JS cards: .year-badge, HTML cards: .result-year
      const year =
        card.querySelector(".year-badge")?.textContent?.trim() ||
        card.querySelector(".result-year")?.textContent?.trim() ||
        "";

      // JS cards: .result-snippet, HTML cards: .result-abstract
      const snippetEl = (card.querySelector(".result-snippet") ||
        card.querySelector(".result-abstract")) as HTMLElement;

      selected.push({
        title: titleEl?.textContent?.trim() || "Unknown",
        url: titleEl?.href || "",
        authors: authors,
        journal: journal,
        year: year,
        abstract:
          snippetEl?.dataset?.fullAbstract ||
          snippetEl?.textContent?.trim() ||
          "",
        doi: cardEl.dataset?.doi || "",
        source:
          card.querySelector(".source-badge")?.textContent?.trim() ||
          cardEl.dataset?.source ||
          "",
        citations: parseInt(cardEl.dataset?.citations || "0") || 0,
        impactFactor: parseFloat(cardEl.dataset?.impactFactor || "0") || 0,
      });
    }
  });
  return selected;
}

/**
 * Generate a BibTeX key from paper data
 */
export function generateBibtexKey(paper: PaperData): string {
  const firstAuthor =
    (paper.authors || "unknown").split(",")[0].split(" ").pop() || "unknown";
  const year = paper.year || "XXXX";
  const titleWord = (paper.title || "untitled")
    .split(" ")[0]
    .toLowerCase()
    .replace(/[^a-z]/g, "");
  return `${firstAuthor.toLowerCase()}${year}${titleWord}`;
}

/**
 * Generate BibTeX entry for a paper
 */
export function generateBibtexEntry(
  paper: PaperData,
  includeAbstract: boolean = false,
): string {
  const key = generateBibtexKey(paper);
  const authors = paper.authors || "Unknown";
  const title = paper.title || "Unknown";
  const journal = paper.journal?.replace(/\s*\(IF.*\)/, "") || "";
  const year = paper.year || "";
  const doi = paper.doi || "";
  const abstract = paper.abstract || "";
  const citations = paper.citations || 0;
  const impactFactor = paper.impactFactor || 0;

  let entry = `@article{${key},\n`;
  entry += `  author = {${authors}},\n`;
  entry += `  title = {${title}},\n`;
  if (journal) entry += `  journal = {${journal}},\n`;
  if (year) entry += `  year = {${year}},\n`;
  if (doi) entry += `  doi = {${doi}},\n`;
  // Custom fields for metrics (widely supported by reference managers)
  entry += `  citations = {${citations}},\n`;
  entry += `  impactfactor = {${impactFactor.toFixed(1)}},\n`;
  if (includeAbstract && abstract) {
    entry += `  abstract = {${abstract.substring(0, 500)}${abstract.length > 500 ? "..." : ""}},\n`;
  }
  entry += `}`;
  return entry;
}

/**
 * Generate JSON export for papers
 */
export function generateJsonExport(papers: PaperData[]): string {
  return JSON.stringify(papers, null, 2);
}

/**
 * Generate plain text export for papers
 */
export function generateTextExport(papers: PaperData[]): string {
  return papers
    .map((paper, index) => {
      const lines = [`[${index + 1}] ${paper.title || "Unknown"}`];
      if (paper.authors) lines.push(`Authors: ${paper.authors}`);
      if (paper.journal) {
        const journalClean = paper.journal.replace(/\s*\(IF.*\)/, "");
        lines.push(`Journal: ${journalClean}`);
      }
      if (paper.year) lines.push(`Year: ${paper.year}`);
      // Always include metrics for clarity
      lines.push(`Citations: ${paper.citations || 0}`);
      lines.push(`Impact Factor: ${(paper.impactFactor || 0).toFixed(1)}`);
      if (paper.doi) lines.push(`DOI: ${paper.doi}`);
      if (paper.url) lines.push(`URL: ${paper.url}`);
      if (paper.abstract) {
        const truncatedAbstract =
          paper.abstract.length > 300
            ? paper.abstract.substring(0, 300) + "..."
            : paper.abstract;
        lines.push(`Abstract: ${truncatedAbstract}`);
      }
      return lines.join("\n");
    })
    .join("\n\n---\n\n");
}

/**
 * Escape CSV field value (handle quotes and commas)
 */
function escapeCsvField(value: string): string {
  if (!value) return "";
  // If contains comma, newline, or quote, wrap in quotes and escape internal quotes
  if (value.includes(",") || value.includes("\n") || value.includes('"')) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

/**
 * Generate CSV export for papers
 */
export function generateCsvExport(papers: PaperData[]): string {
  const headers = [
    "Title",
    "Authors",
    "Journal",
    "Year",
    "Citations",
    "Impact Factor",
    "DOI",
    "URL",
    "Source",
    "Abstract",
  ];
  const rows = papers.map((paper) => [
    escapeCsvField(paper.title || ""),
    escapeCsvField(paper.authors || ""),
    escapeCsvField(paper.journal?.replace(/\s*\(IF.*\)/, "") || ""),
    escapeCsvField(paper.year || ""),
    escapeCsvField(String(paper.citations || 0)),
    escapeCsvField(paper.impactFactor ? paper.impactFactor.toFixed(1) : "0"),
    escapeCsvField(paper.doi || ""),
    escapeCsvField(paper.url || ""),
    escapeCsvField(paper.source || ""),
    escapeCsvField(paper.abstract || ""),
  ]);

  return [headers.join(","), ...rows.map((row) => row.join(","))].join("\n");
}

/**
 * Export papers in specified format
 * Uses all fetched results (not just rendered ones)
 */
/**
 * Normalize query for filename (lowercase, replace spaces with hyphens, remove special chars)
 */
function normalizeQueryForFilename(query: string): string {
  return query
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "") // Remove special characters
    .replace(/\s+/g, "-") // Replace spaces with hyphens
    .replace(/-+/g, "-") // Collapse multiple hyphens
    .substring(0, 50) // Limit length
    .replace(/^-|-$/g, ""); // Remove leading/trailing hyphens
}

export function exportPapers(format: "bibtex" | "json" | "text" | "csv"): void {
  // Use all fetched results for export (not just rendered/selected)
  const papers = getAllPapers();
  if (papers.length === 0) {
    alert("No search results to export. Please run a search first.");
    return;
  }

  let content: string;
  let filename: string;
  let mimeType: string;

  // Build filename: scitex-scholar-<timestamp>-<normalized-query>.<ext>
  const timestamp = new Date().toISOString().slice(0, 19).replace(/[T:]/g, "-");
  const query = getCurrentSearchQuery();
  const normalizedQuery = normalizeQueryForFilename(query) || "export";
  const baseName = `scitex-scholar-${timestamp}-${normalizedQuery}`;

  switch (format) {
    case "bibtex":
      content = papers.map((p) => generateBibtexEntry(p, true)).join("\n\n");
      filename = `${baseName}.bib`;
      mimeType = "text/plain";
      break;
    case "json":
      content = generateJsonExport(papers);
      filename = `${baseName}.tson`;
      mimeType = "application/json";
      break;
    case "csv":
      content = generateCsvExport(papers);
      filename = `${baseName}.csv`;
      mimeType = "text/csv";
      break;
    case "text":
      content = generateTextExport(papers);
      filename = `${baseName}.txt`;
      mimeType = "text/plain";
      break;
  }

  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Show temporary feedback message
 */
export function showCopyFeedback(message: string): void {
  const existing = document.querySelector(".bibtex-copy-feedback");
  if (existing) existing.remove();

  const feedback = document.createElement("div");
  feedback.className = "bibtex-copy-feedback";
  feedback.textContent = message;
  document.body.appendChild(feedback);

  setTimeout(() => {
    feedback.style.opacity = "0";
    setTimeout(() => feedback.remove(), 300);
  }, 2000);
}

/**
 * Update toolbar button states based on selection and results
 */
export function updateToolbarState(): void {
  // Support both class names: .paper-select (JS-created) and .paper-select-checkbox (HTML template)
  const selectedCount = document.querySelectorAll(
    ".result-card .paper-select:checked, .result-card .paper-select-checkbox:checked",
  ).length;
  const hasResults = document.querySelectorAll(".result-card").length > 0;

  // Update selection-dependent buttons
  const selectionButtons = [
    "openUrlsBtn",
    "exportSelectedBibtex",
    "downloadSelectedPdfs",
  ];
  selectionButtons.forEach((id) => {
    const btn = document.getElementById(id) as HTMLButtonElement;
    if (btn) btn.disabled = selectedCount === 0;
  });

  // Enable abstract toggle when results exist
  const abstractBtn = document.getElementById(
    "abstractToggleBtn",
  ) as HTMLButtonElement;
  if (abstractBtn) abstractBtn.disabled = !hasResults;
}

// Note: Button handlers (abstract toggle, save, open URLs, export) are now
// implemented in toolbar-handlers.ts to avoid duplicate event listeners

/**
 * Initialize selection change listener
 * Called from toolbar-handlers.ts
 */
export function initSelectionListener(): void {
  // Only attach once
  if ((document as any).__selectionListenerAttached) return;
  (document as any).__selectionListenerAttached = true;

  document.addEventListener("change", (e) => {
    const target = e.target as HTMLElement;
    // Handle both class names
    if (
      target.classList.contains("paper-select") ||
      target.classList.contains("paper-select-checkbox")
    ) {
      updateToolbarState();
    }
  });
}

/**
 * Initialize Ctrl+C to copy BibTeX
 * Called from toolbar-handlers.ts
 */
export function initCopyShortcut(): void {
  // Only attach once
  if ((document as any).__copyShortcutAttached) return;
  (document as any).__copyShortcutAttached = true;

  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "c") {
      const selection = window.getSelection();
      if (selection && selection.toString().trim().length > 0) {
        return; // Let browser handle normal text copy
      }

      const papers = getSelectedPapers();
      if (papers.length === 0) {
        return;
      }

      e.preventDefault();
      const bibtexContent = papers
        .map((p) => generateBibtexEntry(p, false))
        .join("\n\n");

      navigator.clipboard
        .writeText(bibtexContent)
        .then(() => {
          showCopyFeedback(
            `Copied ${papers.length.toLocaleString()} BibTeX ${papers.length === 1 ? "entry" : "entries"} to clipboard`,
          );
        })
        .catch((err) => {
          console.error("Failed to copy BibTeX:", err);
        });
    }
  });
}

// Note: Initialization is handled by toolbar-handlers.ts
// Do not auto-initialize here to avoid duplicate handlers
