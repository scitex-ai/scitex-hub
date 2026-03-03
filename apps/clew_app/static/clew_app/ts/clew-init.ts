/**
 * Clew App Initialization
 * Sets up the DAG visualization interface and file tree
 */

import mermaid from "mermaid";
import { clewApi } from "./api-client";

// Initialize mermaid once at module load
mermaid.initialize({
  startOnLoad: false,
  theme: document.documentElement.classList.contains("dark-mode")
    ? "dark"
    : "default",
  securityLevel: "loose",
  flowchart: { curve: "basis" },
});

class ClewApp {
  private dagArea: HTMLElement | null = null;
  private detailsPanel: HTMLElement | null = null;
  private projectOwner: string | null = null;
  private projectSlug: string | null = null;
  private projectId: string | null = null;

  constructor() {
    this.dagArea = document.querySelector(".dag-visualization-area");
    this.detailsPanel = document.querySelector(".clew-details-content");
    this.extractProjectInfo();
  }

  private extractProjectInfo() {
    const configEl = document.getElementById("workspace-project-config");
    if (configEl) {
      this.projectOwner = configEl.dataset.username || null;
      this.projectSlug = configEl.dataset.slug || null;
      this.projectId = configEl.dataset.projectId || null;
    }
  }

  async initialize() {
    if (!this.projectOwner || !this.projectSlug) {
      console.log("[Clew] No project selected");
      return;
    }

    await this.loadStats();
    this.setupEventListeners();
    this.setupDropTarget();
    this.setupHeaderButtons();

    const urlParams = new URLSearchParams(window.location.search);
    const targetFile = urlParams.get("file");
    if (targetFile) {
      await this.loadChainForFile(targetFile);
    } else {
      await this.autoRenderDag();
    }
  }

  private async loadStats() {
    const response = await clewApi.getStats();
    if (response.success && response.data) {
      this.updateStatsDisplay(response.data);
    }
  }

  private updateStatsDisplay(stats: any) {
    if (stats.total_runs === 0) return;

    const placeholder = this.dagArea?.querySelector(".dag-placeholder");
    if (placeholder) {
      placeholder.innerHTML = `
        <i class="fas fa-project-diagram fa-3x"></i>
        <h3>DAG Visualization</h3>
        <p>${stats.total_runs} runs tracked (${stats.success_runs} success, ${stats.failed_runs} failed)</p>
        <p class="text-muted">Tracking ${stats.unique_files} unique files</p>
        <button class="btn btn-sm btn-outline-primary mt-2" id="showAllDag">Show DAG</button>
      `;
      const btn = placeholder.querySelector("#showAllDag");
      btn?.addEventListener("click", () => this.renderFullDag());
    }
  }

  private setupHeaderButtons() {
    const header = document.querySelector(".clew-header");
    if (!header) return;

    const btn = document.createElement("button");
    btn.className = "btn btn-sm btn-outline-secondary ms-2";
    btn.innerHTML = '<i class="fas fa-play-circle"></i> Add Examples';
    btn.title = "Load example Clew pipeline scripts into this project";
    btn.addEventListener("click", () => this.addExamples(btn));
    header.appendChild(btn);
  }

  private async addExamples(btn: HTMLButtonElement) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';

    const response = await clewApi.addExamples();
    if (response.success) {
      btn.innerHTML = '<i class="fas fa-check"></i> Examples added';
      await this.loadStats();
    } else {
      btn.innerHTML = '<i class="fas fa-play-circle"></i> Add Examples';
      btn.disabled = false;
      console.error("[Clew] Failed to add examples:", response.error);
      alert(`Failed to add examples: ${response.error}`);
    }
  }

  private setupEventListeners() {
    document.addEventListener("fileSelected", async (event: Event) => {
      const customEvent = event as CustomEvent;
      const filePath = customEvent.detail?.path;
      if (filePath) {
        await this.handleFileSelected(filePath);
      }
    });
  }

  // ── Drop target ──────────────────────────────────────────────────────────
  private setupDropTarget() {
    if (!this.dagArea) return;

    this.dagArea.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.dagArea!.classList.add("drop-target");
      if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
    });

    this.dagArea.addEventListener("dragleave", (e) => {
      e.preventDefault();
      this.dagArea!.classList.remove("drop-target");
    });

    this.dagArea.addEventListener("drop", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      this.dagArea!.classList.remove("drop-target");
      const paths = this.extractDropPaths(e as DragEvent);
      if (paths.length > 0) {
        await this.handleFileSelected(paths[0]);
      }
    });
  }

  private extractDropPaths(e: DragEvent): string[] {
    // Try scitex-specific format first
    const jsonData = e.dataTransfer?.getData("application/x-scitex-file");
    if (jsonData) {
      try {
        const parsed = JSON.parse(jsonData);
        if (Array.isArray(parsed)) return parsed.map((p: any) => p.path || p);
        if (parsed.path) return [parsed.path];
      } catch {
        /* fall through */
      }
    }
    // Fallback: semicolon-separated paths in text/plain
    const textData = e.dataTransfer?.getData("text/plain");
    if (textData) return textData.split(";").filter(Boolean);
    return [];
  }

  // ── File selection with companion file lookup ────────────────────────────
  private async handleFileSelected(filePath: string) {
    // If the file itself is .mmd, render it directly
    if (filePath.endsWith(".mmd")) {
      await this.renderMmdFile(filePath);
      return;
    }

    // Look for companion clew files: {path}-clew.mmd or {path}-clew.png
    const mmdCompanion = `${filePath}-clew.mmd`;
    const pngCompanion = `${filePath}-clew.png`;

    // Try .mmd companion first
    const mmdContent = await this.fetchFileContent(mmdCompanion);
    if (mmdContent) {
      await this.renderMermaidContent(mmdContent);
      return;
    }

    // Try .png companion
    const pngExists = await this.checkFileExists(pngCompanion);
    if (pngExists) {
      this.renderImageFile(pngCompanion);
      return;
    }

    // Try clew API chain verification (only if DB has runs)
    const stats = await clewApi.getStats();
    if (stats.success && stats.data && stats.data.total_runs > 0) {
      await this.loadChainForFile(filePath);
      return;
    }

    // No companion files and no clew runs — keep existing DAG, don't replace it
    console.log("[Clew] No companion files or runs for:", filePath);
  }

  // ── Auto-render dag.mmd on load ──────────────────────────────────────────
  private async autoRenderDag() {
    // First try API (real clew DB runs)
    const response = await clewApi.getStats();
    if (response.success && response.data && response.data.total_runs > 0) {
      await this.renderFullDag();
      return;
    }

    // Fallback: try to load dag.mmd from project root
    const dagContent = await this.fetchFileContent("dag.mmd");
    if (dagContent) {
      await this.renderMermaidContent(dagContent);
      return;
    }

    // Nothing to render — placeholder stays
  }

  // ── Rendering helpers ────────────────────────────────────────────────────
  private async renderMmdFile(filePath: string) {
    const content = await this.fetchFileContent(filePath);
    if (content) {
      await this.renderMermaidContent(content);
    } else {
      this.showError(`Could not load ${filePath}`);
    }
  }

  private async renderMermaidContent(code: string) {
    if (!this.dagArea) return;

    const trimmed = code.trim();
    if (!trimmed || trimmed === "graph TD") {
      this.showError("Empty diagram");
      return;
    }

    const containerId = "mermaid-dag-" + Date.now();
    const wrapper = document.createElement("div");
    wrapper.className = "dag-mermaid-wrapper";
    wrapper.innerHTML = `<div class="mermaid" id="${containerId}">${trimmed}</div>`;
    this.dagArea.innerHTML = "";
    this.dagArea.appendChild(wrapper);

    try {
      await mermaid.run({ nodes: [wrapper.querySelector(".mermaid")!] });
      this.setupDagNodeClickHandlers(wrapper);
    } catch (err) {
      console.error("[Clew] Mermaid render error:", err);
      wrapper.innerHTML = `<pre class="dag-mermaid-code">${trimmed}</pre>`;
    }
  }

  private renderImageFile(filePath: string) {
    if (!this.dagArea) return;
    const url = `/api/workspace/file-content/${encodeURIComponent(filePath)}?project_id=${this.projectId}`;
    this.dagArea.innerHTML = `
      <div class="dag-mermaid-wrapper">
        <img src="${url}" alt="Clew DAG" style="max-width:100%;height:auto;" />
      </div>
    `;
  }

  private async fetchFileContent(filePath: string): Promise<string | null> {
    try {
      const url = `/api/workspace/file-content/${encodeURIComponent(filePath)}?project_id=${this.projectId}`;
      const resp = await fetch(url);
      if (!resp.ok) return null;
      const data = await resp.json();
      if (data.success && data.content) return data.content;
      return null;
    } catch {
      return null;
    }
  }

  private async checkFileExists(filePath: string): Promise<boolean> {
    return (await this.fetchFileContent(filePath)) !== null;
  }

  private async renderFullDag() {
    this.showLoading();
    await this.renderMermaidDag(undefined);
  }

  private async renderMermaidDag(targetFile?: string) {
    if (!this.dagArea) return;

    const response = await clewApi.getMermaidDag(
      targetFile ? { targetFile, pathMode: "name" } : { pathMode: "name" },
    );

    if (!response.success || !response.data?.mermaid) {
      this.showError(response.error || "Failed to load DAG");
      return;
    }

    await this.renderMermaidContent(response.data.mermaid);
  }

  private async loadChainForFile(filePath: string) {
    this.showLoading();

    const response = await clewApi.verifyChain(filePath);
    if (response.success && response.data) {
      await this.renderMermaidDag(filePath);
      this.showChainDetails(response.data);
    } else {
      this.showError(response.error || "Failed to load verification chain");
    }
  }

  private setupDagNodeClickHandlers(wrapper: HTMLElement) {
    const nodes = wrapper.querySelectorAll(".node");
    nodes.forEach((node) => {
      (node as HTMLElement).style.cursor = "pointer";
      node.addEventListener("click", () => {
        const label = node.querySelector(".nodeLabel")?.textContent?.trim();
        if (label) {
          document.dispatchEvent(
            new CustomEvent("fileSelected", { detail: { path: label } }),
          );
        }
      });
    });
  }

  private showChainDetails(chainData: any) {
    if (!this.detailsPanel) return;

    let html = `
      <div class="chain-details">
        <h4>Verification Chain</h4>
        <p><strong>Target:</strong> ${chainData.target_file}</p>
        <p><strong>Status:</strong> ${this.getStatusBadge(chainData.status)}</p>
        <p><strong>Runs:</strong> ${chainData.runs.length}</p>
      </div>
    `;

    html += '<div class="runs-list">';
    chainData.runs.forEach((run: any, index: number) => {
      html += `
        <div class="run-item">
          <h5>Run ${index + 1}: ${run.session_id.substring(0, 12)}...</h5>
          <p><strong>Script:</strong> ${run.script_path || "Unknown"}</p>
          <p><strong>Status:</strong> ${this.getStatusBadge(run.status)}</p>
          <p><strong>Files:</strong> ${run.files.length}</p>
        </div>
      `;
    });
    html += "</div>";
    this.detailsPanel.innerHTML = html;
  }

  private getStatusBadge(status: string): string {
    const badges: Record<string, string> = {
      verified: '<span class="badge badge-success">Verified</span>',
      mismatch: '<span class="badge badge-danger">Mismatch</span>',
      missing: '<span class="badge badge-warning">Missing</span>',
      unknown: '<span class="badge badge-secondary">Unknown</span>',
    };
    return badges[status] || badges.unknown;
  }

  private showLoading() {
    if (this.dagArea) {
      this.dagArea.innerHTML = `
        <div class="dag-placeholder">
          <i class="fas fa-spinner fa-spin fa-3x"></i>
          <h3>Loading...</h3>
          <p>Fetching verification chain</p>
        </div>
      `;
    }
  }

  private showError(message: string) {
    if (this.dagArea) {
      this.dagArea.innerHTML = `
        <div class="dag-placeholder">
          <i class="fas fa-exclamation-triangle fa-3x"></i>
          <h3>Error</h3>
          <p>${message}</p>
        </div>
      `;
    }
  }
}

// Initialize when DOM is ready (supports both direct load and AJAX injection)
function initClew() {
  const app = new ClewApp();
  app.initialize();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initClew);
} else {
  initClew();
}
