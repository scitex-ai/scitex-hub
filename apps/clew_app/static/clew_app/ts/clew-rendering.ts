/**
 * Clew rendering helpers — mermaid, images, loading states
 */

import mermaid from "mermaid";

// Initialize mermaid once at module load
mermaid.initialize({
  startOnLoad: false,
  theme: document.documentElement.classList.contains("dark-mode")
    ? "dark"
    : "default",
  securityLevel: "loose",
  flowchart: { curve: "basis" },
});

export async function renderMermaidContent(
  dagArea: HTMLElement,
  code: string,
): Promise<boolean> {
  const trimmed = code.trim();
  if (!trimmed || trimmed === "graph TD") {
    showError(dagArea, "Empty diagram");
    return false;
  }

  const containerId = "mermaid-dag-" + Date.now();
  const wrapper = document.createElement("div");
  wrapper.className = "dag-mermaid-wrapper";
  wrapper.innerHTML = `<div class="mermaid" id="${containerId}">${trimmed}</div>`;
  dagArea.innerHTML = "";
  dagArea.appendChild(wrapper);

  try {
    await mermaid.run({ nodes: [wrapper.querySelector(".mermaid")!] });
    setupDagNodeClickHandlers(wrapper);
    return true;
  } catch (err) {
    console.error("[Clew] Mermaid render error:", err);
    wrapper.innerHTML = `<pre class="dag-mermaid-code">${trimmed}</pre>`;
    return false;
  }
}

export function renderImageFile(
  dagArea: HTMLElement,
  filePath: string,
  projectId: string | null,
) {
  const url = `/api/workspace/file-content/${encodeURIComponent(filePath)}?project_id=${projectId}`;
  dagArea.innerHTML = `
    <div class="dag-mermaid-wrapper">
      <img src="${url}" alt="Clew DAG" style="max-width:100%;height:auto;" />
    </div>
  `;
}

export async function fetchFileContent(
  filePath: string,
  projectId: string | null,
): Promise<string | null> {
  try {
    const url = `/api/workspace/file-content/${encodeURIComponent(filePath)}?project_id=${projectId}`;
    const resp = await fetch(url);
    if (!resp.ok) return null;
    const data = await resp.json();
    if (data.success && data.content) return data.content;
    return null;
  } catch {
    return null;
  }
}

export function showPlaceholder(
  dagArea: HTMLElement,
  icon: string,
  title: string,
  message: string,
) {
  dagArea.innerHTML = `
    <div class="dag-placeholder">
      <i class="fas ${icon} fa-3x"></i>
      <h3>${title}</h3>
      <p>${message}</p>
    </div>
  `;
}

export function showLoading(dagArea: HTMLElement) {
  dagArea.innerHTML = `
    <div class="dag-placeholder">
      <i class="fas fa-spinner fa-spin fa-3x"></i>
      <h3>Loading...</h3>
      <p>Fetching verification data</p>
    </div>
  `;
}

export function showError(dagArea: HTMLElement, message: string) {
  dagArea.innerHTML = `
    <div class="dag-placeholder">
      <i class="fas fa-exclamation-triangle fa-3x"></i>
      <h3>Error</h3>
      <p>${message}</p>
    </div>
  `;
}

export function getStatusBadge(status: string): string {
  const badges: Record<string, string> = {
    verified: '<span class="badge badge-success">Verified</span>',
    mismatch: '<span class="badge badge-danger">Mismatch</span>',
    missing: '<span class="badge badge-warning">Missing</span>',
    unknown: '<span class="badge badge-secondary">Unknown</span>',
  };
  return badges[status] || badges.unknown;
}

function setupDagNodeClickHandlers(wrapper: HTMLElement) {
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
