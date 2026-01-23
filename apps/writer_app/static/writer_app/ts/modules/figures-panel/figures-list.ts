/**
 * Figures List Module
 * Handles figure card rendering and display
 */

export interface Figure {
  id?: number;
  label?: string;
  file_name: string;
  file_path: string;
  file_type?: string;
  file_size?: number;
  file_hash?: string;
  caption?: string;
  dimensions?: string;
  thumbnail_url?: string;
  thumbnail_path?: string;
  width?: number;
  height?: number;
  tags?: string[];
  is_referenced?: number | boolean;
  reference_count?: number;
  source?: string;
  location?: string;
  last_modified?: number;
}

export class FiguresList {
  private selectedCards: Set<string> = new Set();
  private onCheckboxChange?: (label: string, checked: boolean) => void;
  private onCardClick?: (figure: Figure) => void;
  private onCardDoubleClick?: (card: HTMLElement, figure: Figure) => void;
  private onDragStart?: (event: DragEvent, figure: Figure) => void;
  private onDragEnd?: (event: DragEvent) => void;

  constructor() {
    console.log("[FiguresList] Initialized");
  }

  /**
   * Set event handlers
   */
  setEventHandlers(handlers: {
    onCheckboxChange?: (label: string, checked: boolean) => void;
    onCardClick?: (figure: Figure) => void;
    onCardDoubleClick?: (card: HTMLElement, figure: Figure) => void;
    onDragStart?: (event: DragEvent, figure: Figure) => void;
    onDragEnd?: (event: DragEvent) => void;
  }): void {
    this.onCheckboxChange = handlers.onCheckboxChange;
    this.onCardClick = handlers.onCardClick;
    this.onCardDoubleClick = handlers.onCardDoubleClick;
    this.onDragStart = handlers.onDragStart;
    this.onDragEnd = handlers.onDragEnd;
  }

  /**
   * Render figures as cards
   */
  render(figures: Figure[], containerId: string = "figures-cards-container"): void {
    const container = document.getElementById(containerId);
    if (!container) {
      console.warn("[FiguresList] Container not found:", containerId);
      return;
    }

    // Clear container
    container.innerHTML = "";

    // Render each figure card
    figures.forEach((figure) => {
      const card = this.createFigureCard(figure);
      container.appendChild(card);
    });

    console.log(`[FiguresList] Rendered ${figures.length} figures`);
  }

  /**
   * Create a figure card element
   */
  private createFigureCard(figure: Figure): HTMLElement {
    const card = document.createElement("div");
    card.className = "figure-card";
    const figureKey = figure.label || figure.file_name;
    card.dataset.label = figureKey;

    // Add "referenced" badge if figure is used in paper
    if (figure.is_referenced) {
      const badge = document.createElement("div");
      badge.className = "figure-badge";
      badge.textContent = `In Paper (${figure.reference_count || 0}×)`;
      card.appendChild(badge);
    }

    // Drag handle
    const dragHandle = document.createElement("div");
    dragHandle.className = "figure-drag-handle";
    dragHandle.innerHTML = '<i class="fas fa-grip-vertical"></i>';

    // Thumbnail
    const thumbnail = this.createThumbnail(figure, figureKey);

    // Content
    const content = this.createContent(figure);

    // Checkbox corner
    const checkboxCorner = this.createCheckboxCorner(figureKey);

    // Assemble card
    card.appendChild(dragHandle);
    card.appendChild(thumbnail);
    card.appendChild(content);
    card.appendChild(checkboxCorner);

    // Event listeners
    this.attachCardEventListeners(card, figure);

    return card;
  }

  /**
   * Create thumbnail element
   */
  private createThumbnail(figure: Figure, figureKey: string): HTMLElement {
    const thumbnail = document.createElement("div");
    thumbnail.className = "figure-thumbnail";

    if (figure.thumbnail_url) {
      const img = document.createElement("img");
      img.src = figure.thumbnail_url;
      img.alt = figureKey;
      img.onerror = () => {
        thumbnail.innerHTML = '<i class="fas fa-image"></i>';
      };
      thumbnail.appendChild(img);
    } else {
      thumbnail.innerHTML = '<i class="fas fa-image"></i>';
    }

    return thumbnail;
  }

  /**
   * Create content section of card
   */
  private createContent(figure: Figure): HTMLElement {
    const content = document.createElement("div");
    content.className = "figure-content";

    // Label
    const label = document.createElement("div");
    label.className = "figure-label";
    const displayName = figure.label || figure.file_name.replace(/\.[^/.]+$/, "");
    label.textContent = displayName;

    // Caption
    const caption = document.createElement("div");
    caption.className = "figure-caption";
    caption.textContent = figure.caption || figure.location || "No location info";

    // Metadata
    const metadata = this.createMetadata(figure);

    content.appendChild(label);
    content.appendChild(caption);
    content.appendChild(metadata);

    return content;
  }

  /**
   * Create metadata section
   */
  private createMetadata(figure: Figure): HTMLElement {
    const metadata = document.createElement("div");
    metadata.className = "figure-metadata";

    // File name
    const fileName = document.createElement("span");
    fileName.className = "figure-file-name";
    fileName.textContent = figure.file_name;
    metadata.appendChild(fileName);

    // File size
    if (figure.file_size) {
      const dot1 = document.createElement("span");
      dot1.className = "meta-dot";
      dot1.textContent = "•";
      metadata.appendChild(dot1);

      const fileSize = document.createElement("span");
      fileSize.className = "figure-file-size";
      const sizeKB = Math.round(figure.file_size / 1024);
      fileSize.textContent = `${sizeKB} KB`;
      metadata.appendChild(fileSize);
    }

    // File type
    if (figure.file_type) {
      const dot2 = document.createElement("span");
      dot2.className = "meta-dot";
      dot2.textContent = "•";
      metadata.appendChild(dot2);

      const fileType = document.createElement("span");
      fileType.className = "figure-file-type";
      fileType.textContent = figure.file_type.toUpperCase();
      metadata.appendChild(fileType);
    }

    return metadata;
  }

  /**
   * Create checkbox corner
   */
  private createCheckboxCorner(figureKey: string): HTMLElement {
    const checkboxCorner = document.createElement("div");
    checkboxCorner.className = "figure-checkbox-corner";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "figure-checkbox";
    checkbox.checked = this.selectedCards.has(figureKey);
    checkbox.addEventListener("change", (e) => {
      e.stopPropagation();
      this.handleCheckboxChange(figureKey, checkbox.checked);
    });

    checkboxCorner.appendChild(checkbox);
    return checkboxCorner;
  }

  /**
   * Attach event listeners to card
   */
  private attachCardEventListeners(card: HTMLElement, figure: Figure): void {
    // Click
    card.addEventListener("click", (e) => {
      if (!(e.target as HTMLElement).closest(".figure-checkbox")) {
        this.onCardClick?.(figure);
      }
    });

    // Double click
    card.addEventListener("dblclick", () => {
      this.onCardDoubleClick?.(card, figure);
    });

    // Drag and drop
    card.draggable = true;
    card.addEventListener("dragstart", (e) => this.onDragStart?.(e, figure));
    card.addEventListener("dragend", (e) => this.onDragEnd?.(e));
  }

  /**
   * Handle checkbox change
   */
  private handleCheckboxChange(label: string, checked: boolean): void {
    if (checked) {
      this.selectedCards.add(label);
    } else {
      this.selectedCards.delete(label);
    }

    // Update card styling
    const card = document.querySelector(
      `.figure-card[data-label="${label}"]`,
    ) as HTMLElement;
    if (card) {
      card.classList.toggle("selected", checked);
    }

    this.onCheckboxChange?.(label, checked);
  }

  /**
   * Get selected cards
   */
  getSelectedCards(): Set<string> {
    return this.selectedCards;
  }

  /**
   * Clear selection
   */
  clearSelection(): void {
    this.selectedCards.clear();
    document.querySelectorAll(".figure-card.selected").forEach((card) => {
      card.classList.remove("selected");
      const checkbox = card.querySelector(".figure-checkbox") as HTMLInputElement;
      if (checkbox) checkbox.checked = false;
    });
  }
}
