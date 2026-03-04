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

const MODE_DEFS: Array<{ mode: ClewMode; label: string; title: string }> = [
  { mode: "project", label: "Project", title: "Show full project DAG" },
  {
    mode: "claims",
    label: "Claims",
    title: "Show claims-based DAG from manuscript",
  },
  { mode: "file", label: "File", title: "Drop or select files to trace" },
];

export function setupModeSelector(
  onModeChange: (mode: ClewMode) => void,
  getCurrentMode: () => ClewMode,
) {
  const header = document.querySelector(".clew-header");
  if (!header) return;

  // Create mode selector if it doesn't exist yet
  let selector = document.getElementById("clewModeSelector");
  if (!selector) {
    selector = document.createElement("div");
    selector.className = "clew-mode-selector";
    selector.id = "clewModeSelector";
    for (const def of MODE_DEFS) {
      const btn = document.createElement("button");
      btn.className = "clew-mode-btn";
      btn.dataset.mode = def.mode;
      btn.title = def.title;
      btn.textContent = def.label;
      if (def.mode === getCurrentMode()) btn.classList.add("active");
      selector.appendChild(btn);
    }
    // Insert after the title span, before any existing buttons
    const firstBtn = header.querySelector("button");
    if (firstBtn) {
      header.insertBefore(selector, firstBtn);
    } else {
      header.appendChild(selector);
    }
  }

  selector.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest(
      ".clew-mode-btn",
    ) as HTMLElement;
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
  selector.querySelectorAll(".clew-mode-btn").forEach((btn) => {
    btn.classList.toggle("active", (btn as HTMLElement).dataset.mode === mode);
  });
}

// ── Project mode ────────────────────────────────────────────────────────
export async function renderProjectDag(
  dagArea: HTMLElement,
  projectId: string | null,
) {
  const response = await clewApi.getStats();
  if (response.success && response.data && response.data.total_runs > 0) {
    showLoading(dagArea);
    const dagResp = await clewApi.getMermaidDag({ pathMode: "name" });
    if (dagResp.success && dagResp.data?.mermaid) {
      await renderMermaidContent(dagArea, dagResp.data.mermaid);
      return;
    }
  }

  // Fallback: try dag.mmd from project
  const dagContent = await fetchFileContent("dag.mmd", projectId);
  if (dagContent) {
    await renderMermaidContent(dagArea, dagContent);
    return;
  }

  // Empty state
  const stats = response.data;
  if (stats && stats.total_runs > 0) {
    dagArea.innerHTML = `
      <div class="dag-placeholder">
        <i class="fas fa-project-diagram fa-3x"></i>
        <h3>DAG Visualization</h3>
        <p>${stats.total_runs} runs tracked</p>
      </div>
    `;
  } else {
    showPlaceholder(
      dagArea,
      "fa-project-diagram",
      "No Runs Yet",
      "Clew tracks reproducibility by recording file hashes during <code>@stx.session</code> runs.<br><br>" +
        "<strong>Quick Start:</strong><br>" +
        "1. Click <strong>Add Examples</strong> to get sample scripts<br>" +
        "2. Run them in the terminal: <code>cd examples/clew &amp;&amp; bash 00_run_all.sh</code><br>" +
        "3. Switch to <strong>Project</strong> mode to view the verification DAG",
    );
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
      "Register claims with <code>stx.clew.add_claim()</code> to link manuscript assertions to source data.",
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
    "Drop file(s) from the file tree or select a file to trace its dependency chain.<br>" +
      "<span class='text-muted'>Drop multiple files to see a merged DAG.</span>",
  );
}
