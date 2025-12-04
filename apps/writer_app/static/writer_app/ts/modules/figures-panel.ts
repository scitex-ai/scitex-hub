/**
 * Figures Panel Orchestrator
 * Coordinates all figure-related modules
 */

console.log("[DEBUG] figures-panel.ts loaded");

import type { Figure } from "./figures-panel/figures-list.js";
import { FiguresList } from "./figures-panel/figures-list.js";
import { FigureUpload } from "./figures-panel/figure-upload.js";
import { FigurePreview } from "./figures-panel/figure-preview.js";
import { FigureActions } from "./figures-panel/figure-actions.js";
import { FigureSearch } from "./figures-panel/figure-search.js";
import { FigureState } from "./figures-panel/figure-state.js";

// Re-export Figure type for backward compatibility
export type { Figure };

export class FiguresPanel {
  private figures: Figure[] = [];
  private filteredFigures: Figure[] = [];
  private isLoaded: boolean = false;
  private projectId: string | null = null;

  // Module instances
  private figuresList: FiguresList;
  private figureUpload: FigureUpload;
  private figurePreview: FigurePreview;
  private figureActions: FigureActions;
  private figureSearch: FigureSearch;
  private figureState: FigureState;

  constructor() {
    // Initialize modules
    this.figuresList = new FiguresList();
    this.figureUpload = new FigureUpload();
    this.figurePreview = new FigurePreview();
    this.figureActions = new FigureActions();
    this.figureSearch = new FigureSearch();
    this.figureState = new FigureState();

    this.init();
  }

  /**
   * Initialize the panel
   */
  private init(): void {
    // Get project ID
    const writerConfig = (window as any).WRITER_CONFIG;
    if (writerConfig?.projectId) {
      this.projectId = String(writerConfig.projectId);
      this.figureUpload.setProjectId(this.projectId);
    }

    // Setup modules
    this.setupModules();

    console.log("[FiguresPanel] Initialized with project:", this.projectId);
  }

  /**
   * Setup all modules with event handlers
   */
  private setupModules(): void {
    // Setup upload module
    this.figureUpload.setOnUploadSuccess(() => {
      this.isLoaded = false;
      this.loadFigures();
    });
    this.figureUpload.setupDropZone();

    // Setup list module event handlers
    this.figuresList.setEventHandlers({
      onCheckboxChange: (label, checked) => this.handleCheckboxChange(label, checked),
      onCardClick: (figure) => this.handleCardClick(figure),
      onCardDoubleClick: (card, figure) =>
        this.figurePreview.handleDoubleClick(card, figure),
      onDragStart: (event, figure) => this.figureActions.handleDragStart(event, figure),
      onDragEnd: (event) => this.figureActions.handleDragEnd(event),
    });

    // Setup search module
    this.figureSearch.setupEventListeners();

    // Listen for search and sort changes
    const searchInput = document.getElementById(
      "figures-search-toolbar",
    ) as HTMLInputElement;
    const sortSelect = document.getElementById(
      "figures-sort-toolbar",
    ) as HTMLSelectElement;

    if (searchInput) {
      searchInput.addEventListener("input", () => this.handleSearchAndSort());
    }

    if (sortSelect) {
      sortSelect.addEventListener("change", () => this.handleSearchAndSort());
    }

    console.log("[FiguresPanel] Modules setup complete");
  }

  /**
   * Load figures from API
   */
  async loadFigures(): Promise<void> {
    if (this.isLoaded) {
      console.log("[FiguresPanel] Already loaded, skipping");
      return;
    }

    if (!this.projectId) {
      console.error("[FiguresPanel] No project ID available");
      this.figureState.showEmpty();
      return;
    }

    this.figureState.showLoading();

    try {
      const apiUrl = `/writer/api/project/${this.projectId}/figures/`;
      console.log("[FiguresPanel] Fetching from:", apiUrl);

      const response = await fetch(apiUrl);
      const data = await response.json();

      if (data.success && data.figures) {
        this.figures = data.figures;
        this.filteredFigures = [...this.figures];
        this.isLoaded = true;

        console.log(`[FiguresPanel] Loaded ${this.figures.length} figures`);

        // Apply search and sort
        this.handleSearchAndSort();
      } else {
        console.warn("[FiguresPanel] No figures found");
        this.figureState.showEmpty();
      }
    } catch (error) {
      console.error("[FiguresPanel] Error loading figures:", error);
      this.figureState.showEmpty();
    }
  }

  /**
   * Handle search and sort
   */
  private handleSearchAndSort(): void {
    const searchQuery = this.figureSearch.getCurrentSearchQuery();
    const sortBy = this.figureSearch.getCurrentSortOption();

    this.filteredFigures = this.figureSearch.applySearchAndSort(
      this.figures,
      searchQuery,
      sortBy,
    );

    this.renderFigures();
  }

  /**
   * Render figures
   */
  private renderFigures(): void {
    // Hide all states
    this.figureState.hideAllStates();

    // Update count
    this.updateCountDisplay();

    if (this.filteredFigures.length === 0) {
      const searchQuery = this.figureSearch.getCurrentSearchQuery();
      if (searchQuery) {
        this.figureState.showNoResults();
      } else {
        this.figureState.showEmpty();
      }
      return;
    }

    // Render figures list
    this.figuresList.render(this.filteredFigures);
  }

  /**
   * Handle checkbox change
   */
  private handleCheckboxChange(label: string, checked: boolean): void {
    this.updateCountDisplay();
    console.log(`[FiguresPanel] ${label} ${checked ? "selected" : "deselected"}`);
  }

  /**
   * Handle card click
   */
  private handleCardClick(figure: Figure): void {
    const figureKey = figure.label || figure.file_name;
    console.log("[FiguresPanel] Card clicked:", figureKey);
  }

  /**
   * Update count display
   */
  private updateCountDisplay(): void {
    const selectedCount = this.figuresList.getSelectedCards().size;
    const totalCount = this.filteredFigures.length;
    this.figureState.updateCountDisplay(selectedCount, totalCount);
  }
}

// Initialize and expose globally
const figuresPanel = new FiguresPanel();
(window as any).figuresPanel = figuresPanel;

console.log("[FiguresPanel] Module initialized and exposed globally");
