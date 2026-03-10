/**
 * HTML rendering functions for Scholar Library
 */

import { LibraryPaper, LibraryStats } from "./types";

export class LibraryRenderers {
  private static readonly SAFE_TAGS = new Set([
    "i",
    "b",
    "em",
    "strong",
    "sub",
    "sup",
    "scp",
  ]);

  static escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  /** Allow safe scientific markup (i, b, em, strong, sub, sup, scp), strip everything else. */
  static sanitizeHtml(text: string): string {
    // Decode entity-encoded safe tags (common in CrossRef/PubMed metadata)
    const safeTagRe = /&lt;(\/?(?:i|b|em|strong|sub|sup|scp))&gt;/gi;
    const decoded = text.replace(safeTagRe, "<$1>");

    const div = document.createElement("div");
    div.innerHTML = decoded;
    const walker = document.createTreeWalker(div, NodeFilter.SHOW_ELEMENT);
    const toUnwrap: Element[] = [];
    while (walker.nextNode()) {
      const el = walker.currentNode as Element;
      if (!this.SAFE_TAGS.has(el.tagName.toLowerCase())) {
        toUnwrap.push(el);
      }
      // Strip all attributes from any tag
      while (el.attributes.length > 0)
        el.removeAttribute(el.attributes[0].name);
    }
    for (const el of toUnwrap) el.replaceWith(...Array.from(el.childNodes));
    return div.innerHTML;
  }

  static renderStats(
    stats: LibraryStats,
    onStatClick: (filter: string | null) => void,
  ): void {
    const statsBar = document.getElementById("library-stats-bar");
    if (!statsBar) return;

    statsBar.innerHTML = `
      <div class="library-stat" data-filter="all">
        <div class="library-stat-count">${stats.total}</div>
        <div class="library-stat-label">Total</div>
      </div>
      <div class="library-stat" data-filter="to_read">
        <div class="library-stat-count">${stats.to_read}</div>
        <div class="library-stat-label">To Read</div>
      </div>
      <div class="library-stat" data-filter="reading">
        <div class="library-stat-count">${stats.reading}</div>
        <div class="library-stat-label">Reading</div>
      </div>
      <div class="library-stat" data-filter="read">
        <div class="library-stat-count">${stats.read}</div>
        <div class="library-stat-label">Read</div>
      </div>
      <div class="library-stat" data-filter="referenced">
        <div class="library-stat-count">${stats.referenced}</div>
        <div class="library-stat-label">Referenced</div>
      </div>
      <div class="library-stat" data-filter="favorite">
        <div class="library-stat-count">${stats.favorite}</div>
        <div class="library-stat-label">Favorites</div>
      </div>
    `;

    statsBar.querySelectorAll(".library-stat").forEach((stat) => {
      stat.addEventListener("click", () => {
        const filter = stat.getAttribute("data-filter");
        onStatClick(filter === "all" ? null : filter);
      });
    });
  }

  static updateActiveStatFilter(filter: string | null): void {
    document.querySelectorAll(".library-stat").forEach((stat) => {
      const statFilter = stat.getAttribute("data-filter");
      if ((filter === null && statFilter === "all") || statFilter === filter) {
        stat.classList.add("active");
      } else {
        stat.classList.remove("active");
      }
    });
  }

  static renderPaperList(
    papers: LibraryPaper[],
    selectedPaperId: string | null,
    searchQuery: string,
    onPaperClick: (paperId: string) => void,
  ): void {
    const listContainer = document.getElementById("library-papers-list");
    if (!listContainer) return;

    if (papers.length === 0) {
      listContainer.innerHTML = `
        <div class="library-empty-state">
          <i class="fas fa-book-open"></i>
          <div class="library-empty-state-title">No papers found</div>
          <div class="library-empty-state-description">
            ${searchQuery ? "Try adjusting your search or filters" : "Start by importing papers from BibTeX or adding them manually"}
          </div>
        </div>
      `;
      return;
    }

    listContainer.innerHTML = papers
      .map((paper) => this.renderPaperCard(paper, selectedPaperId))
      .join("");

    listContainer.querySelectorAll(".library-paper-card").forEach((card) => {
      card.addEventListener("click", () => {
        const paperId = card.getAttribute("data-paper-id");
        if (paperId) onPaperClick(paperId);
      });
    });
  }

  /** Normalize tags to array (API may send string or string[]) */
  private static tagsToArray(
    tags: string | string[] | undefined | null,
  ): string[] {
    if (!tags) return [];
    if (Array.isArray(tags)) return tags;
    return tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
  }

  static truncateText(text: string, maxLen: number): string {
    if (text.length <= maxLen) return text;
    return text.slice(0, maxLen - 1) + "\u2026";
  }

  static getCompactStarsHtml(rating: number): string {
    if (!rating) return '<span class="library-rating-compact">-</span>';
    return `<span class="library-rating-compact">${"\u2605".repeat(rating)}</span>`;
  }

  static renderPaperCard(
    paper: LibraryPaper,
    selectedPaperId: string | null,
  ): string {
    const isSelected = paper.id === selectedPaperId;
    return `
      <div class="library-paper-card ${isSelected ? "selected" : ""}" data-paper-id="${paper.id}">
        <div class="library-paper-title">${this.sanitizeHtml(paper.title)}</div>
        <div class="library-paper-meta">
          ${paper.authors ? `<span>${this.escapeHtml(paper.authors)}</span>` : ""}
          ${paper.journal ? `<span>${this.escapeHtml(paper.journal)}</span>` : ""}
          ${paper.year ? `<span>${paper.year}</span>` : ""}
        </div>
        <div class="library-paper-badges">
          ${this.getStatusBadgeHtml(paper.reading_status)}
          ${this.getImportanceStarsHtml(paper.importance_rating)}
          ${this.tagsToArray(paper.tags)
            .map(
              (tag) =>
                `<span class="library-tag">${this.escapeHtml(tag)}</span>`,
            )
            .join("")}
        </div>
      </div>
    `;
  }

  static getStatusBadgeHtml(status: string): string {
    const statusLabels: Record<string, string> = {
      to_read: "To Read",
      reading: "Reading",
      read: "Read",
      referenced: "Referenced",
    };
    const label = statusLabels[status] || status;
    return `<span class="library-status-badge ${status}">${label}</span>`;
  }

  static getImportanceStarsHtml(rating: number): string {
    const stars = [];
    for (let i = 1; i <= 5; i++) {
      stars.push(
        `<i class="fas fa-star ${i <= rating ? "star-filled" : "star-empty"}"></i>`,
      );
    }
    return `<span class="library-importance-stars">${stars.join("")}</span>`;
  }

  static renderPaperDetails(
    paper: LibraryPaper,
    onSave: () => void,
    onRemove: () => void,
    onExport: () => void,
  ): void {
    const detailsPanel = document.getElementById("library-paper-details");
    if (!detailsPanel) return;

    // Show the details panel and hide empty state
    detailsPanel.hidden = false;
    const emptyState = document.getElementById("library-details-empty");
    if (emptyState) emptyState.hidden = true;

    detailsPanel.innerHTML = `
      <div class="library-detail-header">
        <div class="library-detail-title">${this.sanitizeHtml(paper.title)}</div>
        <div class="library-detail-meta">
          ${paper.authors ? `<div>${this.escapeHtml(paper.authors)}</div>` : ""}
          ${paper.journal ? `<div>${this.escapeHtml(paper.journal)}${paper.year ? `, ${paper.year}` : ""}</div>` : ""}
          ${paper.doi ? `<div>DOI: ${this.escapeHtml(paper.doi)}</div>` : ""}
        </div>
      </div>

      <div class="library-detail-body">
        ${
          paper.abstract
            ? `
          <div class="library-detail-section">
            <div class="library-detail-label">Abstract</div>
            <div class="library-detail-abstract">${this.sanitizeHtml(paper.abstract)}</div>
          </div>
        `
            : ""
        }

        <div class="library-detail-section">
          <div class="library-detail-label">Reading Status</div>
          <select class="library-status-select" id="library-status-select">
            <option value="to_read" ${paper.reading_status === "to_read" ? "selected" : ""}>To Read</option>
            <option value="reading" ${paper.reading_status === "reading" ? "selected" : ""}>Reading</option>
            <option value="read" ${paper.reading_status === "read" ? "selected" : ""}>Read</option>
            <option value="referenced" ${paper.reading_status === "referenced" ? "selected" : ""}>Referenced</option>
          </select>
        </div>

        <div class="library-detail-section">
          <div class="library-detail-label">Importance Rating</div>
          <select class="library-importance-select" id="library-importance-select">
            ${[1, 2, 3, 4, 5]
              .map(
                (i) =>
                  `<option value="${i}" ${paper.importance_rating === i ? "selected" : ""}>${"★".repeat(i)}${"☆".repeat(5 - i)}</option>`,
              )
              .join("")}
          </select>
        </div>

        <div class="library-detail-section">
          <div class="library-detail-label">Tags (comma-separated)</div>
          <input type="text" class="library-tags-input" id="library-tags-input"
                 value="${this.tagsToArray(paper.tags).join(", ")}"
                 placeholder="e.g., machine-learning, important, follow-up">
        </div>

        <div class="library-detail-section">
          <div class="library-detail-label">Personal Notes</div>
          <textarea class="library-notes-textarea" id="library-notes-textarea"
                    placeholder="Add your notes here...">${this.escapeHtml(paper.personal_notes || "")}</textarea>
        </div>

        <button class="library-save-btn" id="library-save-btn">
          <i class="fas fa-save"></i> Save Changes
        </button>
      </div>

      <div class="library-detail-actions">
        <button class="library-detail-btn" id="library-export-single-btn">
          <i class="fas fa-file-export"></i> Export BibTeX
        </button>
        <button class="library-detail-btn danger" id="library-remove-paper-btn">
          <i class="fas fa-trash"></i> Remove
        </button>
      </div>
    `;

    const saveBtn = document.getElementById("library-save-btn");
    if (saveBtn) saveBtn.addEventListener("click", onSave);

    const removeBtn = document.getElementById("library-remove-paper-btn");
    if (removeBtn) removeBtn.addEventListener("click", onRemove);

    const exportSingleBtn = document.getElementById(
      "library-export-single-btn",
    );
    if (exportSingleBtn) exportSingleBtn.addEventListener("click", onExport);
  }

  static renderEmptyDetailsPanel(): void {
    const detailsPanel = document.getElementById("library-paper-details");
    if (detailsPanel) {
      detailsPanel.hidden = true;
      detailsPanel.innerHTML = "";
    }
    const emptyState = document.getElementById("library-details-empty");
    if (emptyState) emptyState.hidden = false;
  }
}
