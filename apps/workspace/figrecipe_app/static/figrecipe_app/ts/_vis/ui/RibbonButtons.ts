/**
 * RibbonButtons - Manages ribbon/pane header button interactions
 *
 * Responsibilities:
 * - Initialize data import/export buttons
 * - Initialize table transformation buttons (sort, filter)
 * - Initialize table structure buttons (add rows/columns)
 * - Initialize header/index toggle buttons
 * - Initialize quick plot buttons
 * - Handle drag and drop file uploads
 * - Display modal dialogs and help
 *
 * Dependencies:
 * - Callbacks for data operations
 * - References to UI state (headers, indices)
 * - Modal elements in DOM
 */

// Map plot types to gallery preview images (using new transparent gallery)
const PLOT_PREVIEW_IMAGES: Record<string, string> = {
  scatter: "/apps/figrecipe/api/gallery/project/scatter/scatter/image/?format=binary",
  line: "/apps/figrecipe/api/gallery/project/line/plot/image/?format=binary",
  bar: "/apps/figrecipe/api/gallery/project/categorical/bar/image/?format=binary",
  histogram:
    "/apps/figrecipe/api/gallery/project/distribution/hist/image/?format=binary",
  box: "/apps/figrecipe/api/gallery/project/categorical/boxplot/image/?format=binary",
  violin:
    "/apps/figrecipe/api/gallery/project/categorical/violinplot/image/?format=binary",
  heatmap:
    "/apps/figrecipe/api/gallery/project/grid/stx_heatmap/image/?format=binary",
  contour: "/apps/figrecipe/api/gallery/project/contour/contour/image/?format=binary",
};

export class RibbonButtons {
  private previewPopup: HTMLElement | null = null;

  constructor(
    private handleFileImportCallback?: (file: File) => void,
    private loadDemoDataCallback?: () => void,
    private addColumnsCallback?: (count: number) => void,
    private addRowsCallback?: (count: number) => void,
    private firstRowIsHeaderRef?: { value: boolean },
    private firstColIsIndexRef?: { value: boolean },
    private renderEditableDataTableCallback?: () => void,
    private statusBarCallback?: (message: string) => void,
    private showSortModalCallback?: () => void,
    private showFilterModalCallback?: () => void,
    private showTableHelpCallback?: () => void,
    private createQuickPlotCallback?: (
      plotType: string,
    ) => void | Promise<void>,
    private handleExportPlotCSVCallback?: () => void,
  ) {
    this.createPreviewPopup();
  }

  /**
   * Create the preview popup element
   */
  private createPreviewPopup(): void {
    this.previewPopup = document.createElement("div");
    this.previewPopup.className = "plot-preview-popup";
    this.previewPopup.innerHTML = `
            <img src="" alt="Plot preview">
            <div class="preview-label"></div>
        `;
    document.body.appendChild(this.previewPopup);
  }

  /**
   * Show preview popup for a plot type button
   */
  private showPreview(btn: HTMLElement, plotType: string): void {
    if (!this.previewPopup) return;

    const imagePath = PLOT_PREVIEW_IMAGES[plotType];
    if (!imagePath) return;

    const img = this.previewPopup.querySelector("img") as HTMLImageElement;
    const label = this.previewPopup.querySelector(
      ".preview-label",
    ) as HTMLElement;

    img.src = imagePath;
    label.textContent = btn.getAttribute("data-tooltip") || plotType;

    // Position below the button
    const rect = btn.getBoundingClientRect();
    this.previewPopup.style.left = `${rect.left + rect.width / 2 - 83}px`; // 83 = half of 150px + padding
    this.previewPopup.style.top = `${rect.bottom + 8}px`;

    this.previewPopup.classList.add("visible");
  }

  /**
   * Hide preview popup
   */
  private hidePreview(): void {
    if (this.previewPopup) {
      this.previewPopup.classList.remove("visible");
    }
  }

  /**
   * Initialize all ribbon buttons and their handlers
   */
  public initRibbonButtons(): void {
    const dataInput = document.getElementById(
      "data-file-input",
    ) as HTMLInputElement;

    // Import Data buttons (data table header)
    const importDataBtns = document.querySelectorAll("#import-data-btn-small");
    importDataBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        dataInput?.click();
      });
    });

    dataInput?.addEventListener("change", (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file && this.handleFileImportCallback) {
        this.handleFileImportCallback(file);
      }
    });

    // Demo Data buttons (data table header)
    const demoDataBtns = document.querySelectorAll("#demo-data-btn-small");
    demoDataBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        if (this.loadDemoDataCallback) {
          this.loadDemoDataCallback();
        }
      });
    });

    // Header toggle button (data table header)
    const headerToggleBtn = document.getElementById("header-toggle-btn");
    headerToggleBtn?.addEventListener("click", () => {
      if (this.firstRowIsHeaderRef) {
        this.firstRowIsHeaderRef.value = !this.firstRowIsHeaderRef.value;
        headerToggleBtn.classList.toggle(
          "active",
          this.firstRowIsHeaderRef.value,
        );
        this.updateStatusBar(
          `First row is now treated as ${this.firstRowIsHeaderRef.value ? "header" : "data"}`,
        );
        console.log(
          "[RibbonButtons] First row is header:",
          this.firstRowIsHeaderRef.value,
        );
      }
    });

    // Index toggle button (data table index)
    const indexToggleBtn = document.getElementById("index-toggle-btn");
    indexToggleBtn?.addEventListener("click", () => {
      if (this.firstColIsIndexRef) {
        this.firstColIsIndexRef.value = !this.firstColIsIndexRef.value;
        indexToggleBtn.classList.toggle(
          "active",
          this.firstColIsIndexRef.value,
        );
        this.updateStatusBar(
          `First column is now treated as ${this.firstColIsIndexRef.value ? "index" : "data"}`,
        );
        console.log(
          "[RibbonButtons] First column is index:",
          this.firstColIsIndexRef.value,
        );

        // Re-render table to show/hide index styling
        if (this.renderEditableDataTableCallback) {
          this.renderEditableDataTableCallback();
        }
      }
    });

    // Sort button (data table header)
    const sortBtn = document.getElementById("transform-sort");
    sortBtn?.addEventListener("click", () => {
      if (this.showSortModalCallback) {
        this.showSortModalCallback();
      }
    });

    // Filter button (data table header)
    const filterBtn = document.getElementById("transform-filter");
    filterBtn?.addEventListener("click", () => {
      if (this.showFilterModalCallback) {
        this.showFilterModalCallback();
      }
    });

    // Add columns button (data table header)
    const addColumnsBtn = document.getElementById("add-columns-btn");
    addColumnsBtn?.addEventListener("click", () => {
      if (this.addColumnsCallback) {
        this.addColumnsCallback(10);
      }
    });

    // Add rows button (data table header)
    const addRowsBtn = document.getElementById("add-rows-btn");
    addRowsBtn?.addEventListener("click", () => {
      if (this.addRowsCallback) {
        this.addRowsCallback(10);
      }
    });

    // Table help button - show keyboard shortcuts modal
    const tableHelpBtn = document.getElementById("table-help-btn");
    tableHelpBtn?.addEventListener("click", () => {
      // Show the full keyboard shortcuts modal
      const shortcutsModal = document.getElementById("vis-shortcuts-modal");
      if (shortcutsModal) {
        shortcutsModal.style.display = "block";
        console.log("[RibbonButtons] Vis shortcuts modal opened");
      } else if (this.showTableHelpCallback) {
        // Fallback to alert if modal not found
        this.showTableHelpCallback();
      }
    });

    // Export plot CSV button
    const exportPlotCsvBtn = document.getElementById("export-plot-csv-btn");
    exportPlotCsvBtn?.addEventListener("click", () => {
      if (this.handleExportPlotCSVCallback) {
        this.handleExportPlotCSVCallback();
      }
    });

    // Quick create plot buttons (from canvas pane header)
    const quickPlotBtns = document.querySelectorAll("[data-plot-type]");
    quickPlotBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const plotType = btn.getAttribute("data-plot-type");
        if (plotType && this.createQuickPlotCallback) {
          this.createQuickPlotCallback(plotType);
        }
      });

      // Add hover preview for plot type buttons
      btn.addEventListener("mouseenter", () => {
        const plotType = btn.getAttribute("data-plot-type");
        if (plotType) {
          this.showPreview(btn as HTMLElement, plotType);
        }
      });

      btn.addEventListener("mouseleave", () => {
        this.hidePreview();
      });
    });

    // Download dropdown toggle
    this.initDownloadDropdown();

    console.log(
      "[RibbonButtons] Ribbon buttons initialized with hover previews",
    );
  }

  /**
   * Initialize download dropdown toggle
   */
  private initDownloadDropdown(): void {
    const dropdown = document.getElementById("download-dropdown");
    const toggleBtn = document.getElementById("download-btn");
    if (!dropdown || !toggleBtn) return;

    // Toggle dropdown on button click
    toggleBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdown.classList.toggle("open");
    });

    // Close dropdown when clicking outside
    document.addEventListener("click", (e) => {
      const target = e.target as Element;
      if (!dropdown.contains(target)) {
        dropdown.classList.remove("open");
      }
    });

    // Close dropdown when an item is clicked
    dropdown.querySelectorAll(".dropdown-item").forEach((item) => {
      item.addEventListener("click", () => {
        dropdown.classList.remove("open");
      });
    });

    console.log("[RibbonButtons] Download dropdown initialized");
  }

  /**
   * Initialize drag and drop for file uploads
   */
  public initDragAndDrop(): void {
    const dropZone = document.body;

    // Prevent default drag behaviors
    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(
        eventName,
        (e) => {
          e.preventDefault();
          e.stopPropagation();
        },
        false,
      );
    });

    // Highlight drop zone when file is dragged over
    ["dragenter", "dragover"].forEach((eventName) => {
      dropZone.addEventListener(
        eventName,
        () => {
          dropZone.classList.add("drag-over");
        },
        false,
      );
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(
        eventName,
        () => {
          dropZone.classList.remove("drag-over");
        },
        false,
      );
    });

    // Handle dropped files
    dropZone.addEventListener(
      "drop",
      (e: DragEvent) => {
        const files = e.dataTransfer?.files;
        if (files && files.length > 0) {
          const file = files[0];
          if (file.name.endsWith(".csv") || file.name.endsWith(".xlsx")) {
            if (this.handleFileImportCallback) {
              this.handleFileImportCallback(file);
            }
          } else {
            this.updateStatusBar(
              "Invalid file type. Please drop CSV or Excel files.",
            );
          }
        }
      },
      false,
    );

    console.log("[RibbonButtons] Drag and drop initialized");
  }

  /**
   * Update status bar message
   */
  private updateStatusBar(message: string): void {
    if (this.statusBarCallback) {
      this.statusBarCallback(message);
    }
  }
}
