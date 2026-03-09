/**
 * Clew mode switching logic — Project / Claims / File
 */

import { clewApi, type ClaimInfo } from "./api-client";
import {
  fetchFileContent,
  renderMermaidContent,
  showLoading,
  showPlaceholder,
} from "./clew-rendering";

export type ClewMode = "project" | "claims" | "file";

export function setupModeSelector(
  onModeChange: (mode: ClewMode) => void,
  getCurrentMode: () => ClewMode,
) {
  const selector = document.getElementById("clewModeSelector");
  if (!selector) return;

  selector.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest(".clew-tab") as HTMLElement;
    if (!btn) return;

    const mode = btn.dataset.mode as ClewMode;
    if (mode && mode !== getCurrentMode()) {
      onModeChange(mode);
    }
  });
}

export function updateModeButtons(mode: ClewMode) {
  const selector = document.getElementById("clewModeSelector");
  if (!selector) return;
  selector.querySelectorAll(".clew-tab").forEach((btn) => {
    btn.classList.toggle("active", (btn as HTMLElement).dataset.mode === mode);
  });
  updateModeInfo(mode);
}

const MODE_INFO: Record<ClewMode, string> = {
  project:
    "Visualizes the full verification DAG for all tracked runs. Each node shows a script or file with its SHA-256 hash status — green means verified, red means the file has changed since it was recorded.",
  file: "Drop or select any output file from the file tree to trace its full dependency chain back to the original source data. Multiple files merge into a single DAG.",
  claims:
    "Links specific manuscript assertions (statistics, figures, tables) to the scripts and data that produced them. Register claims with <code>scitex.clew.add_claim()</code> in your analysis scripts.",
};

function updateModeInfo(mode: ClewMode) {
  const infoEl = document.getElementById("clewModeInfo");
  if (!infoEl) return;
  infoEl.innerHTML = MODE_INFO[mode] ?? "";
}

// ── DB status badge ──────────────────────────────────────────────────────
export function updateDbStatusBadge(dbFound: boolean, dbPath: string | null) {
  const actions = document.querySelector(".pane-header-actions");
  if (!actions) return;
  const existing = actions.querySelector(".clew-db-badge");
  if (existing) existing.remove();
  const badge = document.createElement("span");
  badge.className = `clew-db-badge ${dbFound ? "clew-db-badge--found" : "clew-db-badge--missing"}`;
  const label = dbFound ? "DB found" : "No DB";
  const title = dbPath
    ? `${dbFound ? "Database" : "Expected"}: ${dbPath}`
    : "No project database";
  badge.title = title;
  badge.innerHTML = `<i class="fas fa-database"></i> ${label}`;
  actions.appendChild(badge);
}

// ── Project mode ────────────────────────────────────────────────────────
export async function renderProjectDag(
  dagArea: HTMLElement,
  projectId: string | null,
) {
  const response = await clewApi.getStats();
  if (response.success && response.data) {
    updateDbStatusBadge(
      response.data.db_found ?? false,
      response.data.db_path ?? null,
    );
  }
  if (response.success && response.data && response.data.total_runs > 0) {
    showLoading(dagArea);
    const dagResp = await clewApi.getMermaidDag({ pathMode: "name" });
    if (dagResp.success && dagResp.data?.mermaid) {
      await renderMermaidContent(dagArea, dagResp.data.mermaid);
      return;
    }
  }

  // Empty state
  const stats = response.data;
  if (stats && stats.total_runs > 0) {
    dagArea.innerHTML = `
      <div class="dag-placeholder">
        <h3>DAG Visualization</h3>
        <p>${stats.total_runs} runs tracked</p>
      </div>
    `;
  } else {
    dagArea.innerHTML = `
      <div class="dag-placeholder clew-empty-state">
        <h3>No Runs Yet</h3>
        <p class="clew-empty-subtitle">Clew tracks every script run — recording inputs, outputs, and their SHA-256 hashes — then visualizes the full dependency DAG so you can verify reproducibility at any time.</p>
        <div class="clew-instructions clew-instructions-vertical">
          <div class="clew-direction clew-direction-code">
            <h4><i class="fas fa-code"></i> Example Script</h4>
            <pre data-language="python"><code class="language-python">import scitex

@scitex.session
def main():
    data = scitex.io.load("raw_data.csv")
    result = data.groupby("condition").mean()
    scitex.io.save(result, "summary.csv")

    fig, ax = scitex.plt.subplots()
    ax.plot_line(result.index, result.values)
    scitex.io.save(fig, "figure_1.png")</code></pre>
          </div>
          <div class="clew-direction clew-direction-start">
            <h4><i class="fas fa-rocket"></i> Quick Start</h4>
            <ol>
              <li>
                <button class="clew-add-examples-btn btn btn-sm btn-outline-primary">Add Examples</button>
                to load example scripts into this project
              </li>
              <li>Run from project root:
                <pre data-language="bash"><code class="language-bash">bash ./examples/clew/00_run_all.sh</code></pre>
              </li>
              <li>Switch to <strong>Project</strong> mode to view the DAG</li>
            </ol>
            <div class="clew-features">
              <div class="clew-feature">
                <code>scitex.io</code>
                <span>30+ formats (CSV, NumPy, images, pickle, etc.)</span>
              </div>
              <div class="clew-feature">
                <code>scitex.plt</code>
                <span>Publication-ready figures with auto CSV export</span>
              </div>
              <div class="clew-feature">
                <code>scitex.clew</code>
                <span>SHA-256 hashed dependency DAG</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }
}

// ── Claims mode ─────────────────────────────────────────────────────────
export async function renderClaimsDag(dagArea: HTMLElement) {
  showLoading(dagArea);

  const [claimsResp, dagResp] = await Promise.all([
    clewApi.listClaims(),
    clewApi.getMermaidDag({ claims: true, pathMode: "name" }),
  ]);

  if (
    dagResp.success &&
    dagResp.data?.mermaid &&
    dagResp.data.mermaid.trim() !== "graph TD"
  ) {
    await renderMermaidContent(dagArea, dagResp.data.mermaid);
  } else {
    showPlaceholder(
      dagArea,
      "fa-file-contract",
      "No Claims Registered",
      "Claims link specific manuscript assertions (statistics, figures, tables) to the source data and scripts that produced them. Register claims with <code>scitex.clew.add_claim()</code> in your analysis scripts.",
    );
  }

  if (claimsResp.success && claimsResp.data?.claims?.length) {
    renderClaimsList(dagArea, claimsResp.data.claims);
  }
}

function renderClaimsList(dagArea: HTMLElement, claims: ClaimInfo[]) {
  const typeIcons: Record<string, string> = {
    statistic: "fa-chart-bar",
    figure: "fa-image",
    table: "fa-table",
    text: "fa-font",
    value: "fa-hashtag",
  };

  const statusBadges: Record<string, string> = {
    registered: '<span class="badge badge-secondary">Registered</span>',
    verified: '<span class="badge badge-success">Verified</span>',
    mismatch: '<span class="badge badge-danger">Mismatch</span>',
    missing: '<span class="badge badge-warning">Missing</span>',
    partial: '<span class="badge badge-warning">Partial</span>',
  };

  const listHtml = claims
    .map((c) => {
      const icon = typeIcons[c.claim_type] || "fa-question";
      const loc = c.line_number
        ? `${c.file_path.split("/").pop()}:L${c.line_number}`
        : c.file_path.split("/").pop();
      const val = c.claim_value ? ` = ${c.claim_value}` : "";
      const badge = statusBadges[c.status] || statusBadges.registered;
      return `<div class="claim-item">
        <i class="fas ${icon} claim-type-icon"></i>
        <span class="claim-location">${loc}</span>
        <span class="claim-value">${val}</span>
        ${badge}
      </div>`;
    })
    .join("");

  const claimsList = document.createElement("div");
  claimsList.className = "claims-list";
  claimsList.innerHTML = listHtml;
  dagArea.appendChild(claimsList);
}

// ── File mode ───────────────────────────────────────────────────────────
export function showFileModeInstructions(dagArea: HTMLElement) {
  showPlaceholder(
    dagArea,
    "fa-crosshairs",
    "File Trace Mode",
    "Select any output file to trace its full dependency chain back to the original source data as a DAG. Each node shows the script and hash status — green means verified, red means the file has changed since it was recorded.<br><br>" +
      "<span class='text-muted'>Drop multiple files to see a merged DAG.</span>",
  );
}
