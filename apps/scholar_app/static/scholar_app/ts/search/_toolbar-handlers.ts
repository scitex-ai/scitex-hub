/**
 * Toolbar handlers for search results
 *
 * Handles abstract toggle, save, export, PDF download, and sorting buttons.
 * Uses data attributes to prevent duplicate event listener attachment.
 */

import {
  getSelectedPapers,
  exportPapers,
  updateToolbarState,
  initSelectionListener,
  initCopyShortcut,
} from "./_results-toolbar";

/**
 * Abstract toggle click handler
 */
function handleAbstractToggle(btn: HTMLElement): void {
  const modes = ["truncated", "full", "none"];
  const currentMode = btn.dataset.mode || "truncated";
  const nextIndex = (modes.indexOf(currentMode) + 1) % modes.length;
  const nextMode = modes[nextIndex];
  btn.dataset.mode = nextMode;
  btn.textContent = "Abstract: " + (nextMode === "none" ? "no" : nextMode);

  document.querySelectorAll(".result-snippet").forEach((el) => {
    const snippetEl = el as HTMLElement;
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
}

/**
 * Sort results client-side
 */
function sortResults(field: string, direction: "asc" | "desc"): void {
  const container = document.getElementById("progressiveResults");
  if (!container) return;

  const cards = Array.from(
    container.querySelectorAll(".result-card"),
  ) as HTMLElement[];
  if (cards.length === 0) return;

  cards.sort((a, b) => {
    let aVal: number = 0;
    let bVal: number = 0;

    switch (field) {
      case "year":
        aVal = parseInt(a.dataset.year || "0") || 0;
        bVal = parseInt(b.dataset.year || "0") || 0;
        break;
      case "citations":
        aVal = parseInt(a.dataset.citations || "0") || 0;
        bVal = parseInt(b.dataset.citations || "0") || 0;
        break;
      case "impact_factor":
        aVal = parseFloat(a.dataset.impactFactor || "0") || 0;
        bVal = parseFloat(b.dataset.impactFactor || "0") || 0;
        break;
      default:
        return 0;
    }

    if (direction === "desc") {
      return bVal > aVal ? 1 : bVal < aVal ? -1 : 0;
    } else {
      return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
    }
  });

  // Re-append in sorted order
  cards.forEach((card) => container.appendChild(card));
}

/**
 * Handle sorter button click - cycle through: none -> desc -> asc -> none
 */
function handleSorterClick(btn: HTMLElement): void {
  const field = btn.dataset.field;
  if (!field) return;

  const currentDir = btn.dataset.direction || "none";
  let nextDir: "none" | "desc" | "asc";

  // Cycle: none -> desc -> asc -> none
  if (currentDir === "none") {
    nextDir = "desc";
  } else if (currentDir === "desc") {
    nextDir = "asc";
  } else {
    nextDir = "none";
  }

  // Reset all other sorter buttons
  document.querySelectorAll(".sort-toggle-btn").forEach((otherBtn) => {
    if (otherBtn !== btn) {
      (otherBtn as HTMLElement).dataset.direction = "none";
      otherBtn.classList.remove("active", "sort-desc", "sort-asc");
      const indicator = otherBtn.querySelector(".sort-indicator");
      if (indicator) indicator.textContent = "";
    }
  });

  // Update this button
  btn.dataset.direction = nextDir;
  btn.classList.remove("active", "sort-desc", "sort-asc");
  const indicator = btn.querySelector(".sort-indicator");

  if (nextDir === "none") {
    if (indicator) indicator.textContent = "";
  } else {
    btn.classList.add("active", `sort-${nextDir}`);
    if (indicator) indicator.textContent = nextDir === "desc" ? " ↓" : " ↑";
    sortResults(field, nextDir);
  }
}

/**
 * Attach handler to element only once (tracked via data attribute)
 */
function attachHandler(
  elementId: string,
  handler: (this: HTMLElement, e: Event) => void,
): void {
  const el = document.getElementById(elementId);
  if (el && !el.dataset.handlerAttached) {
    el.addEventListener("click", handler);
    el.dataset.handlerAttached = "true";
  }
}

/**
 * Setup toolbar button handlers
 */
export function setupToolbarHandlers(): void {
  // Abstract toggle button
  attachHandler("abstractToggleBtn", function (this: HTMLElement) {
    handleAbstractToggle(this);
  });

  // Save Selected button
  attachHandler("saveSelectedBtn", function () {
    const papers = getSelectedPapers();
    if (papers.length === 0) {
      alert("No papers selected. Click on papers to select them.");
      return;
    }
    const saved = JSON.parse(
      localStorage.getItem("scitex_saved_papers") || "[]",
    );
    const newPapers = papers.filter(
      (p) => !saved.some((s: { title: string }) => s.title === p.title),
    );
    saved.push(...newPapers);
    localStorage.setItem("scitex_saved_papers", JSON.stringify(saved));
    alert(
      `Saved ${newPapers.length.toLocaleString()} paper(s) to library. (${(papers.length - newPapers.length).toLocaleString()} already saved)`,
    );
  });

  // Open URLs button
  attachHandler("openUrlsBtn", function () {
    const papers = getSelectedPapers();
    if (papers.length === 0) {
      alert("No papers selected. Click on papers to select them.");
      return;
    }
    if (papers.length > 10) {
      if (
        !confirm(
          `Open ${papers.length.toLocaleString()} URLs? This may be blocked by your browser.`,
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

  // PDF download buttons
  setupPdfDownloadHandlers();

  // Sorter buttons
  setupSorterButtons();

  // Selection change listener (updates toolbar when checkboxes change)
  initSelectionListener();

  // Ctrl+C to copy BibTeX shortcut
  initCopyShortcut();

  // Update button states
  updateToolbarState();
}

/**
 * Setup sorter button handlers
 */
function setupSorterButtons(): void {
  document.querySelectorAll(".sort-toggle-btn").forEach((btn) => {
    const el = btn as HTMLElement;
    if (!el.dataset.handlerAttached) {
      el.addEventListener("click", function () {
        handleSorterClick(this);
      });
      el.dataset.handlerAttached = "true";
    }
  });
}

/**
 * Setup export dropdown with format selection
 */
function setupExportDropdown(buttonId: string): void {
  const btn = document.getElementById(buttonId);
  if (!btn || btn.dataset.dropdownAttached) return;

  // Wrap button in a container for proper dropdown positioning
  const wrapper = document.createElement("div");
  wrapper.className = "export-dropdown-wrapper";
  wrapper.style.position = "relative";
  wrapper.style.display = "inline-block";
  btn.parentElement?.insertBefore(wrapper, btn);
  wrapper.appendChild(btn);

  // Create dropdown menu
  const dropdown = document.createElement("div");
  dropdown.className = "export-format-dropdown";
  dropdown.innerHTML = `
    <button type="button" class="export-format-option" data-format="bibtex">
      <i class="fas fa-file-alt"></i> BibTeX (.bib)
    </button>
    <button type="button" class="export-format-option" data-format="csv">
      <i class="fas fa-table"></i> CSV (.csv)
    </button>
    <button type="button" class="export-format-option" data-format="json">
      <i class="fas fa-code"></i> JSON (.json)
    </button>
    <button type="button" class="export-format-option" data-format="text">
      <i class="fas fa-file-lines"></i> Plain Text (.txt)
    </button>
  `;
  dropdown.style.display = "none";
  wrapper.appendChild(dropdown);
  btn.dataset.dropdownAttached = "true";

  // Toggle dropdown on button click
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    e.preventDefault();

    // Close other dropdowns
    document
      .querySelectorAll(".export-format-dropdown")
      .forEach((d) => ((d as HTMLElement).style.display = "none"));

    dropdown.style.display =
      dropdown.style.display === "none" ? "block" : "none";
  });

  // Format option click handlers
  dropdown.querySelectorAll(".export-format-option").forEach((option) => {
    option.addEventListener("click", (e) => {
      e.stopPropagation();
      e.preventDefault();
      const format = (option as HTMLElement).dataset.format as
        | "bibtex"
        | "csv"
        | "json"
        | "text";
      exportPapers(format);
      dropdown.style.display = "none";
    });
  });

  // Close dropdown on click outside (only add once)
  if (!document.body.dataset.dropdownCloseAttached) {
    document.addEventListener("click", () => {
      document
        .querySelectorAll(".export-format-dropdown")
        .forEach((d) => ((d as HTMLElement).style.display = "none"));
    });
    document.body.dataset.dropdownCloseAttached = "true";
  }
}

/**
 * Setup PDF download button handlers
 */
function setupPdfDownloadHandlers(): void {
  const handlePdfDownload = async (btn: HTMLButtonElement) => {
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

  attachHandler("downloadSelectedPdfs", function () {
    handlePdfDownload(this as HTMLButtonElement);
  });
}

// Initialize handlers on page load
document.addEventListener("DOMContentLoaded", () => {
  setupToolbarHandlers();
});
