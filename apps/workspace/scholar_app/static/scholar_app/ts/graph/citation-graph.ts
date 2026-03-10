/**
 * Citation Graph Visualization
 * Interactive force-directed network visualization for citation relationships
 *
 * Refactored: Extracted ForceSimulation, GraphRenderer, GraphInteraction,
 * GraphInputHandler, NodeDetailsPanel, and types for maintainability.
 */

import type {
  CitationGraphConfig,
  NetworkNode,
  NetworkData,
  Transform,
  SourceInfo,
} from "./types";
import { GraphRenderer } from "./_GraphRenderer";
import { GraphInputHandler } from "./_GraphInputHandler";
import { GraphLibraryManager } from "./_GraphLibraryManager";
import { NodeDetailsPanel, escapeHtml } from "./_NodeDetailsPanel";
import {
  setupZoomPan,
  startNodeDrag,
  type InteractionState,
} from "./_GraphInteraction";
import { autoSavePapers } from "../common/_auto-save-library";
import {
  startInspiringSpinner,
  type SpinnerHandle,
} from "@/components/inspiring-spinner";

class CitationGraphManager {
  private config: CitationGraphConfig;
  private currentData: NetworkData | null = null;
  private renderer: GraphRenderer;
  private detailsPanel: NodeDetailsPanel;
  private interactionState: InteractionState = {
    transform: { x: 0, y: 0, k: 1 },
    isDragging: false,
  };
  private activeEdgeFilters: Set<string> = new Set([
    "coupling",
    "cocitation",
    "direct",
  ]);
  private loadingSpinner: SpinnerHandle | null = null;
  private sourceInfo: SourceInfo | null = null;
  private graphLibrary: GraphLibraryManager | null = null;

  constructor() {
    const config = window.CITATION_GRAPH_CONFIG;
    if (!config) {
      console.error("Citation graph config not found");
      return;
    }
    this.config = config;

    this.detailsPanel = new NodeDetailsPanel((node) =>
      this.buildFromDois([node.id]),
    );
    this.renderer = new GraphRenderer({
      onNodeHover: (node, el) => this.detailsPanel.showTooltip(node, el),
      onNodeLeave: () => this.detailsPanel.hideTooltip(),
      onNodeClick: (node) => this.detailsPanel.selectNode(node),
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
    if (this.config.urls.listSavedGraphs) {
      this.graphLibrary = new GraphLibraryManager(this.config, {
        onLoadGraph: (data, pos) => this.loadFromSaved(data, pos),
        onRefreshGraph: (info) => this.refreshFromRecipe(info),
        getCurrentData: () => this.currentData,
        getNodePositions: () => this.getNodePositions(),
        getSourceInfo: () => this.sourceInfo,
      });
    }
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
      this.sourceInfo = {
        source_type: "dois",
        seed_dois: dois,
        query_text: "",
        build_params: { num_related: numRelated },
      };
      this.loadingSpinner?.updateMessage("Rendering graph...");
      this.renderGraph(networkData);
      this.graphLibrary?.showSaveButton();
      await this.fetchRelatedPapers(dois[0], numRelated);
    } catch (err) {
      console.error("Error building citation network:", err);
      this.showError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      this.showLoading(false);
    }
  }

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
      this.sourceInfo = {
        source_type: "query",
        seed_dois: networkData.seed_dois || [],
        query_text: query,
        build_params: { num_related: numRelated },
      };
      this.loadingSpinner?.updateMessage("Rendering graph...");
      this.renderGraph(networkData);
      this.graphLibrary?.showSaveButton();
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

  /** Render a previously saved graph without API call */
  public loadFromSaved(
    data: NetworkData,
    positions: Record<string, { x: number; y: number }>,
  ): void {
    // Restore node positions from saved layout
    for (const node of data.nodes) {
      const pos = positions[node.id];
      if (pos) {
        node.x = pos.x;
        node.y = pos.y;
        node.fx = pos.x;
        node.fy = pos.y;
      }
    }
    this.currentData = data;
    this.renderGraph(data);
    this.graphLibrary?.showSaveButton();
  }

  /** Re-build graph from saved recipe */
  public refreshFromRecipe(info: SourceInfo): void {
    if (info.source_type === "query" && info.query_text) {
      this.buildFromQuery(info.query_text);
    } else if (info.seed_dois.length > 0) {
      this.buildFromDois(info.seed_dois);
    }
  }

  /** Extract current node positions for saving layout */
  public getNodePositions(): Record<string, { x: number; y: number }> {
    const positions: Record<string, { x: number; y: number }> = {};
    if (this.currentData) {
      for (const node of this.currentData.nodes) {
        if (node.x != null && node.y != null) {
          positions[node.id] = { x: node.x, y: node.y };
        }
      }
    }
    return positions;
  }

  private renderGraph(data: NetworkData): void {
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

  private async fetchRelatedPapers(doi: string, limit: number): Promise<void> {
    await this.detailsPanel.fetchRelatedPapers(
      doi,
      limit,
      this.config.urls.relatedPapers,
      (url, ms) => this.fetchWithTimeout(url, ms),
      this.currentData,
    );
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

// Re-initialize when Scholar partial is re-injected via AJAX (ES modules are cached)
document.addEventListener("workspace:module-injected", (e) => {
  if ((e as CustomEvent).detail?.module === "scholar") {
    initAll();
  }
});
