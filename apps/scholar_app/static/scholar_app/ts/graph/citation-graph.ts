/**
 * Citation Graph Visualization
 * Interactive force-directed network visualization for citation relationships
 *
 * Refactored: Extracted ForceSimulation, GraphRenderer, and types for maintainability.
 */

import type {
  CitationGraphConfig,
  NetworkNode,
  NetworkEdge,
  NetworkData,
  RelatedPaper,
  Transform,
} from "./types";
import { GraphRenderer } from "./GraphRenderer";
import { saveNodeToLibrary } from "./library-bridge";

class CitationGraphManager {
  private config: CitationGraphConfig;
  private currentData: NetworkData | null = null;
  private renderer: GraphRenderer;
  private transform: Transform = { x: 0, y: 0, k: 1 };
  private isDragging = false;
  private selectedNode: NetworkNode | null = null;

  constructor() {
    const config = window.CITATION_GRAPH_CONFIG;
    if (!config) {
      console.error("Citation graph config not found");
      return;
    }
    this.config = config;

    this.renderer = new GraphRenderer({
      onNodeHover: (node, el) => this.showNodeTooltip(node, el),
      onNodeLeave: () => this.hideNodeTooltip(),
      onNodeClick: (node) => this.selectNode(node),
      onNodeDragStart: (e, node) => this.startNodeDrag(e, node),
      getDepthColor: () => "#3B82F6",
    });

    this.init();
  }

  private init(): void {
    this.bindEvents();
    this.checkServiceHealth();
  }

  private bindEvents(): void {
    const form = document.getElementById("graphForm");
    form?.addEventListener("submit", (e) => this.handleSubmit(e));

    document
      .getElementById("resetZoomBtn")
      ?.addEventListener("click", () => this.resetView());
    document
      .getElementById("downloadSvgBtn")
      ?.addEventListener("click", () => this.downloadSvg());
    document
      .getElementById("fitViewBtn")
      ?.addEventListener("click", () => this.fitToView());
  }

  private async fetchWithTimeout(
    url: string,
    timeoutMs: number = 120000,
  ): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, { signal: controller.signal });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === "AbortError") {
        throw new Error(`Request timed out after ${timeoutMs / 1000} seconds`);
      }
      throw error;
    }
  }

  private async checkServiceHealth(): Promise<void> {
    const statusEl = document.getElementById("serviceStatus");
    if (!statusEl) return;

    try {
      const response = await fetch(this.config.urls.health);
      const data = await response.json();

      statusEl.innerHTML =
        data.status === "healthy"
          ? `<div class="status-indicator status-healthy"><i class="fas fa-check-circle"></i><span>Service available</span></div>`
          : `<div class="status-indicator status-warning"><i class="fas fa-exclamation-triangle"></i><span>Service limited</span></div><small class="status-detail">${data.error || "Unknown status"}</small>`;
    } catch {
      statusEl.innerHTML = `<div class="status-indicator status-error"><i class="fas fa-times-circle"></i><span>Service unavailable</span></div><small class="status-detail">Could not connect to citation graph service</small>`;
    }
  }

  private async handleSubmit(e: Event): Promise<void> {
    e.preventDefault();

    const doiInput = document.getElementById("doiInput") as HTMLInputElement;
    const topNSelect = document.getElementById("topN") as HTMLSelectElement;

    if (!doiInput?.value) {
      this.showError("Please enter a DOI");
      return;
    }

    const doi = doiInput.value.trim();
    const topN = parseInt(topNSelect?.value || "20", 10);

    this.showLoading(true);
    this.hideError();

    try {
      const networkUrl = `${this.config.urls.buildNetwork}?doi=${encodeURIComponent(doi)}&top_n=${topN}`;
      const networkResponse = await this.fetchWithTimeout(networkUrl, 120000);

      if (!networkResponse.ok) {
        const errorData = await networkResponse.json();
        throw new Error(errorData.error || "Failed to build network");
      }

      const networkData: NetworkData = await networkResponse.json();
      this.currentData = networkData;

      this.renderGraph(networkData);
      await this.fetchRelatedPapers(doi, topN);
    } catch (err) {
      console.error("Error building citation network:", err);
      this.showError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      this.showLoading(false);
    }
  }

  private renderGraph(data: NetworkData): void {
    const container = document.getElementById("graphVisualization");
    const canvas = document.getElementById("graphCanvas");

    if (!container || !canvas) return;

    container.classList.remove("hidden");

    const titleEl = document.getElementById("graphTitle");
    if (titleEl) {
      const seedNode = data.nodes.find((n) => n.is_seed);
      titleEl.textContent = seedNode
        ? `Network: ${seedNode.title.substring(0, 50)}...`
        : "Citation Network";
    }

    this.renderer.render(canvas, data.nodes, data.edges);
    this.setupZoomPan(canvas);
  }

  private setupZoomPan(container: HTMLElement): void {
    const svg = this.renderer.getSvg();
    if (!svg) return;

    let isPanning = false;
    let startX = 0;
    let startY = 0;

    svg.addEventListener("wheel", (e) => {
      e.preventDefault();
      const scaleFactor = e.deltaY > 0 ? 0.9 : 1.1;
      const rect = svg.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const newK = Math.max(0.1, Math.min(5, this.transform.k * scaleFactor));
      this.transform.x =
        mouseX - (mouseX - this.transform.x) * (newK / this.transform.k);
      this.transform.y =
        mouseY - (mouseY - this.transform.y) * (newK / this.transform.k);
      this.transform.k = newK;

      this.renderer.applyTransform(this.transform);
    });

    svg.addEventListener("mousedown", (e) => {
      if (e.target === svg || (e.target as Element).closest(".graph-edges")) {
        isPanning = true;
        startX = e.clientX - this.transform.x;
        startY = e.clientY - this.transform.y;
        svg.style.cursor = "grabbing";
      }
    });

    svg.addEventListener("mousemove", (e) => {
      if (isPanning && !this.isDragging) {
        this.transform.x = e.clientX - startX;
        this.transform.y = e.clientY - startY;
        this.renderer.applyTransform(this.transform);
      }
    });

    svg.addEventListener("mouseup", () => {
      isPanning = false;
      svg.style.cursor = "grab";
    });
    svg.addEventListener("mouseleave", () => {
      isPanning = false;
      svg.style.cursor = "grab";
    });
    svg.style.cursor = "grab";
  }

  private startNodeDrag(e: MouseEvent, node: NetworkNode): void {
    e.stopPropagation();
    this.isDragging = true;

    const svg = this.renderer.getSvg()!;
    const rect = svg.getBoundingClientRect();

    const onMouseMove = (moveEvent: MouseEvent) => {
      const x =
        (moveEvent.clientX - rect.left - this.transform.x) / this.transform.k;
      const y =
        (moveEvent.clientY - rect.top - this.transform.y) / this.transform.k;
      node.fx = x;
      node.fy = y;
      node.x = x;
      node.y = y;
      this.renderer.getSimulation()?.reheat();
    };

    const onMouseUp = () => {
      this.isDragging = false;
      if (!node.is_seed) {
        node.fx = null;
        node.fy = null;
      }
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  }

  private showNodeTooltip(node: NetworkNode, element: SVGGElement): void {
    document.getElementById("graphTooltip")?.remove();

    const tooltip = document.createElement("div");
    tooltip.id = "graphTooltip";
    tooltip.className = "graph-tooltip";
    tooltip.innerHTML = `
      <div class="tooltip-title">${this.escapeHtml(node.title)}</div>
      <div class="tooltip-authors">${node.authors.slice(0, 3).join(", ")}${node.authors.length > 3 ? "..." : ""}</div>
      <div class="tooltip-meta">
        <span class="tooltip-year">${node.year}</span>
        ${node.similarity_score ? `<span class="tooltip-score">Score: ${node.similarity_score.toFixed(1)}</span>` : ""}
      </div>
      <div class="tooltip-hint">Click to view details</div>
    `;

    document.body.appendChild(tooltip);
    const rect = element.getBoundingClientRect();
    tooltip.style.left = `${rect.left + rect.width / 2}px`;
    tooltip.style.top = `${rect.top - 10}px`;
  }

  private hideNodeTooltip(): void {
    document.getElementById("graphTooltip")?.remove();
  }

  private selectNode(node: NetworkNode): void {
    this.selectedNode = node;
    document
      .querySelectorAll(".graph-node")
      .forEach((el) => el.classList.remove("selected"));
    document.querySelector(`[data-id="${node.id}"]`)?.classList.add("selected");
    this.showNodeDetails(node);
  }

  private showNodeDetails(node: NetworkNode): void {
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
        <div class="detail-title">${this.escapeHtml(node.title)}</div>
        <div class="detail-authors">${node.authors.join(", ")}</div>
        <div class="detail-year">Published: ${node.year}</div>
        ${node.similarity_score ? `<div class="detail-score">Similarity Score: <strong>${node.similarity_score.toFixed(2)}</strong></div>` : ""}
        <div class="detail-doi"><a href="https://doi.org/${node.id}" target="_blank" rel="noopener"><i class="fas fa-external-link-alt"></i> View on DOI.org</a></div>
        <button class="btn-save-to-library" data-doi="${node.id}">
          <i class="fas fa-bookmark"></i> Save to Library
        </button>
      </div>
    `;

    panel
      .querySelector(".btn-save-to-library")
      ?.addEventListener("click", () => {
        saveNodeToLibrary(node);
      });
  }

  private async fetchRelatedPapers(doi: string, limit: number): Promise<void> {
    const container = document.getElementById("relatedPapersList");
    const content = document.getElementById("relatedPapersContent");
    if (!container || !content) return;

    try {
      const url = `${this.config.urls.relatedPapers}?doi=${encodeURIComponent(doi)}&limit=${limit}`;
      const response = await this.fetchWithTimeout(url, 60000);

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
                <div class="paper-title">${this.escapeHtml(paper.title)}</div>
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
          if (paperDoi && this.currentData) {
            const node = this.currentData.nodes.find((n) => n.id === paperDoi);
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

  private showLoading(show: boolean): void {
    const loading = document.getElementById("graphLoading");
    const visualization = document.getElementById("graphVisualization");
    const related = document.getElementById("relatedPapersList");

    if (show) {
      loading?.classList.remove("hidden");
      visualization?.classList.add("hidden");
      related?.classList.add("hidden");
    } else {
      loading?.classList.add("hidden");
    }
  }

  private showError(message: string): void {
    const errorEl = document.getElementById("graphError");
    const messageEl = document.getElementById("graphErrorMessage");
    if (errorEl && messageEl) {
      messageEl.textContent = message;
      errorEl.classList.remove("hidden");
    }
  }

  private hideError(): void {
    document.getElementById("graphError")?.classList.add("hidden");
  }

  private resetView(): void {
    this.transform = { x: 0, y: 0, k: 1 };
    this.renderer.applyTransform(this.transform);
  }

  private fitToView(): void {
    if (!this.currentData) return;

    const svg = this.renderer.getSvg();
    if (!svg) return;

    const nodes = this.currentData.nodes;
    if (nodes.length === 0) return;

    const minX = Math.min(...nodes.map((n) => n.x || 0));
    const maxX = Math.max(...nodes.map((n) => n.x || 0));
    const minY = Math.min(...nodes.map((n) => n.y || 0));
    const maxY = Math.max(...nodes.map((n) => n.y || 0));

    const padding = 50;
    const graphWidth = maxX - minX + padding * 2;
    const graphHeight = maxY - minY + padding * 2;

    const svgRect = svg.getBoundingClientRect();
    const scale = Math.min(
      svgRect.width / graphWidth,
      svgRect.height / graphHeight,
      2,
    );

    this.transform = {
      x: svgRect.width / 2 - ((minX + maxX) / 2) * scale,
      y: svgRect.height / 2 - ((minY + maxY) / 2) * scale,
      k: scale,
    };

    this.renderer.applyTransform(this.transform);
  }

  private downloadSvg(): void {
    const svg = document.getElementById("citationGraphSvg");
    if (!svg) return;

    const svgData = new XMLSerializer().serializeToString(svg);
    const blob = new Blob([svgData], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = "citation-graph.svg";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  private escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  new CitationGraphManager();
});
