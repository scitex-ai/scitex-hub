/**
 * Scholar Library Tab Manager - Main Orchestrator
 * Manages the library tab functionality: filtering, searching, viewing, editing papers
 * Supports card/table view modes, collection sidebar, and keyboard navigation
 */

import {
  LibraryCollection,
  LibraryPaper,
  UpdatePaperData,
  ViewMode,
} from "./types";
import { LibraryAPI } from "./api";
import { LibraryFilters } from "./filters";
import { LibraryRenderers } from "./renderers";
import {
  startInspiringSpinner,
  type SpinnerHandle,
} from "../../../../../../static/shared/ts/components/inspiring-spinner";

class LibraryManager {
  private papers: LibraryPaper[] = [];
  private filteredPapers: LibraryPaper[] = [];
  private selectedPaperId: string | null = null;
  private activeStatusFilter: string | null = null;
  private searchQuery: string = "";
  private loadingSpinner: SpinnerHandle | null = null;

  // View mode
  private viewMode: ViewMode = "table";

  // Collections
  private collections: LibraryCollection[] = [];
  private selectedCollectionId: string | null = null;

  // Table sorting
  private sortColumn: string = "title";
  private sortAsc: boolean = true;

  async initialize(): Promise<void> {
    const loadingEl = document.getElementById("library-loading");
    if (loadingEl) {
      this.loadingSpinner = startInspiringSpinner(
        loadingEl,
        "Loading papers...",
      );
    }
    await Promise.all([this.fetchPapers(), this.fetchCollections()]);
    this.loadingSpinner?.stop();
    this.loadingSpinner = null;
    this.renderStats();
    this.renderCollectionSidebar();
    this.applyFilters();
    this.renderPaperList();
    this.setupEventListeners();
    this.setupImportExport();
    this.setupViewToggle();
    this.setupKeyboardNav();
  }

  private async fetchPapers(): Promise<void> {
    this.papers = await LibraryAPI.fetchPapers();
  }

  private async fetchCollections(): Promise<void> {
    this.collections = await LibraryAPI.fetchCollections();
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
    let papers = LibraryFilters.applyFilters(
      this.papers,
      this.activeStatusFilter,
      this.searchQuery,
    );

    // Filter by collection
    if (this.selectedCollectionId) {
      papers = papers.filter(
        (p) =>
          p.collection_ids &&
          p.collection_ids.includes(this.selectedCollectionId!),
      );
    }

    this.filteredPapers = papers;
  }

  private renderPaperList(): void {
    // Apply table sorting if in table mode
    if (this.viewMode === "table") {
      this.sortFilteredPapers();
      LibraryRenderers.renderPaperTable(
        this.filteredPapers,
        this.selectedPaperId,
        this.searchQuery,
        (paperId) => this.selectPaper(paperId),
        (column) => this.handleTableSort(column),
        this.sortColumn,
        this.sortAsc,
      );
    } else {
      LibraryRenderers.renderPaperList(
        this.filteredPapers,
        this.selectedPaperId,
        this.searchQuery,
        (paperId) => this.selectPaper(paperId),
      );
    }
  }

  private renderCollectionSidebar(): void {
    LibraryRenderers.renderCollectionSidebar(
      this.collections,
      this.selectedCollectionId,
      this.papers.length,
      (collectionId) => this.selectCollection(collectionId),
    );
  }

  private selectCollection(collectionId: string | null): void {
    this.selectedCollectionId = collectionId;
    this.renderCollectionSidebar();
    this.applyFilters();
    this.renderPaperList();
  }

  private handleTableSort(column: string): void {
    if (this.sortColumn === column) {
      this.sortAsc = !this.sortAsc;
    } else {
      this.sortColumn = column;
      this.sortAsc = true;
    }
    this.renderPaperList();
  }

  private sortFilteredPapers(): void {
    const col = this.sortColumn;
    const asc = this.sortAsc;
    this.filteredPapers.sort((a, b) => {
      let cmp = 0;
      switch (col) {
        case "title":
          cmp = (a.title || "").localeCompare(b.title || "");
          break;
        case "authors":
          cmp = (a.authors || "").localeCompare(b.authors || "");
          break;
        case "year":
          cmp = (a.year || 0) - (b.year || 0);
          break;
        case "journal":
          cmp = (a.journal || "").localeCompare(b.journal || "");
          break;
        case "reading_status":
          cmp = (a.reading_status || "").localeCompare(b.reading_status || "");
          break;
        case "importance_rating":
          cmp = (a.importance_rating || 0) - (b.importance_rating || 0);
          break;
      }
      return asc ? cmp : -cmp;
    });
  }

  private selectPaper(paperId: string): void {
    this.selectedPaperId = paperId;

    // Update selection in both card and table views
    document
      .querySelectorAll(".library-paper-card, .library-table-row")
      .forEach((el) => {
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
      this.renderCollectionSidebar();
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
    const fileInput = document.getElementById(
      "bibtex-file-input",
    ) as HTMLInputElement | null;
    if (importBtn && fileInput) {
      fileInput.addEventListener("change", async (e) => {
        const file = (e.target as HTMLInputElement).files?.[0];
        if (file) await this.importBibtexFile(file);
      });
      importBtn.addEventListener("click", () => fileInput.click());
    }
  }

  private setupViewToggle(): void {
    const tableBtn = document.getElementById("library-view-table-btn");
    const cardBtn = document.getElementById("library-view-card-btn");

    tableBtn?.addEventListener("click", () => {
      this.viewMode = "table";
      tableBtn.classList.add("active");
      cardBtn?.classList.remove("active");
      this.applyFilters();
      this.renderPaperList();
    });

    cardBtn?.addEventListener("click", () => {
      this.viewMode = "card";
      cardBtn.classList.add("active");
      tableBtn?.classList.remove("active");
      this.applyFilters();
      this.renderPaperList();
    });
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
    await Promise.all([this.fetchPapers(), this.fetchCollections()]);
    this.renderStats();
    this.renderCollectionSidebar();
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
