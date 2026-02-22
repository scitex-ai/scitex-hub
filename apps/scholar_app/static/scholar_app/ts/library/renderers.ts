/**
 * HTML rendering functions for Scholar Library
 */

import { API, LibraryCollection, LibraryPaper, LibraryStats } from "./types";
import { LibraryAPI } from "./api";

export class LibraryRenderers {
  static escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
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

  static renderPaperTable(
    papers: LibraryPaper[],
    selectedPaperId: string | null,
    searchQuery: string,
    onPaperClick: (paperId: string) => void,
    onSort: (column: string) => void,
    sortColumn: string,
    sortAsc: boolean,
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

    const arrow = (col: string) => {
      if (sortColumn !== col) return "";
      return sortAsc ? " \u25B2" : " \u25BC";
    };

    const headerHtml = `
      <thead>
        <tr>
          <th class="library-table-th sortable" data-sort="title">Title${arrow("title")}</th>
          <th class="library-table-th sortable" data-sort="authors">Authors${arrow("authors")}</th>
          <th class="library-table-th sortable" data-sort="year">Year${arrow("year")}</th>
          <th class="library-table-th sortable" data-sort="journal">Journal${arrow("journal")}</th>
          <th class="library-table-th sortable" data-sort="reading_status">Status${arrow("reading_status")}</th>
          <th class="library-table-th sortable" data-sort="importance_rating">Rating${arrow("importance_rating")}</th>
        </tr>
      </thead>
    `;

    const rowsHtml = papers
      .map((paper) => {
        const isSelected = paper.id === selectedPaperId;
        const authors = paper.authors
          ? this.truncateText(paper.authors, 30)
          : "";
        const journal = paper.journal
          ? this.truncateText(paper.journal, 25)
          : "";
        return `
          <tr class="library-table-row ${isSelected ? "selected" : ""}" data-paper-id="${paper.id}">
            <td class="library-table-td library-table-title">${this.escapeHtml(this.truncateText(paper.title, 60))}</td>
            <td class="library-table-td">${this.escapeHtml(authors)}</td>
            <td class="library-table-td">${paper.year || ""}</td>
            <td class="library-table-td">${this.escapeHtml(journal)}</td>
            <td class="library-table-td">${this.getStatusBadgeHtml(paper.reading_status)}</td>
            <td class="library-table-td">${this.getCompactStarsHtml(paper.importance_rating)}</td>
          </tr>
        `;
      })
      .join("");

    listContainer.innerHTML = `
      <table class="library-table">
        ${headerHtml}
        <tbody>${rowsHtml}</tbody>
      </table>
    `;

    listContainer.querySelectorAll(".library-table-row").forEach((row) => {
      row.addEventListener("click", () => {
        const paperId = row.getAttribute("data-paper-id");
        if (paperId) onPaperClick(paperId);
      });
    });

    listContainer
      .querySelectorAll(".library-table-th.sortable")
      .forEach((th) => {
        th.addEventListener("click", () => {
          const col = th.getAttribute("data-sort");
          if (col) onSort(col);
        });
      });
  }

  static truncateText(text: string, maxLen: number): string {
    if (text.length <= maxLen) return text;
    return text.slice(0, maxLen - 1) + "\u2026";
  }

  static getCompactStarsHtml(rating: number): string {
    if (!rating) return '<span class="library-rating-compact">-</span>';
    return `<span class="library-rating-compact">${"\u2605".repeat(rating)}</span>`;
  }

  static renderCollectionSidebar(
    collections: LibraryCollection[],
    selectedCollectionId: string | null,
    totalPaperCount: number,
    onCollectionClick: (collectionId: string | null) => void,
  ): void {
    const list = document.getElementById("library-sidebar-list");
    if (!list) return;

    const allActive = selectedCollectionId === null ? "active" : "";
    let html = `
      <div class="library-sidebar-item ${allActive}" data-collection-id="all">
        <i class="fas fa-layer-group"></i>
        <span class="library-sidebar-item-name">All Papers</span>
        <span class="library-sidebar-item-count">${totalPaperCount}</span>
      </div>
    `;

    for (const col of collections) {
      const active = col.id === selectedCollectionId ? "active" : "";
      const icon = col.icon || "fas fa-folder";
      html += `
        <div class="library-sidebar-item ${active}" data-collection-id="${col.id}">
          <i class="${this.escapeHtml(icon)}"></i>
          <span class="library-sidebar-item-name">${this.escapeHtml(col.name)}</span>
          <span class="library-sidebar-item-count">${col.paper_count}</span>
        </div>
      `;
    }

    list.innerHTML = html;

    list.querySelectorAll(".library-sidebar-item").forEach((item) => {
      item.addEventListener("click", () => {
        const id = item.getAttribute("data-collection-id");
        onCollectionClick(id === "all" ? null : id);
      });
    });
  }

  static renderPaperCard(
    paper: LibraryPaper,
    selectedPaperId: string | null,
  ): string {
    const isSelected = paper.id === selectedPaperId;
    return `
      <div class="library-paper-card ${isSelected ? "selected" : ""}" data-paper-id="${paper.id}">
        <div class="library-paper-title">${this.escapeHtml(paper.title)}</div>
        <div class="library-paper-meta">
          ${paper.authors ? `<span>${this.escapeHtml(paper.authors)}</span>` : ""}
          ${paper.journal ? `<span>${this.escapeHtml(paper.journal)}</span>` : ""}
          ${paper.year ? `<span>${paper.year}</span>` : ""}
        </div>
        <div class="library-paper-badges">
          ${this.getStatusBadgeHtml(paper.reading_status)}
          ${this.getImportanceStarsHtml(paper.importance_rating)}
          ${paper.tags?.map((tag) => `<span class="library-tag">${this.escapeHtml(tag)}</span>`).join("") || ""}
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
        <div class="library-detail-title">${this.escapeHtml(paper.title)}</div>
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
            <div class="library-detail-abstract">${this.escapeHtml(paper.abstract)}</div>
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
                 value="${paper.tags?.join(", ") || ""}"
                 placeholder="e.g., machine-learning, important, follow-up">
        </div>

        <div class="library-detail-section">
          <div class="library-detail-label">Personal Notes</div>
          <textarea class="library-notes-textarea" id="library-notes-textarea"
                    placeholder="Add your notes here...">${this.escapeHtml(paper.personal_notes || "")}</textarea>
        </div>

        ${
          paper.pdf_path
            ? `
        <div class="library-detail-section">
          <div class="library-detail-label">PDF</div>
          <div id="library-pdf-container">
            <button class="library-detail-btn" id="library-view-pdf-btn">
              <i class="fas fa-file-pdf"></i> View PDF
            </button>
          </div>
        </div>`
            : ""
        }

        <div class="library-detail-section">
          <div class="library-detail-label">
            BibTeX
            <button class="library-detail-btn-inline" id="library-bibtex-toggle">
              <i class="fas fa-code"></i>
            </button>
          </div>
          <pre class="library-bibtex-viewer hidden" id="library-bibtex-content">Loading...</pre>
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

    // BibTeX toggle — lazy fetch on first show
    const bibtexToggle = document.getElementById("library-bibtex-toggle");
    const bibtexContent = document.getElementById(
      "library-bibtex-content",
    ) as HTMLPreElement | null;
    let bibtexLoaded = false;
    if (bibtexToggle && bibtexContent) {
      bibtexToggle.addEventListener("click", async () => {
        bibtexContent.classList.toggle("hidden");
        if (!bibtexContent.classList.contains("hidden") && !bibtexLoaded) {
          bibtexLoaded = true;
          try {
            const bibtex = await LibraryAPI.fetchPaperBibtex(paper.paper_id);
            bibtexContent.textContent = bibtex || "(no BibTeX available)";
          } catch {
            bibtexContent.textContent = "(failed to load BibTeX)";
          }
        }
      });
    }

    // PDF inline viewer
    const viewPdfBtn = document.getElementById("library-view-pdf-btn");
    if (viewPdfBtn && paper.pdf_path) {
      viewPdfBtn.addEventListener("click", () => {
        const container = document.getElementById("library-pdf-container");
        if (!container) return;
        container.innerHTML = `
          <iframe
            class="library-pdf-viewer"
            src="${API.servePdf(paper.pdf_path!)}"
            title="PDF Viewer">
          </iframe>`;
      });
    }
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
