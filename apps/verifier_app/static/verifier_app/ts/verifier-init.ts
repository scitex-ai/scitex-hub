/**
 * Verifier App Initialization
 * Sets up the DAG visualization interface and file tree
 */

import { verifierApi, type DagData } from "./api-client";

class VerifierApp {
  private dagArea: HTMLElement | null = null;
  private detailsPanel: HTMLElement | null = null;
  private projectOwner: string | null = null;
  private projectSlug: string | null = null;

  constructor() {
    this.dagArea = document.querySelector(".dag-visualization-area");
    this.detailsPanel = document.querySelector(".verifier-details-content");
    this.extractProjectInfo();
  }

  private extractProjectInfo() {
    const configEl = document.getElementById("verifier-project-config");
    if (configEl) {
      this.projectOwner = configEl.dataset.username || null;
      this.projectSlug = configEl.dataset.slug || null;
    }
  }

  async initialize() {
    // Initialize file tree
    await this.initFileTree();

    if (!this.projectOwner || !this.projectSlug) {
      console.log("[Verifier] No project selected");
      return;
    }

    // Load initial statistics
    await this.loadStats();

    // Setup event listeners
    this.setupEventListeners();

    // Check for file parameter in URL
    const urlParams = new URLSearchParams(window.location.search);
    const targetFile = urlParams.get("file");
    if (targetFile) {
      await this.loadChainForFile(targetFile);
    }
  }

  private async initFileTree() {
    const treeContainer = document.getElementById("file-tree");
    if (!treeContainer || !this.projectOwner || !this.projectSlug) return;

    try {
      const { WorkspaceFilesTree } =
        await import("@/components/workspace-files-tree/WorkspaceFilesTree");
      const { initHiddenFilesToggle } =
        await import("@/components/workspace-files-tree/HiddenFilesToggle");
      const { initModuleFilterButtons } =
        await import("@/components/workspace-files-tree/ModuleFilterButtons");

      const apiUrl = `/${this.projectOwner}/${this.projectSlug}/api/file-tree/`;

      const tree = new WorkspaceFilesTree({
        container: treeContainer,
        apiUrl,
        mode: "verifier",
        username: this.projectOwner,
        projectSlug: this.projectSlug,
      });

      tree.init();
      initHiddenFilesToggle(tree);
      initModuleFilterButtons(tree, "verifier");
    } catch (err) {
      console.error("[Verifier] Failed to init file tree:", err);
    }
  }

  private async loadStats() {
    const response = await verifierApi.getStats();
    if (response.success && response.data) {
      this.updateStatsDisplay(response.data);
    } else {
      console.error("[Verifier] Failed to load stats:", response.error);
    }
  }

  private updateStatsDisplay(stats: any) {
    const placeholder = this.dagArea?.querySelector(".dag-placeholder");
    if (placeholder) {
      const statsHtml = `
        <i class="fas fa-project-diagram fa-3x"></i>
        <h3>DAG Visualization</h3>
        <p>Database contains ${stats.total_runs} runs</p>
        <p class="text-muted">
          ${stats.success_runs} successful, ${stats.failed_runs} failed
        </p>
        <p class="text-muted">
          Tracking ${stats.unique_files} unique files
        </p>
        <p class="text-muted">
          Uses <code>scitex.verify</code> package for dependency tracking
        </p>
      `;
      placeholder.innerHTML = statsHtml;
    }
  }

  private setupEventListeners() {
    document.addEventListener("fileSelected", async (event: Event) => {
      const customEvent = event as CustomEvent;
      const filePath = customEvent.detail?.path;
      if (filePath) {
        await this.loadChainForFile(filePath);
      }
    });
  }

  private async loadChainForFile(filePath: string) {
    this.showLoading();

    const response = await verifierApi.verifyChain(filePath);
    if (response.success && response.data) {
      await this.renderDag(filePath);
      this.showChainDetails(response.data);
    } else {
      this.showError(response.error || "Failed to load verification chain");
    }
  }

  private async renderDag(targetFile: string) {
    const response = await verifierApi.getDagJson({
      targetFile,
      pathMode: "name",
    });

    if (response.success && response.data) {
      this.renderDagVisualization(response.data);
    } else {
      this.showError(response.error || "Failed to load DAG data");
    }
  }

  private renderDagVisualization(dagData: DagData) {
    if (!this.dagArea) return;

    if (dagData.metadata.empty || dagData.nodes.length === 0) {
      this.dagArea.innerHTML = `
        <div class="dag-placeholder">
          <i class="fas fa-info-circle fa-3x"></i>
          <h3>No Verification Data</h3>
          <p>This file has not been tracked by scitex.verify</p>
          <p class="text-muted">
            Run your analysis scripts with <code>@stx.session</code> decorator
            to enable verification tracking
          </p>
        </div>
      `;
      return;
    }

    const dagHtml = this.generateSimpleDagHtml(dagData);
    this.dagArea.innerHTML = dagHtml;
  }

  private generateSimpleDagHtml(dagData: DagData): string {
    const { nodes, links } = dagData;

    let html = '<div class="dag-simple-view">';
    html += `<h4>Verification Chain (${nodes.length} nodes, ${links.length} edges)</h4>`;

    const scripts = nodes.filter((n) => n.type === "script");
    const files = nodes.filter((n) => n.type === "file");

    html += "<div class='dag-section'>";
    html += `<h5>Scripts (${scripts.length})</h5><ul>`;
    scripts.forEach((node) => {
      const statusIcon =
        node.status === "verified"
          ? '<i class="fas fa-check-circle text-success"></i>'
          : '<i class="fas fa-times-circle text-danger"></i>';
      html += `<li>${statusIcon} ${node.name}</li>`;
    });
    html += "</ul></div>";

    html += "<div class='dag-section'>";
    html += `<h5>Files (${files.length})</h5><ul>`;
    files.forEach((node) => {
      const statusIcon =
        node.status === "verified"
          ? '<i class="fas fa-check-circle text-success"></i>'
          : '<i class="fas fa-times-circle text-danger"></i>';
      html += `<li>${statusIcon} ${node.name} (${node.role})</li>`;
    });
    html += "</ul></div>";

    html += "</div>";
    return html;
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

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  const app = new VerifierApp();
  app.initialize();
});
