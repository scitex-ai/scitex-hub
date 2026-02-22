/**
 * Node Details Panel & Tooltip
 * Renders tooltip on hover and detail panel on click for graph nodes.
 */

import type { NetworkNode, NetworkData, RelatedPaper } from "./types";
import { saveNodeToLibrary } from "./library-bridge";

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

export { escapeHtml };

export class NodeDetailsPanel {
  private tooltipHideTimer: ReturnType<typeof setTimeout> | null = null;
  private onExplore: (node: NetworkNode) => void;

  constructor(onExplore: (node: NetworkNode) => void) {
    this.onExplore = onExplore;
  }

  showTooltip(node: NetworkNode, element: SVGGElement): void {
    if (this.tooltipHideTimer) {
      clearTimeout(this.tooltipHideTimer);
      this.tooltipHideTimer = null;
    }

    let tooltip = document.getElementById("graphTooltip");
    if (!tooltip) {
      tooltip = document.createElement("div");
      tooltip.id = "graphTooltip";
      tooltip.className = "graph-tooltip";
      document.body.appendChild(tooltip);
    }

    tooltip.innerHTML = `
      <div class="tooltip-title">${escapeHtml(node.title)}</div>
      <div class="tooltip-authors">${node.authors.slice(0, 3).join(", ")}${node.authors.length > 3 ? "..." : ""}</div>
      <div class="tooltip-meta">
        <span class="tooltip-year">${node.year}</span>
        ${node.citation_count != null ? `<span class="tooltip-citations"><i class="fas fa-quote-right"></i> ${node.citation_count}</span>` : ""}
        ${node.similarity_score ? `<span class="tooltip-score">Score: ${node.similarity_score.toFixed(1)}</span>` : ""}
      </div>
      <div class="tooltip-hint">Click to view details</div>
    `;

    tooltip.style.display = "";
    const rect = element.getBoundingClientRect();
    tooltip.style.left = `${rect.left + rect.width / 2}px`;
    tooltip.style.top = `${rect.top - 10}px`;
  }

  hideTooltip(): void {
    if (this.tooltipHideTimer) clearTimeout(this.tooltipHideTimer);
    this.tooltipHideTimer = setTimeout(() => {
      const tooltip = document.getElementById("graphTooltip");
      if (tooltip) tooltip.style.display = "none";
    }, 50);
  }

  showDetails(node: NetworkNode): void {
    const panel = document.getElementById("nodeDetailsPanel");
    if (!panel) return;
    panel.classList.remove("hidden");
    panel.innerHTML = `
      <div class="node-details-header">
        <h6>${node.is_seed ? '<i class="fas fa-star"></i> Seed Paper' : '<i class="fas fa-file-alt"></i> Related Paper'}</h6>
        <button class="btn-close-panel" onclick="document.getElementById('nodeDetailsPanel').classList.add('hidden')">
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div class="node-details-content">
        <div class="detail-title">${escapeHtml(node.title)}</div>
        <div class="detail-authors">${node.authors.join(", ")}</div>
        <div class="detail-meta-row">
          <span class="detail-year">Published: ${node.year}</span>
          ${node.citation_count != null ? `<span class="detail-citations"><i class="fas fa-quote-right"></i> ${node.citation_count} citations</span>` : ""}
        </div>
        ${node.similarity_score ? `<div class="detail-score">Similarity: <strong>${node.similarity_score.toFixed(2)}</strong></div>` : ""}
        <div class="detail-doi"><a href="https://doi.org/${node.id}" target="_blank" rel="noopener"><i class="fas fa-external-link-alt"></i> View on DOI.org</a></div>
        <div class="detail-actions">
          ${!node.is_seed ? `<button class="btn-explore-from" data-doi="${node.id}"><i class="fas fa-project-diagram"></i> Explore from here</button>` : ""}
          <button class="btn-save-to-library" data-doi="${node.id}">
            <i class="fas fa-bookmark"></i> Save to Library
          </button>
        </div>
      </div>
    `;
    panel
      .querySelector(".btn-save-to-library")
      ?.addEventListener("click", () => saveNodeToLibrary(node));
    panel.querySelector(".btn-explore-from")?.addEventListener("click", () => {
      this.onExplore(node);
    });
  }

  selectNode(node: NetworkNode): void {
    document
      .querySelectorAll(".graph-node")
      .forEach((el) => el.classList.remove("selected"));
    document.querySelector(`[data-id="${node.id}"]`)?.classList.add("selected");
    this.showDetails(node);
  }

  async fetchRelatedPapers(
    doi: string,
    limit: number,
    url: string,
    fetchWithTimeout: (url: string, ms: number) => Promise<Response>,
    currentData: NetworkData | null,
  ): Promise<void> {
    const container = document.getElementById("relatedPapersList");
    const content = document.getElementById("relatedPapersContent");
    if (!container || !content) return;
    try {
      const fullUrl = `${url}?doi=${encodeURIComponent(doi)}&limit=${limit}`;
      const response = await fetchWithTimeout(fullUrl, 60000);
      if (!response.ok) throw new Error("Failed to fetch related papers");
      const data = await response.json();
      const papers: RelatedPaper[] = data.related || [];
      content.innerHTML =
        papers.length === 0
          ? '<p class="empty-message">No related papers found</p>'
          : papers
              .map(
                (paper, i) => `
            <div class="related-paper-item" data-doi="${paper.id}">
              <div class="paper-rank">${i + 1}</div>
              <div class="paper-info">
                <div class="paper-title">${escapeHtml(paper.title)}</div>
                <div class="paper-meta">
                  <span class="paper-authors">${paper.authors.slice(0, 2).join(", ")}${paper.authors.length > 2 ? " et al." : ""}</span>
                  <span class="paper-year">${paper.year}</span>
                </div>
              </div>
              <div class="paper-score">
                <div class="score-bar"><div class="score-fill" style="width: ${Math.min(100, paper.similarity_score * 2)}%"></div></div>
                <span class="score-value">${paper.similarity_score.toFixed(1)}</span>
              </div>
            </div>
          `,
              )
              .join("");
      content.querySelectorAll(".related-paper-item").forEach((item) => {
        item.addEventListener("click", () => {
          const paperDoi = item.getAttribute("data-doi");
          if (paperDoi && currentData) {
            const node = currentData.nodes.find((n) => n.id === paperDoi);
            if (node) this.selectNode(node);
          }
        });
      });
      container.classList.remove("hidden");
    } catch (err) {
      console.error("Error fetching related papers:", err);
      content.innerHTML =
        '<p class="error-message">Failed to load related papers</p>';
      container.classList.remove("hidden");
    }
  }
}
