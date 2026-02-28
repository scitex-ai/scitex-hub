/**
 * Scholar Library Tab Manager - Main Orchestrator
 * Manages the library tab functionality: filtering, searching, viewing, editing papers
 * Supports card/table view modes and keyboard navigation
 */

import { LibraryPaper, UpdatePaperData } from "./types";
import { LibraryAPI } from "./api";
import { LibraryFilters } from "./filters";
import { LibraryRenderers } from "./renderers";
class LibraryManager {
  private papers: LibraryPaper[] = [];
  private filteredPapers: LibraryPaper[] = [];
  private selectedPaperId: string | null = null;
  private activeStatusFilter: string | null = null;
  private searchQuery: string = "";

  async initialize(): Promise<void> {
    await this.fetchPapers();
    this.renderStats();
    this.applyFilters();
    this.renderPaperList();
    this.setupEventListeners();
    this.setupImportExport();
    this.setupKeyboardNav();
  }

  private async fetchPapers(): Promise<void> {
    this.papers = await LibraryAPI.fetchPapers();
  }

  private renderStats(): void {
    const stats = LibraryFilters.calculateStats(this.papers);
    LibraryRenderers.renderStats(stats, (filter) =>
      this.setStatusFilter(filter),
    );
  }

  private setStatusFilter(filter: string | null): void {
    this.activeStatusFilter = filter;
    LibraryRenderers.updateActiveStatFilter(filter);
    this.applyFilters();
    this.renderPaperList();
  }

  private applyFilters(): void {
    this.filteredPapers = LibraryFilters.applyFilters(
      this.papers,
      this.activeStatusFilter,
      this.searchQuery,
    );
  }

  private renderPaperList(): void {
    LibraryRenderers.renderPaperList(
      this.filteredPapers,
      this.selectedPaperId,
      this.searchQuery,
      (paperId) => this.selectPaper(paperId),
    );
  }

  private selectPaper(paperId: string): void {
    this.selectedPaperId = paperId;

    // Update selection in card view
    document.querySelectorAll(".library-paper-card").forEach((el) => {
      if (el.getAttribute("data-paper-id") === paperId) {
        el.classList.add("selected");
      } else {
        el.classList.remove("selected");
      }
    });

    const paper = this.papers.find((p) => p.id === paperId);
    if (paper) {
      LibraryRenderers.renderPaperDetails(
        paper,
        () => this.savePaperChanges(paperId),
        () => this.confirmRemovePaper(paperId),
        () => LibraryAPI.exportSinglePaper(paperId),
      );
    }
  }

  private async savePaperChanges(paperId: string): Promise<void> {
    const statusSelect = document.getElementById(
      "library-status-select",
    ) as HTMLSelectElement;
    const importanceSelect = document.getElementById(
      "library-importance-select",
    ) as HTMLSelectElement;
    const tagsInput = document.getElementById(
      "library-tags-input",
    ) as HTMLInputElement;
    const notesTextarea = document.getElementById(
      "library-notes-textarea",
    ) as HTMLTextAreaElement;
    const saveBtn = document.getElementById(
      "library-save-btn",
    ) as HTMLButtonElement;

    if (!statusSelect || !importanceSelect || !tagsInput || !notesTextarea)
      return;

    const data: UpdatePaperData = {
      reading_status: statusSelect.value,
      importance_rating: parseInt(importanceSelect.value, 10),
      tags: tagsInput.value
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
      personal_notes: notesTextarea.value,
    };

    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";

    try {
      await LibraryAPI.updatePaper(paperId, data);

      const paper = this.papers.find((p) => p.id === paperId);
      if (paper) {
        paper.reading_status = data.reading_status;
        paper.importance_rating = data.importance_rating;
        paper.tags = data.tags;
        paper.personal_notes = data.personal_notes;
      }

      this.renderStats();
      this.applyFilters();
      this.renderPaperList();

      saveBtn.textContent = "Saved!";
      setTimeout(() => {
        saveBtn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
        saveBtn.disabled = false;
      }, 1500);
    } catch (error) {
      console.error("Failed to save paper changes:", error);
      alert("Failed to save changes. Please try again.");
      saveBtn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
      saveBtn.disabled = false;
    }
  }

  private confirmRemovePaper(paperId: string): void {
    const paper = this.papers.find((p) => p.id === paperId);
    if (!paper) return;
    this.removePaper(paperId);
  }

  private async removePaper(paperId: string): Promise<void> {
    try {
      await LibraryAPI.removePaper(paperId);

      this.papers = this.papers.filter((p) => p.id !== paperId);
      this.selectedPaperId = null;

      LibraryRenderers.renderEmptyDetailsPanel();
      this.renderStats();
      this.applyFilters();
      this.renderPaperList();
    } catch (error) {
      console.error("Failed to remove paper:", error);
      alert("Failed to remove paper. Please try again.");
    }
  }

  private setupEventListeners(): void {
    const searchInput = document.getElementById(
      "library-search-input",
    ) as HTMLInputElement;
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        this.searchQuery = (e.target as HTMLInputElement).value;
        this.applyFilters();
        this.renderPaperList();
      });
    }

    const refreshBtn = document.getElementById("library-refresh-btn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => this.refreshLibrary());
    }
  }

  private setupImportExport(): void {
    const exportAllBtn = document.getElementById("library-export-all-btn");
    if (exportAllBtn) {
      exportAllBtn.addEventListener("click", () =>
        LibraryAPI.exportAllPapers(),
      );
    }

    const importBtn = document.getElementById("library-import-btn");
    if (importBtn) {
      const fileInput = document.createElement("input");
      fileInput.type = "file";
      fileInput.accept = ".bib";
      fileInput.style.display = "none";
      document.body.appendChild(fileInput);

      fileInput.addEventListener("change", async (e) => {
        const file = (e.target as HTMLInputElement).files?.[0];
        if (file) await this.importBibtexFile(file);
      });

      importBtn.addEventListener("click", () => fileInput.click());
    }
  }

  private setupKeyboardNav(): void {
    const tabLibrary = document.getElementById("tab-library");
    if (!tabLibrary) return;

    tabLibrary.addEventListener("keydown", (e: KeyboardEvent) => {
      // Don't capture if user is typing in an input/textarea/select
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          this.navigatePaper(1);
          break;
        case "ArrowUp":
          e.preventDefault();
          this.navigatePaper(-1);
          break;
        case "Escape":
          e.preventDefault();
          this.selectedPaperId = null;
          LibraryRenderers.renderEmptyDetailsPanel();
          this.renderPaperList();
          break;
      }
    });

    // Make the tab focusable for keyboard events
    tabLibrary.setAttribute("tabindex", "0");
  }

  private navigatePaper(direction: number): void {
    if (this.filteredPapers.length === 0) return;

    const currentIdx = this.filteredPapers.findIndex(
      (p) => p.id === this.selectedPaperId,
    );
    let nextIdx: number;

    if (currentIdx === -1) {
      nextIdx = direction > 0 ? 0 : this.filteredPapers.length - 1;
    } else {
      nextIdx = currentIdx + direction;
      if (nextIdx < 0) nextIdx = 0;
      if (nextIdx >= this.filteredPapers.length)
        nextIdx = this.filteredPapers.length - 1;
    }

    const paper = this.filteredPapers[nextIdx];
    if (paper) {
      this.selectPaper(paper.id);
      // Scroll the selected element into view
      const selector = `[data-paper-id="${paper.id}"]`;
      const el = document.querySelector(selector);
      el?.scrollIntoView({ block: "nearest" });
    }
  }

  private async importBibtexFile(file: File): Promise<void> {
    try {
      const result = await LibraryAPI.importBibtex(file);
      alert(`Successfully imported ${result.imported_count || 0} papers.`);
      await this.refreshLibrary();
    } catch (error) {
      console.error("Failed to import BibTeX:", error);
      alert(
        "Failed to import BibTeX file. Please check the format and try again.",
      );
    }
  }

  async refreshLibrary(): Promise<void> {
    await this.fetchPapers();
    this.renderStats();
    this.applyFilters();
    this.renderPaperList();
  }
}

let _manager: LibraryManager | null = null;

export function initLibraryManager(): void {
  if (_manager) return; // Already initialized
  _manager = new LibraryManager();
  _manager.initialize();

  // Re-fetch papers when navigating back to Library tab
  window.addEventListener("hashchange", () => {
    if (window.location.hash === "#library") {
      _manager?.refreshLibrary();
    }
  });
}
