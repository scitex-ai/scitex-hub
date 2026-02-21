/**
 * Scholar Library Tab Manager - Main Orchestrator
 * Manages the library tab functionality: filtering, searching, viewing, editing papers
 */

import { LibraryPaper, UpdatePaperData } from "./types";
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

  async initialize(): Promise<void> {
    const loadingEl = document.getElementById("library-loading");
    if (loadingEl) {
      this.loadingSpinner = startInspiringSpinner(
        loadingEl,
        "Loading papers...",
      );
    }
    await this.fetchPapers();
    this.loadingSpinner?.stop();
    this.loadingSpinner = null;
    this.renderStats();
    this.applyFilters();
    this.renderPaperList();
    this.setupEventListeners();
    this.setupImportExport();
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

    document.querySelectorAll(".library-paper-card").forEach((card) => {
      if (card.getAttribute("data-paper-id") === paperId) {
        card.classList.add("selected");
      } else {
        card.classList.remove("selected");
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

  private async refreshLibrary(): Promise<void> {
    await this.fetchPapers();
    this.renderStats();
    this.applyFilters();
    this.renderPaperList();
  }
}

export function initLibraryManager(): void {
  const manager = new LibraryManager();
  manager.initialize();
}
