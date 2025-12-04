/**
 * Figure Preview Module
 * Handles expanded view and preview functionality
 */

import type { Figure } from "./figures-list.js";

export class FigurePreview {
  constructor() {
    console.log("[FigurePreview] Initialized");
  }

  /**
   * Handle card double click to show/hide expanded view
   */
  handleDoubleClick(card: HTMLElement, figure: Figure): void {
    const figureKey = figure.label || figure.file_name;
    console.log("[FigurePreview] Card double-clicked:", figureKey);

    // Toggle expanded view
    let expandedView = card.querySelector(".figure-expanded-view") as HTMLElement;

    if (expandedView) {
      expandedView.remove();
    } else {
      expandedView = this.createExpandedView(figure);
      card.appendChild(expandedView);
    }
  }

  /**
   * Create expanded view for figure
   */
  private createExpandedView(figure: Figure): HTMLElement {
    const expanded = document.createElement("div");
    expanded.className = "figure-expanded-view";

    // Preview section
    if (figure.thumbnail_url) {
      const preview = this.createPreviewSection(figure);
      expanded.appendChild(preview);
    }

    // Details section
    const details = this.createDetailsSection(figure);
    expanded.appendChild(details);

    return expanded;
  }

  /**
   * Create preview section with image
   */
  private createPreviewSection(figure: Figure): HTMLElement {
    const preview = document.createElement("div");
    preview.className = "figure-expanded-preview";

    const img = document.createElement("img");
    img.src = figure.thumbnail_url!;
    img.alt = figure.label || figure.file_name;
    img.onerror = () => {
      preview.innerHTML = '<i class="fas fa-image"></i><p>Image not available</p>';
    };

    preview.appendChild(img);
    return preview;
  }

  /**
   * Create details section with metadata
   */
  private createDetailsSection(figure: Figure): HTMLElement {
    const details = document.createElement("div");
    details.className = "figure-expanded-details";

    // Build details HTML
    const detailsHTML: string[] = [
      `<div><strong>File:</strong> ${figure.file_name}</div>`,
      `<div><strong>Path:</strong> ${figure.file_path}</div>`,
    ];

    if (figure.file_size) {
      const sizeKB = Math.round(figure.file_size / 1024);
      detailsHTML.push(`<div><strong>Size:</strong> ${sizeKB} KB</div>`);
    }

    if (figure.dimensions) {
      detailsHTML.push(`<div><strong>Dimensions:</strong> ${figure.dimensions}</div>`);
    }

    if (figure.file_type) {
      detailsHTML.push(
        `<div><strong>Type:</strong> ${figure.file_type.toUpperCase()}</div>`,
      );
    }

    if (figure.caption) {
      detailsHTML.push(`<div><strong>Caption:</strong> ${figure.caption}</div>`);
    }

    if (figure.location) {
      detailsHTML.push(`<div><strong>Location:</strong> ${figure.location}</div>`);
    }

    if (figure.tags && figure.tags.length > 0) {
      detailsHTML.push(`<div><strong>Tags:</strong> ${figure.tags.join(", ")}</div>`);
    }

    details.innerHTML = detailsHTML.join("");
    return details;
  }

  /**
   * Show preview modal (alternative to expanded view)
   */
  showPreviewModal(figure: Figure): void {
    // Create modal overlay
    const modal = document.createElement("div");
    modal.className = "figure-preview-modal";
    modal.style.display = "flex";

    // Modal content
    const modalContent = document.createElement("div");
    modalContent.className = "figure-preview-modal-content";

    // Close button
    const closeBtn = document.createElement("button");
    closeBtn.className = "figure-preview-modal-close";
    closeBtn.innerHTML = '<i class="fas fa-times"></i>';
    closeBtn.onclick = () => modal.remove();

    // Image
    const img = document.createElement("img");
    img.src = figure.thumbnail_url || figure.file_path;
    img.alt = figure.label || figure.file_name;
    img.style.maxWidth = "100%";
    img.style.maxHeight = "80vh";

    // Details
    const details = this.createDetailsSection(figure);

    modalContent.appendChild(closeBtn);
    modalContent.appendChild(img);
    modalContent.appendChild(details);
    modal.appendChild(modalContent);

    // Close on overlay click
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    });

    // Close on Escape key
    const escapeHandler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        modal.remove();
        document.removeEventListener("keydown", escapeHandler);
      }
    };
    document.addEventListener("keydown", escapeHandler);

    document.body.appendChild(modal);
  }
}
