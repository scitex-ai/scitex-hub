/**
 * Table Renderer
 * Handles rendering of table cards and UI elements
 */

import { Table } from "./types.js";

export class TableRenderer {
  private selectedCards: Set<string> = new Set();
  private onCardClick?: (table: Table) => void;
  private onCardDoubleClick?: (card: HTMLElement, table: Table) => void;
  private onCheckboxChange?: (label: string, checked: boolean) => void;
  private onDragStart?: (event: DragEvent, table: Table) => void;
  private onDragEnd?: (event: DragEvent) => void;

  /**
   * Set event handlers
   */
  setEventHandlers(handlers: {
    onCardClick?: (table: Table) => void;
    onCardDoubleClick?: (card: HTMLElement, table: Table) => void;
    onCheckboxChange?: (label: string, checked: boolean) => void;
    onDragStart?: (event: DragEvent, table: Table) => void;
    onDragEnd?: (event: DragEvent) => void;
  }): void {
    this.onCardClick = handlers.onCardClick;
    this.onCardDoubleClick = handlers.onCardDoubleClick;
    this.onCheckboxChange = handlers.onCheckboxChange;
    this.onDragStart = handlers.onDragStart;
    this.onDragEnd = handlers.onDragEnd;
  }

  /**
   * Get selected cards
   */
  getSelectedCards(): Set<string> {
    return this.selectedCards;
  }

  /**
   * Render tables as cards
   */
  renderTables(tables: Table[]): void {
    const container = document.getElementById("tables-cards-container");
    if (!container) return;

    // Clear container
    container.innerHTML = "";

    // Render each table card
    tables.forEach((table) => {
      const card = this.createTableCard(table);
      container.appendChild(card);
    });

    console.log(`[TableRenderer] Rendered ${tables.length} tables`);
  }

  /**
   * Create a table card element
   */
  private createTableCard(table: Table): HTMLElement {
    const card = document.createElement("div");
    card.className = "table-card";
    const tableKey = table.label || table.file_name;
    card.dataset.label = tableKey;

    // Add "referenced" badge if table is used in paper
    if (table.is_referenced) {
      const badge = document.createElement("div");
      badge.className = "table-badge";
      badge.textContent = `In Paper (${table.reference_count || 0}×)`;
      card.appendChild(badge);
    }

    // Drag handle
    const dragHandle = document.createElement("div");
    dragHandle.className = "table-drag-handle";
    dragHandle.innerHTML = '<i class="fas fa-grip-vertical"></i>';

    // Thumbnail
    const thumbnail = this.createThumbnail(table, tableKey);

    // Content
    const content = this.createCardContent(table);

    // Checkbox corner
    const checkboxCorner = this.createCheckboxCorner(tableKey);

    // Assemble card
    card.appendChild(dragHandle);
    card.appendChild(thumbnail);
    card.appendChild(content);
    card.appendChild(checkboxCorner);

    // Event listeners
    card.addEventListener("click", (e) => {
      if (!(e.target as HTMLElement).closest(".table-checkbox")) {
        this.onCardClick?.(table);
      }
    });

    card.addEventListener("dblclick", () => {
      this.onCardDoubleClick?.(card, table);
    });

    // Drag and drop
    card.draggable = true;
    card.addEventListener("dragstart", (e) => this.onDragStart?.(e, table));
    card.addEventListener("dragend", (e) => this.onDragEnd?.(e));

    return card;
  }

  /**
   * Create thumbnail element
   */
  private createThumbnail(table: Table, tableKey: string): HTMLElement {
    const thumbnail = document.createElement("div");
    thumbnail.className = "table-thumbnail";

    if (table.thumbnail_url) {
      const img = document.createElement("img");
      img.src = table.thumbnail_url;
      img.alt = tableKey;
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
   * Create card content
   */
  private createCardContent(table: Table): HTMLElement {
    const content = document.createElement("div");
    content.className = "table-content";

    // Label (use filename without extension)
    const label = document.createElement("div");
    label.className = "table-label";
    const displayName = table.label || table.file_name.replace(/\.[^/.]+$/, "");
    label.textContent = displayName;

    // Caption (use source/location info)
    const caption = document.createElement("div");
    caption.className = "table-caption";
    caption.textContent = table.caption || table.location || "No location info";

    // Metadata
    const metadata = this.createMetadata(table);

    content.appendChild(label);
    content.appendChild(caption);
    content.appendChild(metadata);

    return content;
  }

  /**
   * Create metadata section
   */
  private createMetadata(table: Table): HTMLElement {
    const metadata = document.createElement("div");
    metadata.className = "table-metadata";

    const fileName = document.createElement("span");
    fileName.className = "table-file-name";
    fileName.textContent = table.file_name;
    metadata.appendChild(fileName);

    if (table.file_size) {
      const dot1 = document.createElement("span");
      dot1.className = "meta-dot";
      dot1.textContent = "•";
      metadata.appendChild(dot1);

      const fileSize = document.createElement("span");
      fileSize.className = "table-file-size";
      const sizeKB = Math.round(table.file_size / 1024);
      fileSize.textContent = `${sizeKB} KB`;
      metadata.appendChild(fileSize);
    }

    if (table.file_type) {
      const dot2 = document.createElement("span");
      dot2.className = "meta-dot";
      dot2.textContent = "•";
      metadata.appendChild(dot2);

      const fileType = document.createElement("span");
      fileType.className = "table-file-type";
      fileType.textContent = table.file_type.toUpperCase();
      metadata.appendChild(fileType);
    }

    return metadata;
  }

  /**
   * Create checkbox corner
   */
  private createCheckboxCorner(tableKey: string): HTMLElement {
    const checkboxCorner = document.createElement("div");
    checkboxCorner.className = "table-checkbox-corner";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "table-checkbox";
    checkbox.checked = this.selectedCards.has(tableKey);
    checkbox.addEventListener("change", (e) => {
      e.stopPropagation();
      this.handleCheckboxChange(tableKey, checkbox.checked);
    });

    checkboxCorner.appendChild(checkbox);
    return checkboxCorner;
  }

  /**
   * Handle checkbox change internally
   */
  private handleCheckboxChange(label: string, checked: boolean): void {
    if (checked) {
      this.selectedCards.add(label);
    } else {
      this.selectedCards.delete(label);
    }

    // Update selected card styling
    const card = document.querySelector(
      `.table-card[data-label="${label}"]`,
    ) as HTMLElement;
    if (card) {
      card.classList.toggle("selected", checked);
    }

    this.onCheckboxChange?.(label, checked);
    console.log(`[TableRenderer] ${label} ${checked ? "selected" : "deselected"}`);
  }

  /**
   * Create expanded view for table
   */
  createExpandedView(table: Table): HTMLElement {
    const expanded = document.createElement("div");
    expanded.className = "table-expanded-view";

    // Preview
    if (table.thumbnail_url) {
      const preview = document.createElement("div");
      preview.className = "table-expanded-preview";
      const img = document.createElement("img");
      img.src = table.thumbnail_url;
      img.alt = table.label || table.file_name;
      preview.appendChild(img);
      expanded.appendChild(preview);
    }

    // Details
    const details = document.createElement("div");
    details.className = "table-expanded-details";

    details.innerHTML = `
      <div><strong>File:</strong> ${table.file_name}</div>
      <div><strong>Path:</strong> ${table.file_path}</div>
      ${table.file_size ? `<div><strong>Size:</strong> ${table.file_size}</div>` : ""}
      ${table.dimensions ? `<div><strong>Dimensions:</strong> ${table.dimensions}</div>` : ""}
    `;

    expanded.appendChild(details);

    return expanded;
  }
}
