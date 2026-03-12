/**
 * PlotGallery - Plot type gallery with thumbnails
 *
 * Shows plot type thumbnails on ribbon button hover
 * Allows selecting plot types to create new figures
 */

export interface PlotInfo {
  id: string;
  name: string;
  category: string;
  number: string;
  files: {
    png: string | null;
    json: string | null;
    csv: string | null;
  };
}

export interface GalleryInfo {
  id: string;
  name: string;
  description: string;
  plots: PlotInfo[];
}

export interface GalleryData {
  galleries: GalleryInfo[];
  total_plots: number;
}

export class PlotGallery {
  private galleries: GalleryInfo[] = [];
  private categories: Map<string, PlotInfo[]> = new Map();
  private galleryContainer: HTMLElement | null = null;
  private currentCategory: string = "all";
  private isLoading: boolean = false;

  private onSelectCallback?: (plot: PlotInfo, gallery: GalleryInfo) => void;

  constructor(
    options: {
      containerId?: string;
      onSelect?: (plot: PlotInfo, gallery: GalleryInfo) => void;
    } = {},
  ) {
    this.galleryContainer = document.getElementById(
      options.containerId || "plot-gallery",
    );
    this.onSelectCallback = options.onSelect;

    this.loadGalleries();
  }

  /**
   * Load galleries from API
   */
  private async loadGalleries(): Promise<void> {
    if (this.isLoading) return;
    this.isLoading = true;

    try {
      const response = await fetch("/apps/figrecipe/api/gallery/");
      if (!response.ok) {
        throw new Error("Failed to load galleries");
      }

      const data: GalleryData = await response.json();
      this.galleries = data.galleries;

      // Organize by category
      this.organizeByCategory();

      console.log(
        `[PlotGallery] Loaded ${data.total_plots} plots from ${this.galleries.length} galleries`,
      );
    } catch (error) {
      console.error("[PlotGallery] Load error:", error);
    } finally {
      this.isLoading = false;
    }
  }

  /**
   * Organize plots by category
   */
  private organizeByCategory(): void {
    this.categories.clear();

    for (const gallery of this.galleries) {
      for (const plot of gallery.plots) {
        const category = plot.category;
        if (!this.categories.has(category)) {
          this.categories.set(category, []);
        }
        this.categories.get(category)!.push(plot);
      }
    }
  }

  /**
   * Get all categories
   */
  public getCategories(): string[] {
    return Array.from(this.categories.keys());
  }

  /**
   * Get plots by category
   */
  public getPlotsByCategory(category: string): PlotInfo[] {
    if (category === "all") {
      return this.galleries.flatMap((g) => g.plots);
    }
    return this.categories.get(category) || [];
  }

  /**
   * Get plots by gallery
   */
  public getPlotsByGallery(galleryId: string): PlotInfo[] {
    const gallery = this.galleries.find((g) => g.id === galleryId);
    return gallery?.plots || [];
  }

  /**
   * Create gallery dropdown HTML for a ribbon button
   */
  public createGalleryDropdown(category: string = "all"): HTMLElement {
    const dropdown = document.createElement("div");
    dropdown.className = "plot-gallery-dropdown";

    const plots = this.getPlotsByCategory(category);

    if (plots.length === 0) {
      dropdown.innerHTML =
        '<div class="gallery-empty">No plots available</div>';
      return dropdown;
    }

    // Category tabs
    const tabsHtml = this.createCategoryTabs(category);

    // Thumbnails grid
    const gridHtml = plots
      .map((plot) => this.createThumbnailItem(plot))
      .join("");

    dropdown.innerHTML = `
            <div class="gallery-tabs">${tabsHtml}</div>
            <div class="gallery-grid">${gridHtml}</div>
        `;

    // Bind events
    this.bindDropdownEvents(dropdown);

    return dropdown;
  }

  /**
   * Create category tabs HTML
   */
  private createCategoryTabs(activeCategory: string): string {
    const categories = ["all", ...this.getCategories()];

    return categories
      .map(
        (cat) => `
            <button class="gallery-tab ${cat === activeCategory ? "active" : ""}"
                    data-category="${cat}">
                ${this.formatCategoryName(cat)}
            </button>
        `,
      )
      .join("");
  }

  /**
   * Create thumbnail item HTML
   */
  private createThumbnailItem(plot: PlotInfo): string {
    const gallery = this.galleries.find((g) =>
      g.plots.some((p) => p.id === plot.id),
    );

    return `
            <div class="gallery-item" data-plot-id="${plot.id}"
                 data-gallery-id="${gallery?.id || ""}"
                 title="${plot.name}">
                <div class="gallery-thumbnail">
                    <img src="/apps/figrecipe/api/gallery/${gallery?.id || "matplotlib"}/${plot.id.split("_").slice(1).join("_")}/thumbnail/?format=binary"
                         alt="${plot.name}"
                         loading="lazy"
                         onerror="this.style.display='none'">
                </div>
                <div class="gallery-item-name">${plot.name}</div>
                <div class="gallery-item-badge ${gallery?.id || ""}">${gallery?.name || ""}</div>
            </div>
        `;
  }

  /**
   * Bind dropdown events
   */
  private bindDropdownEvents(dropdown: HTMLElement): void {
    // Category tab clicks
    dropdown.querySelectorAll(".gallery-tab").forEach((tab) => {
      tab.addEventListener("click", (e) => {
        const category = (e.target as HTMLElement).dataset.category || "all";
        this.switchCategory(dropdown, category);
      });
    });

    // Thumbnail clicks
    dropdown.querySelectorAll(".gallery-item").forEach((item) => {
      item.addEventListener("click", () => {
        const plotId = (item as HTMLElement).dataset.plotId;
        const galleryId = (item as HTMLElement).dataset.galleryId;

        if (plotId && galleryId) {
          this.handlePlotSelect(plotId, galleryId);
        }
      });
    });
  }

  /**
   * Switch category in dropdown
   */
  private switchCategory(dropdown: HTMLElement, category: string): void {
    this.currentCategory = category;

    // Update tabs
    dropdown.querySelectorAll(".gallery-tab").forEach((tab) => {
      tab.classList.toggle(
        "active",
        (tab as HTMLElement).dataset.category === category,
      );
    });

    // Update grid
    const grid = dropdown.querySelector(".gallery-grid");
    if (grid) {
      const plots = this.getPlotsByCategory(category);
      grid.innerHTML = plots
        .map((plot) => this.createThumbnailItem(plot))
        .join("");

      // Rebind thumbnail events
      grid.querySelectorAll(".gallery-item").forEach((item) => {
        item.addEventListener("click", () => {
          const plotId = (item as HTMLElement).dataset.plotId;
          const galleryId = (item as HTMLElement).dataset.galleryId;

          if (plotId && galleryId) {
            this.handlePlotSelect(plotId, galleryId);
          }
        });
      });
    }
  }

  /**
   * Handle plot selection
   */
  private handlePlotSelect(plotId: string, galleryId: string): void {
    const gallery = this.galleries.find((g) => g.id === galleryId);
    const plot = gallery?.plots.find((p) => p.id === plotId);

    if (plot && gallery) {
      console.log(`[PlotGallery] Selected: ${plot.name} from ${gallery.name}`);
      this.onSelectCallback?.(plot, gallery);
    }
  }

  /**
   * Format category name for display
   */
  private formatCategoryName(category: string): string {
    const names: Record<string, string> = {
      all: "All",
      line: "Line",
      scatter: "Scatter",
      bar: "Bar",
      distribution: "Distribution",
      statistical: "Statistical",
      heatmap: "Heatmap",
      contour: "Contour",
      pie: "Pie",
      vector: "Vector",
      error: "Error",
      stem: "Stem",
      other: "Other",
    };
    return (
      names[category] || category.charAt(0).toUpperCase() + category.slice(1)
    );
  }

  /**
   * Attach gallery to a ribbon button
   */
  public attachToButton(buttonEl: HTMLElement, category: string = "all"): void {
    let dropdownEl: HTMLElement | null = null;

    buttonEl.addEventListener("mouseenter", () => {
      if (!dropdownEl) {
        dropdownEl = this.createGalleryDropdown(category);
        buttonEl.appendChild(dropdownEl);
      }
      dropdownEl.classList.add("show");
    });

    buttonEl.addEventListener("mouseleave", () => {
      if (dropdownEl) {
        dropdownEl.classList.remove("show");
      }
    });
  }

  /**
   * Load template for selected plot
   */
  public async loadTemplate(plotId: string, galleryId: string): Promise<any> {
    try {
      const response = await fetch(
        `/apps/figrecipe/api/gallery/${galleryId}/${plotId}/template/`,
      );
      if (!response.ok) {
        throw new Error("Failed to load template");
      }
      return await response.json();
    } catch (error) {
      console.error("[PlotGallery] Template load error:", error);
      return null;
    }
  }
}
