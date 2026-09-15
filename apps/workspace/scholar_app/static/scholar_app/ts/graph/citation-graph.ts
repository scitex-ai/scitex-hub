/**
 * Citation Graph - Scholar "Citations" tab.
 * Fetches a network from the citation-graph API and draws it with CanvasGraph;
 * tapping a paper centres it and opens the NodeSheet.
 */

import type {
  CitationGraphConfig,
  NetworkNode,
  NetworkData,
  SourceInfo,
} from "./types";
import { CanvasGraph } from "./_CanvasGraph";
import { GraphInputHandler } from "./_GraphInputHandler";
import { GraphLibraryManager } from "./_GraphLibraryManager";
import { NodeSheet, escapeHtml } from "./_NodeSheet";
import { gt } from "./_graph-i18n";
import {
  startInspiringSpinner,
  type SpinnerHandle,
} from "@/components/inspiring-spinner";

const $ = (id: string) => document.getElementById(id);

class CitationGraphManager {
  private config!: CitationGraphConfig;
  private currentData: NetworkData | null = null;
  private graph: CanvasGraph | null = null;
  private sheet: NodeSheet | null = null;
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
    const sheetEl = $("graphNodeSheet");
    if (sheetEl) {
      this.sheet = new NodeSheet(
        sheetEl,
        (node) => this.buildFromDois([node.id]),
        () => this.graph?.select(null),
      );
    }
    this.bindControls();
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

  private bindControls(): void {
    $("fitViewBtn")?.addEventListener("click", () => this.graph?.fit());
    $("zoomInBtn")?.addEventListener("click", () => this.graph?.zoomBy(1.4));
    $("zoomOutBtn")?.addEventListener("click", () =>
      this.graph?.zoomBy(1 / 1.4),
    );
    $("downloadPngBtn")?.addEventListener("click", () => this.downloadPng());
    const hint = $("graphHint");
    if (hint) hint.textContent = gt("hint");
  }

  private async fetchWithTimeout(
    url: string,
    timeoutMs = 120000,
  ): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(url, { signal: controller.signal });
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        throw new Error(`Request timed out after ${timeoutMs / 1000} seconds`);
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  private async checkServiceHealth(): Promise<void> {
    const statusEl = $("serviceStatus");
    if (!statusEl || !this.config.urls.health) return;
    try {
      const data = await (await fetch(this.config.urls.health)).json();
      statusEl.innerHTML =
        data.status === "healthy"
          ? `<div class="status-indicator status-healthy"><i class="fas fa-check-circle"></i><span>Service available</span></div>`
          : `<div class="status-indicator status-warning"><i class="fas fa-exclamation-triangle"></i><span>Local index unavailable — using online Crossref</span></div>`;
    } catch {
      statusEl.innerHTML = `<div class="status-indicator status-warning"><i class="fas fa-exclamation-triangle"></i><span>Using online Crossref</span></div>`;
    }
  }

  private numRelated(): number {
    return parseInt(($("topN") as HTMLSelectElement | null)?.value || "20", 10);
  }

  public buildFromDois(dois: string[]): Promise<void> {
    const n = this.numRelated();
    const param = dois.map((d) => encodeURIComponent(d)).join(",");
    return this.build(
      `${this.config.urls.buildNetworkMulti}?dois=${param}&num_related_per_doi=${n}`,
      {
        source_type: "dois",
        seed_dois: dois,
        query_text: "",
        build_params: { num_related: n },
      },
    );
  }

  public buildFromQuery(query: string): Promise<void> {
    const n = this.numRelated();
    return this.build(
      `${this.config.urls.buildNetworkQuery}?q=${encodeURIComponent(query)}&num_related_per_doi=${n}`,
      {
        source_type: "query",
        seed_dois: [],
        query_text: query,
        build_params: { num_related: n },
      },
    );
  }

  private async build(url: string, info: SourceInfo): Promise<void> {
    this.showLoading(true);
    try {
      const res = await this.fetchWithTimeout(url);
      const data = await res.json().catch(() => {
        throw new Error(`Citation graph API answered HTTP ${res.status}`);
      });
      if (!res.ok) throw new Error(data.error || "Failed to build network");
      const network = data as NetworkData;
      this.sourceInfo = {
        ...info,
        seed_dois: network.seed_dois?.length
          ? network.seed_dois
          : info.seed_dois,
      };
      this.showLoading(false);
      this.renderGraph(network);
    } catch (err) {
      console.error("Error building citation network:", err);
      this.showLoading(false);
      this.showError(err instanceof Error ? err.message : "An error occurred");
    }
  }

  public loadFromSaved(
    data: NetworkData,
    positions: Record<string, { x: number; y: number }>,
  ): void {
    for (const node of data.nodes) {
      const pos = positions[node.id];
      if (pos) {
        node.x = pos.x;
        node.y = pos.y;
      }
    }
    this.renderGraph(data);
  }

  public refreshFromRecipe(info: SourceInfo): void {
    if (info.source_type === "query" && info.query_text) {
      this.buildFromQuery(info.query_text);
    } else if (info.seed_dois.length > 0) {
      this.buildFromDois(info.seed_dois);
    }
  }

  public getNodePositions(): Record<string, { x: number; y: number }> {
    const positions: Record<string, { x: number; y: number }> = {};
    for (const node of this.currentData?.nodes || []) {
      if (node.x != null && node.y != null)
        positions[node.id] = { x: node.x, y: node.y };
    }
    return positions;
  }

  private renderGraph(data: NetworkData): void {
    const seeds = data.nodes.filter((n) => n.is_seed);
    if (data.nodes.length === 0 || data.edges.length === 0) {
      this.currentData = null;
      this.showEmpty(
        data.nodes.length === 0 ? gt("emptyNoPaper") : gt("emptyNoLinks"),
      );
      return;
    }
    this.currentData = data;
    $("graphVisualization")?.classList.remove("hidden");
    this.sheet?.hide();

    const host = $("graphCanvas");
    if (!host) return;
    if (!this.graph || !host.querySelector(".citation-graph-canvas")) {
      this.graph?.destroy();
      this.graph = new CanvasGraph(host, {
        onNodeTap: (n) => this.onNodeTap(n),
      });
    }
    this.graph.setData(data.nodes, data.edges);
    const summary = gt("graphSummary", {
      nodes: data.nodes.length,
      edges: data.edges.length,
    });
    this.graph.setAriaLabel(summary);

    const titleEl = $("graphTitle");
    if (titleEl) {
      const t = seeds[0]?.title || seeds[0]?.id || "";
      titleEl.textContent = gt("networkOf", {
        title: t.length > 60 ? `${t.slice(0, 58)}…` : t,
      });
      titleEl.title = t;
    }
    const summaryEl = $("graphSummary");
    if (summaryEl) summaryEl.textContent = summary;
    this.renderPaperList(data.nodes);
    this.graphLibrary?.showSaveButton();

    const graph = this.graph;
    // Lets e2e probes find a node on screen without reaching into the module.
    (window as unknown as Record<string, unknown>).__citationGraph = {
      nodeCount: data.nodes.length,
      edgeCount: data.edges.length,
      nodeClientPoint: (i: number) => graph.nodeClientPoint(data.nodes[i]),
    };
  }

  private onNodeTap(node: NetworkNode | null): void {
    if (!node) {
      this.sheet?.hide();
      this.graph?.select(null);
      return;
    }
    this.selectNode(node);
  }

  private selectNode(node: NetworkNode): void {
    this.graph?.select(node);
    this.sheet?.show(node);
    const sheetH = this.sheet?.height() || 0;
    this.graph?.centerOnNode(node, sheetH);
  }

  private renderPaperList(nodes: NetworkNode[]): void {
    const container = $("relatedPapersList");
    const content = $("relatedPapersContent");
    const heading = $("relatedPapersHeading");
    if (!container || !content) return;
    if (heading) heading.textContent = gt("related");
    const sorted = [...nodes].sort(
      (a, b) =>
        Number(b.is_seed) - Number(a.is_seed) ||
        (b.citation_count || 0) - (a.citation_count || 0),
    );
    content.innerHTML = sorted
      .map(
        (p, i) => `
        <button type="button" class="related-paper-item${p.is_seed ? " is-seed" : ""}" data-index="${nodes.indexOf(p)}">
          <span class="paper-rank">${i + 1}</span>
          <span class="paper-info">
            <span class="paper-title">${escapeHtml(p.title || p.id)}</span>
            <span class="paper-meta">${escapeHtml((p.authors || []).slice(0, 2).join(", "))}${(p.authors || []).length > 2 ? " et al." : ""} ${p.year || ""}</span>
          </span>
          <span class="paper-cites">${(p.citation_count || 0).toLocaleString()}</span>
        </button>`,
      )
      .join("");
    content
      .querySelectorAll<HTMLElement>(".related-paper-item")
      .forEach((item) => {
        item.addEventListener("click", () => {
          const node = nodes[Number(item.dataset.index)];
          if (!node) return;
          $("graphVisualization")?.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
          });
          this.selectNode(node);
        });
      });
    container.classList.remove("hidden");
  }

  private showLoading(show: boolean): void {
    const loading = $("graphLoading");
    if (show) {
      for (const id of [
        "graphVisualization",
        "relatedPapersList",
        "graphError",
        "graphEmpty",
      ]) {
        $(id)?.classList.add("hidden");
      }
      if (loading) {
        loading.classList.remove("hidden");
        this.loadingSpinner?.stop();
        this.loadingSpinner = startInspiringSpinner(loading, gt("building"));
      }
    } else {
      this.loadingSpinner?.stop();
      this.loadingSpinner = null;
      loading?.classList.add("hidden");
    }
  }

  private showEmpty(message: string): void {
    const el = $("graphEmpty");
    if (!el) return this.showError(message);
    const title = el.querySelector(".graph-empty__title");
    const body = el.querySelector(".graph-empty__body");
    if (title) title.textContent = gt("emptyTitle");
    if (body) body.textContent = message;
    el.classList.remove("hidden");
  }

  private showError(message: string): void {
    const messageEl = $("graphErrorMessage");
    if (messageEl) messageEl.textContent = message;
    $("graphError")?.classList.remove("hidden");
  }

  private downloadPng(): void {
    if (!this.graph) return;
    const link = document.createElement("a");
    link.href = this.graph.toDataURL();
    link.download = "citation-graph.png";
    document.body.appendChild(link);
    link.click();
    link.remove();
  }
}

function initAll(): void {
  const graphManager = new CitationGraphManager();
  new GraphInputHandler({
    onBuildGraph: (dois) => graphManager.buildFromDois(dois),
    onBuildFromQuery: (query) => graphManager.buildFromQuery(query),
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
  if ((e as CustomEvent).detail?.module === "scholar") initAll();
});
