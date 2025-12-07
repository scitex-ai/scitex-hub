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

interface PaperData {
  title: string;
  url: string;
  authors: string;
  journal: string;
  year: string;
  abstract: string;
  doi: string;
  source: string;
}

/**
 * Get data from selected paper cards
 */
export function getSelectedPapers(): PaperData[] {
  const selected: PaperData[] = [];
  document.querySelectorAll(".result-card").forEach((card) => {
    const checkbox = card.querySelector(".paper-select") as HTMLInputElement;
    if (checkbox && checkbox.checked) {
      const titleEl = card.querySelector(".result-title a") as HTMLAnchorElement;
      const metaEl = card.querySelector(".result-meta");
      const snippetEl = card.querySelector(".result-snippet") as HTMLElement;
      const yearEl = card.querySelector(".year-badge");

      selected.push({
        title: titleEl?.textContent?.trim() || "Unknown",
        url: titleEl?.href || "",
        authors: metaEl?.querySelector(".authors")?.textContent?.trim() || "",
        journal: metaEl?.querySelector(".journal-badge")?.textContent?.trim() || "",
        year: yearEl?.textContent?.trim() || "",
        abstract: snippetEl?.dataset?.fullAbstract || snippetEl?.textContent?.trim() || "",
        doi: (card as HTMLElement).dataset?.doi || "",
        source: metaEl?.querySelector(".source-badge")?.textContent?.trim() || "",
      });
    }
  });
  return selected;
}

/**
 * Generate a BibTeX key from paper data
 */
export function generateBibtexKey(paper: PaperData): string {
  const firstAuthor = (paper.authors || "unknown").split(",")[0].split(" ").pop() || "unknown";
  const year = paper.year || "XXXX";
  const titleWord = (paper.title || "untitled").split(" ")[0].toLowerCase().replace(/[^a-z]/g, "");
  return `${firstAuthor.toLowerCase()}${year}${titleWord}`;
}

/**
 * Generate BibTeX entry for a paper
 */
export function generateBibtexEntry(paper: PaperData, includeAbstract: boolean = false): string {
  const key = generateBibtexKey(paper);
  const authors = paper.authors || "Unknown";
  const title = paper.title || "Unknown";
  const journal = paper.journal?.replace(/\s*\(IF.*\)/, "") || "";
  const year = paper.year || "";
  const doi = paper.doi || "";
  const abstract = paper.abstract || "";

  let entry = `@article{${key},\n`;
  entry += `  author = {${authors}},\n`;
  entry += `  title = {${title}},\n`;
  if (journal) entry += `  journal = {${journal}},\n`;
  if (year) entry += `  year = {${year}},\n`;
  if (doi) entry += `  doi = {${doi}},\n`;
  if (includeAbstract && abstract) {
    entry += `  abstract = {${abstract.substring(0, 500)}${abstract.length > 500 ? "..." : ""}},\n`;
  }
  entry += `}`;
  return entry;
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
 * Update toolbar button states based on selection
 */
export function updateToolbarState(): void {
  const selectedCount = document.querySelectorAll(".result-card .paper-select:checked").length;
  const buttons = ["saveSelectedBtn", "openUrlsBtn", "exportSelectedBibtex"];
  buttons.forEach((id) => {
    const btn = document.getElementById(id) as HTMLButtonElement;
    if (btn) btn.disabled = selectedCount === 0;
  });
}

/**
 * Initialize abstract toggle button
 */
function initAbstractToggle(): void {
  const btn = document.getElementById("abstractToggleBtn") as HTMLButtonElement;
  btn?.addEventListener("click", function () {
    const modes = ["truncated", "full", "none"];
    const currentMode = this.dataset.mode || "truncated";
    const nextIndex = (modes.indexOf(currentMode) + 1) % modes.length;
    const nextMode = modes[nextIndex];
    this.dataset.mode = nextMode;
    this.textContent = "Abstract: " + (nextMode === "none" ? "no" : nextMode);

    document.querySelectorAll(".result-snippet").forEach((el) => {
      const elem = el as HTMLElement;
      if (nextMode === "none") {
        elem.style.display = "none";
      } else if (nextMode === "full") {
        elem.style.display = "block";
        elem.classList.add("expanded");
        elem.dataset.expanded = "true";
      } else {
        elem.style.display = "block";
        elem.classList.remove("expanded");
        elem.dataset.expanded = "false";
      }
    });
  });
}

/**
 * Initialize save selected button
 */
function initSaveSelected(): void {
  document.getElementById("saveSelectedBtn")?.addEventListener("click", () => {
    const papers = getSelectedPapers();
    if (papers.length === 0) {
      alert("No papers selected. Click on papers to select them.");
      return;
    }
    const saved = JSON.parse(localStorage.getItem("scitex_saved_papers") || "[]");
    const newPapers = papers.filter((p) => !saved.some((s: PaperData) => s.title === p.title));
    saved.push(...newPapers);
    localStorage.setItem("scitex_saved_papers", JSON.stringify(saved));
    alert(`Saved ${newPapers.length} paper(s) to library. (${papers.length - newPapers.length} already saved)`);
  });
}

/**
 * Initialize open URLs button
 */
function initOpenUrls(): void {
  document.getElementById("openUrlsBtn")?.addEventListener("click", () => {
    const papers = getSelectedPapers();
    if (papers.length === 0) {
      alert("No papers selected. Click on papers to select them.");
      return;
    }
    if (papers.length > 10) {
      if (!confirm(`Open ${papers.length} URLs? This may be blocked by your browser.`)) return;
    }
    papers.forEach((paper, i) => {
      if (paper.url && paper.url !== "#") {
        setTimeout(() => window.open(paper.url, "_blank"), i * 100);
      }
    });
  });
}

/**
 * Initialize BibTeX export button
 */
function initBibtexExport(): void {
  document.getElementById("exportSelectedBibtex")?.addEventListener("click", () => {
    const papers = getSelectedPapers();
    if (papers.length === 0) {
      alert("No papers selected. Click on papers to select them.");
      return;
    }

    const bibtexContent = papers.map((p) => generateBibtexEntry(p, true)).join("\n\n");

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
}

/**
 * Initialize Ctrl+C to copy BibTeX
 */
function initCopyShortcut(): void {
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
      const bibtexContent = papers.map((p) => generateBibtexEntry(p, false)).join("\n\n");

      navigator.clipboard
        .writeText(bibtexContent)
        .then(() => {
          showCopyFeedback(`Copied ${papers.length} BibTeX ${papers.length === 1 ? "entry" : "entries"} to clipboard`);
        })
        .catch((err) => {
          console.error("Failed to copy BibTeX:", err);
        });
    }
  });
}

/**
 * Initialize selection change listener
 */
function initSelectionListener(): void {
  document.addEventListener("change", (e) => {
    const target = e.target as HTMLElement;
    if (target.classList.contains("paper-select")) {
      updateToolbarState();
    }
  });
}

/**
 * Initialize all toolbar functionality
 */
export function initResultsToolbar(): void {
  initAbstractToggle();
  initSaveSelected();
  initOpenUrls();
  initBibtexExport();
  initCopyShortcut();
  initSelectionListener();
  updateToolbarState();
}

// Auto-initialize on DOMContentLoaded
document.addEventListener("DOMContentLoaded", initResultsToolbar);
