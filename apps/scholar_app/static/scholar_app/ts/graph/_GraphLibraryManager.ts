/**
 * Graph Library Manager
 * Handles saving, loading, renaming, deleting, and refreshing persisted citation graphs.
 * Renders a tab bar for switching between saved graphs.
 */

import type {
  CitationGraphConfig,
  NetworkData,
  SavedGraphSummary,
  SourceInfo,
} from "./types";

interface GraphLibraryCallbacks {
  onLoadGraph: (
    data: NetworkData,
    positions: Record<string, { x: number; y: number }>,
  ) => void;
  onRefreshGraph: (sourceInfo: SourceInfo) => void;
  getCurrentData: () => NetworkData | null;
  getNodePositions: () => Record<string, { x: number; y: number }>;
  getSourceInfo: () => SourceInfo | null;
}

export class GraphLibraryManager {
  private config: CitationGraphConfig;
  private callbacks: GraphLibraryCallbacks;
  private savedGraphs: SavedGraphSummary[] = [];
  private activeGraphId: string | null = null;
  private contextMenu: HTMLElement | null = null;

  constructor(config: CitationGraphConfig, callbacks: GraphLibraryCallbacks) {
    this.config = config;
    this.callbacks = callbacks;
    this.init();
  }

  private async init(): Promise<void> {
    this.bindEvents();
    await this.fetchSavedGraphs();
  }

  private bindEvents(): void {
    document
      .getElementById("graphSaveBtn")
      ?.addEventListener("click", () => this.showSaveDialog());
    document
      .getElementById("graphSaveBtn2")
      ?.addEventListener("click", () => this.showSaveDialog());
    document.addEventListener("click", () => this.hideContextMenu());
  }

  async fetchSavedGraphs(): Promise<void> {
    if (!this.config.urls.listSavedGraphs) return;
    try {
      const resp = await fetch(this.config.urls.listSavedGraphs);
      if (!resp.ok) return;
      const data = await resp.json();
      this.savedGraphs = data.graphs || [];
      this.renderTabBar();
    } catch (err) {
      console.error("[GraphLibrary] Failed to fetch saved graphs:", err);
    }
  }

  /** Show save button when a graph is built */
  showSaveButton(): void {
    document.getElementById("graphSaveBtn")?.classList.remove("hidden");
    document.getElementById("graphTabsBar")?.classList.remove("hidden");
  }

  private renderTabBar(): void {
    const bar = document.getElementById("graphTabsBar");
    const list = document.getElementById("graphTabsList");
    if (!bar || !list) return;

    if (this.savedGraphs.length === 0 && !this.callbacks.getCurrentData()) {
      bar.classList.add("hidden");
      return;
    }
    bar.classList.remove("hidden");

    list.innerHTML = this.savedGraphs
      .map(
        (g) => `
      <div class="graph-tab ${g.id === this.activeGraphId ? "active" : ""}"
           data-graph-id="${g.id}" title="${this.escapeAttr(g.name)}">
        <span class="graph-tab-name">${this.escapeHtml(g.name)}</span>
        <span class="graph-tab-count">${g.node_count}</span>
      </div>
    `,
      )
      .join("");

    list.querySelectorAll(".graph-tab").forEach((tab) => {
      tab.addEventListener("click", (e) => {
        const id = (tab as HTMLElement).dataset.graphId;
        if (id) this.loadGraph(id);
      });
      tab.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        const id = (tab as HTMLElement).dataset.graphId;
        if (id) this.showContextMenu(e as MouseEvent, id);
      });
    });
  }

  private showSaveDialog(): void {
    const data = this.callbacks.getCurrentData();
    if (!data) return;

    const existing = document.getElementById("graphSaveDialog");
    if (existing) existing.remove();

    const dialog = document.createElement("div");
    dialog.id = "graphSaveDialog";
    dialog.className = "graph-save-dialog";
    dialog.innerHTML = `
      <input type="text" id="graphSaveName" class="graph-save-input"
             placeholder="Name this graph..." autofocus />
      <button id="graphSaveConfirm" class="graph-save-confirm">
        <i class="fas fa-check"></i>
      </button>
      <button id="graphSaveCancel" class="graph-save-cancel">
        <i class="fas fa-times"></i>
      </button>
    `;

    const bar = document.getElementById("graphTabsBar");
    bar?.appendChild(dialog);

    const input = document.getElementById("graphSaveName") as HTMLInputElement;
    input?.focus();

    const doSave = () => {
      const name = input?.value.trim();
      if (name) this.saveCurrentGraph(name);
      dialog.remove();
    };

    input?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") doSave();
      if (e.key === "Escape") dialog.remove();
    });
    document
      .getElementById("graphSaveConfirm")
      ?.addEventListener("click", doSave);
    document
      .getElementById("graphSaveCancel")
      ?.addEventListener("click", () => dialog.remove());
  }

  private async saveCurrentGraph(name: string): Promise<void> {
    const data = this.callbacks.getCurrentData();
    if (!data) return;
    const sourceInfo = this.callbacks.getSourceInfo();
    const positions = this.callbacks.getNodePositions();

    try {
      const resp = await fetch(this.config.urls.saveGraph, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.getCsrfToken(),
        },
        body: JSON.stringify({
          name,
          source_type: sourceInfo?.source_type || "dois",
          seed_dois: sourceInfo?.seed_dois || data.seed_dois || [],
          query_text: sourceInfo?.query_text || "",
          build_params: sourceInfo?.build_params || {},
          graph_data: data,
          node_positions: positions,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json();
        alert(err.error || "Failed to save graph");
        return;
      }

      const result = await resp.json();
      this.activeGraphId = result.id;
      await this.fetchSavedGraphs();
    } catch (err) {
      console.error("[GraphLibrary] Save failed:", err);
    }
  }

  private async loadGraph(graphId: string): Promise<void> {
    const url = this.config.urls.loadGraph.replace("__ID__", graphId);
    try {
      const resp = await fetch(url);
      if (!resp.ok) return;
      const data = await resp.json();
      this.activeGraphId = graphId;
      this.renderTabBar();
      this.callbacks.onLoadGraph(data.graph_data, data.node_positions || {});
    } catch (err) {
      console.error("[GraphLibrary] Load failed:", err);
    }
  }

  private showContextMenu(e: MouseEvent, graphId: string): void {
    this.hideContextMenu();
    const menu = document.createElement("div");
    menu.className = "graph-tab-context-menu";
    menu.innerHTML = `
      <button class="ctx-item" data-action="rename"><i class="fas fa-pen"></i> Rename</button>
      <button class="ctx-item" data-action="refresh"><i class="fas fa-sync"></i> Refresh</button>
      <button class="ctx-item ctx-item--danger" data-action="delete"><i class="fas fa-trash"></i> Delete</button>
    `;
    menu.style.left = `${e.clientX}px`;
    menu.style.top = `${e.clientY}px`;
    document.body.appendChild(menu);
    this.contextMenu = menu;

    menu.querySelectorAll(".ctx-item").forEach((btn) => {
      btn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const action = (btn as HTMLElement).dataset.action;
        this.hideContextMenu();
        if (action === "rename") this.promptRename(graphId);
        if (action === "refresh") this.refreshGraph(graphId);
        if (action === "delete") this.deleteGraph(graphId);
      });
    });
  }

  private hideContextMenu(): void {
    this.contextMenu?.remove();
    this.contextMenu = null;
  }

  private promptRename(graphId: string): void {
    const graph = this.savedGraphs.find((g) => g.id === graphId);
    const newName = prompt("Rename graph:", graph?.name || "");
    if (newName?.trim()) this.renameGraph(graphId, newName.trim());
  }

  private async renameGraph(graphId: string, newName: string): Promise<void> {
    const url = this.config.urls.renameGraph.replace("__ID__", graphId);
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.getCsrfToken(),
        },
        body: JSON.stringify({ name: newName }),
      });
      if (resp.ok) await this.fetchSavedGraphs();
    } catch (err) {
      console.error("[GraphLibrary] Rename failed:", err);
    }
  }

  private async deleteGraph(graphId: string): Promise<void> {
    if (!confirm("Delete this saved graph?")) return;
    const url = this.config.urls.deleteGraph.replace("__ID__", graphId);
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": this.getCsrfToken() },
      });
      if (resp.ok) {
        if (this.activeGraphId === graphId) this.activeGraphId = null;
        await this.fetchSavedGraphs();
      }
    } catch (err) {
      console.error("[GraphLibrary] Delete failed:", err);
    }
  }

  private async refreshGraph(graphId: string): Promise<void> {
    const url = this.config.urls.refreshGraph.replace("__ID__", graphId);
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": this.getCsrfToken() },
      });
      if (!resp.ok) return;
      const recipe = await resp.json();
      this.activeGraphId = graphId;
      this.callbacks.onRefreshGraph({
        source_type: recipe.source_type,
        seed_dois: recipe.seed_dois,
        query_text: recipe.query_text,
        build_params: recipe.build_params,
      });
    } catch (err) {
      console.error("[GraphLibrary] Refresh failed:", err);
    }
  }

  private getCsrfToken(): string {
    return (
      document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
        ?.value ||
      document.cookie.match(/csrftoken=([^;]+)/)?.[1] ||
      ""
    );
  }

  private escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  private escapeAttr(text: string): string {
    return text.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
}
