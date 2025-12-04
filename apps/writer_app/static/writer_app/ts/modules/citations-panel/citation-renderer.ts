/**
 * Citation Renderer Module
 * Handles rendering of citation cards in the DOM
 */

import { Citation } from "./types.js";

export class CitationRenderer {
  private selectedCards: Set<string> = new Set();

  /**
   * Set selected cards
   */
  public setSelectedCards(selected: Set<string>): void {
    this.selectedCards = selected;
  }

  /**
   * Render citations to container
   */
  public renderCitations(
    citations: Citation[],
    containerId: string = "citations-cards-container",
  ): void {
    const container = document.getElementById(containerId);
    if (!container) {
      console.error(`[CitationRenderer] Container ${containerId} not found`);
      return;
    }

    if (citations.length === 0) {
      container.innerHTML = "";
      return;
    }

    container.innerHTML = citations
      .map((citation) => this.createCardHTML(citation))
      .join("");

    console.log(
      `[CitationRenderer] Rendered ${citations.length} citation cards`,
    );
  }

  /**
   * Create HTML for a single citation card
   */
  private createCardHTML(citation: Citation): string {
    const authors = this.formatAuthors(citation.authors);
    const citationCount = citation.citation_count || 0;
    const citationClass = citationCount > 100 ? "high-citations" : "";
    const isSelected = this.selectedCards.has(citation.key);

    return `
<div class="citation-card ${isSelected ? "selected" : ""}"
     draggable="true"
     data-citation-key="${citation.key}"
     data-citation-title="${this.escapeHtml(citation.title || "")}"
     data-expanded="false">
  <!-- Drag Handle Icon -->
  <div class="citation-drag-handle" title="Drag to insert">
    <i class="fas fa-grip-vertical"></i>
  </div>

  <!-- Upper Right Corner: Metrics & Checkbox -->
  <div class="citation-metrics-corner">
    ${citationCount > 0 ? `<span class="citation-count-badge ${citationClass}">${citationCount} cited</span>` : ""}
    ${citation.impact_factor ? `<span class="impact-factor-badge">IF ${citation.impact_factor}</span>` : ""}
    <input type="checkbox"
           class="citation-checkbox"
           data-citation-key="${citation.key}"
           ${isSelected ? "checked" : ""}
           title="Select for bulk insert">
  </div>

  <!-- Compact View (Always Visible) -->
  <div class="citation-compact-view">
    <!-- Line 1: Key | Authors | Journal • Year -->
    <div class="citation-meta-line">
      <span class="citation-key">${this.escapeHtml(citation.key)}</span>
      <span class="citation-authors-inline">${this.escapeHtml(authors)}</span>
      ${citation.journal ? `<span class="meta-dot">•</span>` : ""}
      ${citation.journal ? `<span class="citation-journal-inline">${this.escapeHtml(citation.journal)}</span>` : ""}
      ${citation.year ? `<span class="meta-dot">•</span><span class="citation-year">${citation.year}</span>` : ""}
    </div>
    <!-- Line 2: Title -->
    <div class="citation-title-line">${this.escapeHtml(citation.title || "Untitled")}</div>
  </div>

  <!-- Expanded View (Hidden by default, shown on double-click) -->
  <div class="citation-expanded-view" style="display: none;">
    ${citation.abstract ? `<div class="citation-abstract"><strong>Abstract:</strong> ${this.escapeHtml(citation.abstract)}</div>` : ""}
    ${citation.doi ? `<div class="citation-doi"><strong>DOI:</strong> <a href="https://doi.org/${this.escapeHtml(citation.doi)}" target="_blank">${this.escapeHtml(citation.doi)}</a></div>` : ""}
    ${citation.url ? `<div class="citation-url"><strong>URL:</strong> <a href="${this.escapeHtml(citation.url)}" target="_blank">${this.escapeHtml(citation.url)}</a></div>` : ""}
    ${citation.publisher ? `<div class="citation-publisher"><strong>Publisher:</strong> ${this.escapeHtml(citation.publisher)}</div>` : ""}
  </div>
</div>`;
  }

  /**
   * Format authors for display
   */
  private formatAuthors(authors: string[] | undefined): string {
    if (!Array.isArray(authors) || authors.length === 0) {
      return "Unknown authors";
    }

    const displayAuthors = authors.slice(0, 3).join(", ");
    return authors.length > 3 ? `${displayAuthors} et al.` : displayAuthors;
  }

  /**
   * Escape HTML
   */
  private escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}
