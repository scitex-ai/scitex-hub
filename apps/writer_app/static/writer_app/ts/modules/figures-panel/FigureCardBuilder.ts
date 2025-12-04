/**
 * Figure Card Builder
 * Handles creation of figure cards for the figures panel
 */

import type { Figure } from "../figures-panel.js";

export class FigureCardBuilder {
  /**
   * Create a figure card element
   */
  static createCard(
    figure: Figure,
    selectedCards: Set<string>,
    handlers: {
      onCheckboxChange: (label: string, checked: boolean) => void;
      onCardClick: (figure: Figure) => void;
      onCardDoubleClick: (card: HTMLElement, figure: Figure) => void;
      onDragStart: (e: DragEvent, figure: Figure) => void;
      onDragEnd: (e: DragEvent) => void;
    },
  ): HTMLElement {
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
    const checkboxCorner = this.createCheckboxCorner(
      figureKey,
      selectedCards,
      handlers.onCheckboxChange,
    );

    // Assemble card
    card.appendChild(dragHandle);
    card.appendChild(thumbnail);
    card.appendChild(content);
    card.appendChild(checkboxCorner);

    // Event listeners
    card.addEventListener("click", (e) => {
      if (!(e.target as HTMLElement).closest(".figure-checkbox")) {
        handlers.onCardClick(figure);
      }
    });

    card.addEventListener("dblclick", () => {
      handlers.onCardDoubleClick(card, figure);
    });

    // Drag and drop
    card.draggable = true;
    card.addEventListener("dragstart", (e) => handlers.onDragStart(e, figure));
    card.addEventListener("dragend", (e) => handlers.onDragEnd(e));

    return card;
  }

  /**
   * Create thumbnail element
   */
  private static createThumbnail(
    figure: Figure,
    figureKey: string,
  ): HTMLElement {
    const thumbnail = document.createElement("div");
    thumbnail.className = "figure-thumbnail";

    if (figure.thumbnail_url) {
      const img = document.createElement("img");
      img.src = figure.thumbnail_url;
      img.alt = figureKey;
      img.onerror = () => {
        // Fallback to icon if image fails to load
        thumbnail.innerHTML = '<i class="fas fa-image"></i>';
      };
      thumbnail.appendChild(img);
    } else {
      thumbnail.innerHTML = '<i class="fas fa-image"></i>';
    }

    return thumbnail;
  }

  /**
   * Create content section
   */
  private static createContent(figure: Figure): HTMLElement {
    const content = document.createElement("div");
    content.className = "figure-content";

    // Label (use filename without extension)
    const label = document.createElement("div");
    label.className = "figure-label";
    const displayName =
      figure.label || figure.file_name.replace(/\.[^/.]+$/, "");
    label.textContent = displayName;

    // Caption (use source/location info)
    const caption = document.createElement("div");
    caption.className = "figure-caption";
    caption.textContent =
      figure.caption || figure.location || "No location info";

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
  private static createMetadata(figure: Figure): HTMLElement {
    const metadata = document.createElement("div");
    metadata.className = "figure-metadata";

    const fileName = document.createElement("span");
    fileName.className = "figure-file-name";
    fileName.textContent = figure.file_name;
    metadata.appendChild(fileName);

    if (figure.file_size) {
      const dot1 = document.createElement("span");
      dot1.className = "meta-dot";
      dot1.textContent = "•";
      metadata.appendChild(dot1);

      const fileSize = document.createElement("span");
      fileSize.className = "figure-file-size";
      // Format bytes to KB
      const sizeKB = Math.round(figure.file_size / 1024);
      fileSize.textContent = `${sizeKB} KB`;
      metadata.appendChild(fileSize);
    }

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
  private static createCheckboxCorner(
    figureKey: string,
    selectedCards: Set<string>,
    onCheckboxChange: (label: string, checked: boolean) => void,
  ): HTMLElement {
    const checkboxCorner = document.createElement("div");
    checkboxCorner.className = "figure-checkbox-corner";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "figure-checkbox";
    checkbox.checked = selectedCards.has(figureKey);
    checkbox.addEventListener("change", (e) => {
      e.stopPropagation();
      onCheckboxChange(figureKey, checkbox.checked);
    });

    checkboxCorner.appendChild(checkbox);

    return checkboxCorner;
  }
}
