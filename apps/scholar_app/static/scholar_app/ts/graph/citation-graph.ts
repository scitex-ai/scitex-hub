/**
 * Citation Graph Visualization
 * Interactive force-directed network visualization for citation relationships
 *
 * Refactored: Extracted ForceSimulation, GraphRenderer, GraphInteraction,
 * GraphInputHandler, and types for maintainability.
 */

import type {
  CitationGraphConfig,
  NetworkNode,
  NetworkData,
  RelatedPaper,
  Transform,
} from "./types";
import { GraphRenderer } from "./GraphRenderer";
import { GraphInputHandler } from "./GraphInputHandler";
import {
  setupZoomPan,
  startNodeDrag,
  type InteractionState,
} from "./GraphInteraction";
import { saveNodeToLibrary } from "./library-bridge";
import { autoSavePapers } from "../common/auto-save-library";
import {
  startInspiringSpinner,
  type SpinnerHandle,
} from "../../../../../../static/shared/ts/components/inspiring-spinner";

class CitationGraphManager {
  private config: CitationGraphConfig;
  private currentData: NetworkData | null = null;
  private renderer: GraphRenderer;
  private interactionState: InteractionState = {
    transform: { x: 0, y: 0, k: 1 },
    isDragging: false,
  };
  private selectedNode: NetworkNode | null = null;
  private tooltipHideTimer: ReturnType<typeof setTimeout> | null = null;
  private activeEdgeFilters: Set<string> = new Set([
    "coupling",
    "cocitation",
    "direct",
  ]);
  private loadingSpinner: SpinnerHandle | null = null;

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
      onNodeDragStart: (e, node) =>
        startNodeDrag(e, node, this.renderer, this.interactionState),
      getDepthColor: () => "#3B82F6",
    });

    this.init();
  }

  private get transform(): Transform {
    return this.interactionState.transform;
  }
  private set transform(t: Transform) {
    this.interactionState.transform = t;
  }

  private init(): void {
    this.bindEvents();
    this.checkServiceHealth();
  }

  private bindEvents(): void {
    document
      .getElementById("resetZoomBtn")
      ?.addEventListener("click", () => this.resetView());
    document
      .getElementById("downloadSvgBtn")
      ?.addEventListener("click", () => this.downloadSvg());
    document
      .getElementById("fitViewBtn")
      ?.addEventListener("click", () => this.fitToView());

    // Edge type filter toggles
    document.querySelectorAll(".edge-filter-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const type = btn.getAttribute("data-edge-type");
        if (!type) return;
        if (this.activeEdgeFilters.has(type)) {
          this.activeEdgeFilters.delete(type);
          btn.classList.remove("active");
        } else {
          this.activeEdgeFilters.add(type);
          btn.classList.add("active");
        }
        this.renderer.filterEdges(this.activeEdgeFilters);
      });
    });
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

  /**
   * Build graph from multiple DOIs (unified entry point for all flows)
   */
  public async buildFromDois(dois: string[]): Promise<void> {
    if (dois.length === 0) {
      this.showError("No DOIs provided");
      return;
    }
    const topNSelect = document.getElementById("topN") as HTMLSelectElement;
    const numRelated = parseInt(topNSelect?.value || "20", 10);
    this.showLoading(true);
    this.hideError();
    try {
      const doisParam = dois.map((d) => encodeURIComponent(d)).join(",");
      const networkUrl = `${this.config.urls.buildNetworkMulti}?dois=${doisParam}&num_related_per_doi=${numRelated}`;
      const networkResponse = await this.fetchWithTimeout(networkUrl, 120000);
      if (!networkResponse.ok) {
        const errorData = await networkResponse.json();
        throw new Error(errorData.error || "Failed to build network");
      }
      const networkData: NetworkData = await networkResponse.json();
      this.currentData = networkData;
      this.loadingSpinner?.updateMessage("Rendering graph...");
      this.renderGraph(networkData);
      // Fetch related papers for the first seed DOI
      await this.fetchRelatedPapers(dois[0], numRelated);
    } catch (err) {
      console.error("Error building citation network:", err);
      this.showError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      this.showLoading(false);
    }
  }

  /**
   * Build graph from a text query (delegates search + DOI detection to backend)
   */
  public async buildFromQuery(query: string): Promise<void> {
    if (!query.trim()) {
      this.showError("Please enter a search query");
      return;
    }
    const topNSelect = document.getElementById("topN") as HTMLSelectElement;
    const numRelated = parseInt(topNSelect?.value || "20", 10);
    this.showLoading(true);
    this.hideError();
    try {
      const networkUrl = `${this.config.urls.buildNetworkQuery}?q=${encodeURIComponent(query)}&num_related_per_doi=${numRelated}`;
      const networkResponse = await this.fetchWithTimeout(networkUrl, 120000);
      if (!networkResponse.ok) {
        const errorData = await networkResponse.json();
        throw new Error(errorData.error || "Failed to build network");
      }
      const networkData: NetworkData = await networkResponse.json();
      if (networkData.nodes.length === 0) {
        this.showError("No papers with DOI found for this query");
        return;
      }
      this.currentData = networkData;
      this.loadingSpinner?.updateMessage("Rendering graph...");
      this.renderGraph(networkData);
      if (networkData.seed_dois?.length > 0) {
        await this.fetchRelatedPapers(networkData.seed_dois[0], numRelated);
      }
    } catch (err) {
      console.error("Error building citation network from query:", err);
      this.showError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      this.showLoading(false);
    }
  }

  private renderGraph(data: NetworkData): void {
    // Auto-save all graph nodes to project bibliography
    autoSavePapers(
      data.nodes.map((n) => ({
        title: n.title,
        authors: n.authors?.join(", "),
        year: String(n.year || ""),
        doi: n.id,
      })),
      "citation_graph",
    );

    const container = document.getElementById("graphVisualization");
    const canvas = document.getElementById("graphCanvas");
    if (!container || !canvas) return;
    container.classList.remove("hidden");
    const titleEl = document.getElementById("graphTitle");
    if (titleEl) {
      const seedNodes = data.nodes.filter((n) => n.is_seed);
      if (seedNodes.length === 1) {
        titleEl.textContent = `Network: ${seedNodes[0].title.substring(0, 50)}...`;
      } else if (seedNodes.length > 1) {
        titleEl.textContent = `Network: ${seedNodes.length} seed papers, ${data.nodes.length} total`;
      } else {
        titleEl.textContent = "Citation Network";
      }
    }
    this.renderer.render(canvas, data.nodes, data.edges);
    setupZoomPan(this.renderer, this.interactionState);
  }

  private showNodeTooltip(node: NetworkNode, element: SVGGElement): void {
    // Cancel any pending hide
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

  private hideNodeTooltip(): void {
    if (this.tooltipHideTimer) clearTimeout(this.tooltipHideTimer);
    this.tooltipHideTimer = setTimeout(() => {
      const tooltip = document.getElementById("graphTooltip");
      if (tooltip) tooltip.style.display = "none";
    }, 50);
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
      this.exploreFromNode(node);
    });
  }

  private exploreFromNode(node: NetworkNode): void {
    this.buildFromDois([node.id]);
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
      if (loading) {
        this.loadingSpinner = startInspiringSpinner(
          loading,
          "Building citation network...",
        );
      }
    } else {
      this.loadingSpinner?.stop();
      this.loadingSpinner = null;
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
}

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Initialize (handle both direct load and SPA injection)
function initAll(): void {
  const graphManager = new CitationGraphManager();

  new GraphInputHandler({
    onBuildGraph: (dois) => {
      graphManager.buildFromDois(dois);
    },
    onBuildFromQuery: (query) => {
      graphManager.buildFromQuery(query);
    },
    escapeHtml,
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initAll);
} else {
  initAll();
}
