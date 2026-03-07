/**
 * Toolbar handlers for search results
 *
 * Extracted from scitex-search.ts for maintainability.
 * Handles abstract toggle, save, export, and PDF download buttons.
 */
import { toggleSelectAll } from "./result-card";
import { getSelectedPapers, exportPapers } from "./results-toolbar";
/**
 * Setup toolbar button handlers
 */
export function setupToolbarHandlers() {
  // Abstract toggle button
  document
    .getElementById("abstractToggleBtn")
    ?.addEventListener("click", function () {
      const modes = ["truncated", "full", "none"];
      const currentMode = this.dataset.mode || "truncated";
      const nextIndex = (modes.indexOf(currentMode) + 1) % modes.length;
      const nextMode = modes[nextIndex];
      this.dataset.mode = nextMode;
      this.textContent = "Abstract: " + (nextMode === "none" ? "no" : nextMode);
      document.querySelectorAll(".result-snippet").forEach((el) => {
        const snippetEl = el;
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
        localStorage.getItem("scitex_saved_papers") || "[]",
      );
      const newPapers = papers.filter(
        (p) => !saved.some((s) => s.title === p.title),
      );
      saved.push(...newPapers);
      localStorage.setItem("scitex_saved_papers", JSON.stringify(saved));
      alert(
        `Saved ${newPapers.length} paper(s) to library. (${papers.length - newPapers.length} already saved)`,
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
            `Open ${papers.length} URLs? This may be blocked by your browser.`,
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
  // Export button with format dropdown
  setupExportDropdown("exportSelectedBibtex");
  setupExportDropdown("actionExportBibtex");
  // PDF download buttons
  setupPdfDownloadHandlers();
  // Fixed action bar handlers
  setupActionBarHandlers();
}
/**
 * Setup export dropdown with format selection
 */
function setupExportDropdown(buttonId) {
  const btn = document.getElementById(buttonId);
  if (!btn) return;
  // Create dropdown menu
  const dropdown = document.createElement("div");
  dropdown.className = "export-format-dropdown";
  dropdown.innerHTML = `
    <button type="button" class="export-format-option" data-format="bibtex">
      <i class="fas fa-file-alt"></i> BibTeX (.bib)
    </button>
    <button type="button" class="export-format-option" data-format="json">
      <i class="fas fa-code"></i> JSON (.json)
    </button>
    <button type="button" class="export-format-option" data-format="text">
      <i class="fas fa-file-lines"></i> Plain Text (.txt)
    </button>
  `;
  dropdown.style.display = "none";
  btn.parentElement?.appendChild(dropdown);
  btn.style.position = "relative";
  // Toggle dropdown on button click
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const papers = getSelectedPapers();
    if (papers.length === 0) {
      alert("No papers selected. Click on papers to select them.");
      return;
    }
    // Close other dropdowns
    document
      .querySelectorAll(".export-format-dropdown")
      .forEach((d) => (d.style.display = "none"));
    dropdown.style.display =
      dropdown.style.display === "none" ? "block" : "none";
  });
  // Format option click handlers
  dropdown.querySelectorAll(".export-format-option").forEach((option) => {
    option.addEventListener("click", (e) => {
      e.stopPropagation();
      const format = option.dataset.format;
      exportPapers(format);
      dropdown.style.display = "none";
    });
  });
  // Close dropdown on click outside
  document.addEventListener("click", () => {
    dropdown.style.display = "none";
  });
}
/**
 * Setup PDF download button handlers
 */
function setupPdfDownloadHandlers() {
  const handlePdfDownload = async (btn) => {
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
      handlePdfDownload(this);
    });
  document
    .getElementById("actionDownloadPdfs")
    ?.addEventListener("click", function () {
      handlePdfDownload(this);
    });
}
/**
 * Setup fixed selection action bar handlers
 */
function setupActionBarHandlers() {
  // Save Selected
  document
    .getElementById("actionSaveSelected")
    ?.addEventListener("click", function () {
      const papers = getSelectedPapers();
      if (papers.length === 0) return;
      const saved = JSON.parse(
        localStorage.getItem("scitex_saved_papers") || "[]",
      );
      const newPapers = papers.filter(
        (p) => !saved.some((s) => s.title === p.title),
      );
      saved.push(...newPapers);
      localStorage.setItem("scitex_saved_papers", JSON.stringify(saved));
      alert(
        `Saved ${newPapers.length} paper(s) to library. (${papers.length - newPapers.length} already saved)`,
      );
    });
  // Note: Export button dropdown is set up in setupToolbarHandlers()
  // Open URLs
  document
    .getElementById("actionOpenUrls")
    ?.addEventListener("click", function () {
      const papers = getSelectedPapers();
      if (papers.length === 0) return;
      if (papers.length > 10) {
        if (
          !confirm(
            `Open ${papers.length} URLs? This may be blocked by your browser.`,
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
//# sourceMappingURL=toolbar-handlers.ts.map
