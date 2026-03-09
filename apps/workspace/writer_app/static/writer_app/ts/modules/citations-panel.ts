/**
 * Citations Panel Orchestrator
 * Coordinates citation management modules
 */


import { statePersistence } from "./_state-persistence";
import type { Citation } from "./_citations-panel/types";
import { CitationSearch } from "./_citations-panel/citation-search";
import { CitationSorting } from "./_citations-panel/citation-sorting";
import { CitationRenderer } from "./_citations-panel/citation-renderer";
import { CitationActions } from "./_citations-panel/citation-actions";
import { CitationLoader } from "./_citations-panel/citation-loader";
import { CitationUpload } from "./_citations-panel/citation-upload";
import { UIState } from "./_citations-panel/ui-state";

export type { Citation } from "./_citations-panel/types";

export class CitationsPanel {
  private citations: Citation[] = [];
  private filteredCitations: Citation[] = [];
  private isLoaded: boolean = false;
  private projectId: string | null = null;

  // Module instances
  private search: CitationSearch;
  private sorting: CitationSorting;
  private renderer: CitationRenderer;
  private actions: CitationActions;
  private loader: CitationLoader;
  private upload: CitationUpload;
  private uiState: UIState;

  constructor() {
    this.search = new CitationSearch();
    this.sorting = new CitationSorting();
    this.renderer = new CitationRenderer();
    this.actions = new CitationActions(() => this.updateSelectionUI());
    this.uiState = new UIState();

    this.init();

    // Loader is initialized after projectId is set
    this.loader = new CitationLoader(this.projectId);

    // Upload handler
    this.upload = new CitationUpload(this.projectId);
    this.upload.setOnUploadSuccess(() => {
      this.isLoaded = false;
      this.loadCitations();
    });
    this.upload.setupDropZone();
  }

  /**
   * Initialize the panel
   */
  private init(): void {
    // Get project ID
    const writerConfig = (window as any).WRITER_CONFIG;
    if (writerConfig?.projectId) {
      this.projectId = String(writerConfig.projectId);
    }

    // Setup event listeners
    this.setupEventListeners();

    console.log("[CitationsPanel] Initialized with project:", this.projectId);
  }

  /**
   * Setup event listeners
   */
  private setupEventListeners(): void {
    // Search input (toolbar)
    const searchInput = document.getElementById(
      "citations-search-toolbar",
    ) as HTMLInputElement;
    if (searchInput) {
      searchInput.addEventListener("input", () => this.handleSearch());
    }

    // Sort select (toolbar)
    const sortSelect = document.getElementById(
      "citations-sort-toolbar",
    ) as HTMLSelectElement;
    if (sortSelect) {
      // Restore saved sorting preference
      const savedSort = statePersistence.getSavedCitationsSorting();
      if (savedSort) {
        sortSelect.value = savedSort;
        console.log("[CitationsPanel] Restored sorting preference:", savedSort);
      }

      sortSelect.addEventListener("change", () =>
        this.handleSort(sortSelect.value),
      );
    }

    console.log("[CitationsPanel] Event listeners setup complete");
  }

  /**
   * Load citations from API
   */
  async loadCitations(): Promise<void> {
    if (this.isLoaded) {
      console.log("[CitationsPanel] Already loaded, skipping");
      return;
    }

    if (!this.projectId) {
      console.error("[CitationsPanel] No project ID available");
      this.uiState.showEmptyState();
      return;
    }

    this.uiState.showLoading();

    const result = await this.loader.loadCitations();

    if (result.success && result.citations.length > 0) {
      this.citations = result.citations;
      this.filteredCitations = [...this.citations];
      this.isLoaded = true;

      // Apply saved sort or default to citation count
      const savedSort = statePersistence.getSavedCitationsSorting();
      this.handleSort(savedSort || "citation-count");
    } else {
      console.warn("[CitationsPanel] No citations found");
      this.uiState.showEmptyState();
    }
  }

  /**
   * Render citations as cards
   */
  private renderCitations(): void {
    const container = document.getElementById("citations-cards-container");
    if (!container) return;

    // Hide all empty states
    this.uiState.hideAllStates();

    // Update count display
    this.updateCountDisplay();

    if (this.filteredCitations.length === 0) {
      const searchInput = document.getElementById(
        "citations-search-toolbar",
      ) as HTMLInputElement;
      if (searchInput && searchInput.value.trim()) {
        this.uiState.showNoResults();
      } else {
        this.uiState.showEmptyState();
      }
      return;
    }

    // Sync selected cards to renderer
    this.renderer.setSelectedCards(this.actions.getSelectedCards());

    // Render cards
    this.renderer.renderCitations(this.filteredCitations);

    // Attach event listeners
    this.actions.attachListeners();
  }

  /**
   * Handle search with fuzzy matching
   */
  private handleSearch(): void {
    const searchInput = document.getElementById(
      "citations-search-toolbar",
    ) as HTMLInputElement;

    if (!searchInput) return;

    const query = searchInput.value.trim();
    this.filteredCitations = this.search.filterCitations(this.citations, query);
    this.renderCitations();
  }

  /**
   * Handle sorting
   */
  private handleSort(sortBy: string): void {
    console.log("[CitationsPanel] Sorting by:", sortBy);

    // Save sorting preference
    statePersistence.saveCitationsSorting(sortBy);

    this.filteredCitations = this.sorting.sortCitations(
      this.filteredCitations,
      sortBy,
    );
    this.renderCitations();
  }

  /**
   * Update count display (toolbar selection total)
   */
  private updateCountDisplay(): void {
    this.uiState.updateCountDisplay(
      this.actions.getSelectedCards().size,
      this.filteredCitations.length,
    );
  }

  /**
   * Update selection UI
   */
  private updateSelectionUI(): void {
    this.updateCountDisplay();
  }

  /**
   * Clear all selections
   */
  public clearSelection(): void {
    this.actions.clearSelection();
    this.updateSelectionUI();
  }
}
