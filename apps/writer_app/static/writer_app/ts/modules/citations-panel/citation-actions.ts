/**
 * Citation Actions Module
 * Handles user interactions with citation cards (drag, click, expand)
 */

export class CitationActions {
  private selectedCards: Set<string> = new Set();
  private onSelectionChange?: () => void;

  constructor(onSelectionChange?: () => void) {
    this.onSelectionChange = onSelectionChange;
  }

  /**
   * Get selected cards
   */
  public getSelectedCards(): Set<string> {
    return this.selectedCards;
  }

  /**
   * Set selected cards
   */
  public setSelectedCards(selected: Set<string>): void {
    this.selectedCards = selected;
  }

  /**
   * Clear all selections
   */
  public clearSelection(): void {
    this.selectedCards.clear();
    document.querySelectorAll(".citation-card.selected").forEach((card) => {
      card.classList.remove("selected");
      const checkbox = card.querySelector(
        ".citation-checkbox",
      ) as HTMLInputElement;
      if (checkbox) checkbox.checked = false;
    });
    this.notifySelectionChange();
    console.log("[CitationActions] Selection cleared");
  }

  /**
   * Attach event listeners to citation cards
   */
  public attachListeners(): void {
    const cards = document.querySelectorAll(".citation-card");

    cards.forEach((card) => {
      card.addEventListener("dragstart", (e) =>
        this.handleDragStart(e as DragEvent),
      );
      card.addEventListener("dragend", (e) => this.handleDragEnd(e as DragEvent));
      card.addEventListener("click", (e) => this.handleCardClick(e as MouseEvent));
      card.addEventListener("dblclick", (e) =>
        this.handleCardDoubleClick(e as MouseEvent),
      );
    });

    // Attach checkbox listeners
    const checkboxes = document.querySelectorAll(".citation-checkbox");
    checkboxes.forEach((checkbox) => {
      checkbox.addEventListener("change", (e) =>
        this.handleCheckboxChange(e as Event),
      );
    });

    console.log(
      `[CitationActions] Attached listeners to ${cards.length} cards`,
    );
  }

  /**
   * Handle drag start
   */
  private handleDragStart(e: DragEvent): void {
    const card = e.target as HTMLElement;
    const citationKey = card.dataset.citationKey;

    if (!citationKey || !e.dataTransfer) return;

    // If card is part of multi-selection, drag all selected cards
    if (this.selectedCards.size > 0 && this.selectedCards.has(citationKey)) {
      const keys = Array.from(this.selectedCards).join(",");
      e.dataTransfer.setData("text/plain", keys);
      console.log("[CitationActions] Drag started (multi):", keys);
    } else {
      e.dataTransfer.setData("text/plain", citationKey);
      console.log("[CitationActions] Drag started (single):", citationKey);
    }

    e.dataTransfer.effectAllowed = "copy";
    card.classList.add("dragging");
  }

  /**
   * Handle drag end
   */
  private handleDragEnd(e: DragEvent): void {
    const card = e.target as HTMLElement;
    card.classList.remove("dragging");
  }

  /**
   * Handle checkbox change
   */
  private handleCheckboxChange(e: Event): void {
    e.stopPropagation();
    const checkbox = e.target as HTMLInputElement;
    const citationKey = checkbox.dataset.citationKey;

    if (!citationKey) return;

    const card = checkbox.closest(".citation-card") as HTMLElement;

    if (checkbox.checked) {
      this.selectedCards.add(citationKey);
      if (card) card.classList.add("selected");
    } else {
      this.selectedCards.delete(citationKey);
      if (card) card.classList.remove("selected");
    }

    console.log(
      "[CitationActions] Selected cards:",
      Array.from(this.selectedCards),
    );
    this.notifySelectionChange();
  }

  /**
   * Handle card click to toggle selection
   */
  private handleCardClick(e: MouseEvent): void {
    const target = e.target as HTMLElement;

    // Don't handle clicks on checkbox or drag handle
    if (
      target.classList.contains("citation-checkbox") ||
      target.classList.contains("citation-drag-handle") ||
      target.closest(".citation-drag-handle")
    ) {
      return;
    }

    const card = e.currentTarget as HTMLElement;
    const citationKey = card.dataset.citationKey;

    if (!citationKey) return;

    e.preventDefault();

    const checkbox = card.querySelector(
      ".citation-checkbox",
    ) as HTMLInputElement;

    // Toggle selection
    if (this.selectedCards.has(citationKey)) {
      this.selectedCards.delete(citationKey);
      card.classList.remove("selected");
      if (checkbox) checkbox.checked = false;
    } else {
      this.selectedCards.add(citationKey);
      card.classList.add("selected");
      if (checkbox) checkbox.checked = true;
    }

    console.log(
      "[CitationActions] Selected cards:",
      Array.from(this.selectedCards),
    );
    this.notifySelectionChange();
  }

  /**
   * Handle card double-click to toggle expand/collapse
   */
  private handleCardDoubleClick(e: MouseEvent): void {
    const target = e.target as HTMLElement;

    // Don't expand on checkbox or drag handle double-click
    if (
      target.classList.contains("citation-checkbox") ||
      target.classList.contains("citation-drag-handle") ||
      target.closest(".citation-drag-handle") ||
      target.closest(".citation-metrics-corner")
    ) {
      return;
    }

    const card = e.currentTarget as HTMLElement;
    const expandedView = card.querySelector(
      ".citation-expanded-view",
    ) as HTMLElement;

    if (!expandedView) return;

    e.preventDefault();
    e.stopPropagation();

    // Toggle expanded state
    const isExpanded = card.dataset.expanded === "true";

    if (isExpanded) {
      expandedView.style.display = "none";
      card.dataset.expanded = "false";
      console.log("[CitationActions] Collapsed citation card");
    } else {
      expandedView.style.display = "block";
      card.dataset.expanded = "true";
      console.log("[CitationActions] Expanded citation card");
    }
  }

  /**
   * Notify listeners of selection change
   */
  private notifySelectionChange(): void {
    if (this.onSelectionChange) {
      this.onSelectionChange();
    }
  }
}
