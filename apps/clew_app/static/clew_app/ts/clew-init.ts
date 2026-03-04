/**
 * Clew App Initialization — thin orchestrator
 * Delegates rendering to clew-modes, clew-drop, clew-rendering
 */

import { clewApi } from "./api-client";
import {
  extractDropPaths,
  handleFileSelected,
  renderMultiTargetDag,
} from "./clew-drop";
import {
  type ClewMode,
  renderClaimsDag,
  renderProjectDag,
  setupModeSelector,
  showFileModeInstructions,
  updateModeButtons,
} from "./clew-modes";

class ClewApp {
  private dagArea: HTMLElement | null = null;
  private detailsPanel: HTMLElement | null = null;
  private projectOwner: string | null = null;
  private projectSlug: string | null = null;
  private projectId: string | null = null;
  private currentMode: ClewMode = "project";

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

    setupModeSelector(
      (mode) => {
        this.currentMode = mode;
        updateModeButtons(mode);
        this.renderCurrentMode();
      },
      () => this.currentMode,
    );

    this.setupEventListeners();
    this.setupDropTarget();
    this.setupHeaderButtons();

    const urlParams = new URLSearchParams(window.location.search);
    const targetFile = urlParams.get("file");
    if (targetFile) {
      this.switchToFileMode();
      if (this.dagArea) {
        await handleFileSelected(
          this.dagArea,
          targetFile,
          this.projectId,
          this.detailsPanel,
        );
      }
    } else {
      await this.renderCurrentMode();
    }
  }

  private switchToFileMode() {
    this.currentMode = "file";
    updateModeButtons("file");
  }

  private async renderCurrentMode() {
    if (!this.dagArea) return;
    switch (this.currentMode) {
      case "project":
        await renderProjectDag(this.dagArea, this.projectId);
        break;
      case "claims":
        await renderClaimsDag(this.dagArea);
        break;
      case "file":
        showFileModeInstructions(this.dagArea);
        break;
    }
  }

  // ── Header buttons ──────────────────────────────────────────────────────
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
      btn.innerHTML = '<i class="fas fa-check"></i> Added';
      this.showExamplesGuidance();
    } else {
      btn.innerHTML = '<i class="fas fa-play-circle"></i> Add Examples';
      btn.disabled = false;
      console.error("[Clew] Failed to add examples:", response.error);
      alert(`Failed to add examples: ${response.error}`);
    }
  }

  private showExamplesGuidance() {
    if (!this.dagArea) return;
    this.dagArea.innerHTML = `
      <div class="dag-placeholder">
        <i class="fas fa-check-circle fa-3x"></i>
        <h3>Examples Ready</h3>
        <p>Example scripts added to <code>examples/clew/</code></p>
        <div class="clew-instructions" style="margin-top:1rem;">
          <div class="clew-direction">
            <h4>Step 1: Run the examples</h4>
            <p>Open a terminal and run:</p>
            <pre><code>cd examples/clew
bash 00_run_all.sh</code></pre>
          </div>
          <div class="clew-direction">
            <h4>Step 2: View the DAG</h4>
            <p>After running, click <strong>Project</strong> to see the full verification DAG.</p>
            <pre><code>scitex clew list
scitex clew status</code></pre>
          </div>
        </div>
      </div>
    `;
  }

  // ── Event listeners ─────────────────────────────────────────────────────
  private setupEventListeners() {
    document.addEventListener("fileSelected", async (event: Event) => {
      const customEvent = event as CustomEvent;
      const filePath = customEvent.detail?.path;
      if (filePath && this.dagArea) {
        this.switchToFileMode();
        await handleFileSelected(
          this.dagArea,
          filePath,
          this.projectId,
          this.detailsPanel,
        );
      }
    });
  }

  // ── Drop target ─────────────────────────────────────────────────────────
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
      const paths = extractDropPaths(e as DragEvent);
      if (paths.length === 0) return;

      this.switchToFileMode();

      if (paths.length > 1) {
        await renderMultiTargetDag(this.dagArea!, paths);
      } else {
        await handleFileSelected(
          this.dagArea!,
          paths[0],
          this.projectId,
          this.detailsPanel,
        );
      }
    });
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
