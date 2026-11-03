/**
 * Clew rendering helpers — mermaid, images, loading states
 */

import mermaid from "mermaid";
import { interactiveSvg } from "@/utils/diagram-svg";

// Initialize mermaid once at module load
mermaid.initialize({
  startOnLoad: false,
  theme: document.documentElement.classList.contains("dark-mode")
    ? "dark"
    : "default",
  securityLevel: "strict",
  htmlLabels: false,
  flowchart: { curve: "basis", htmlLabels: false },
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
  wrapper.textContent = "Rendering diagram…";
  dagArea.replaceChildren();
  dagArea.appendChild(wrapper);

  try {
    const { svg } = await mermaid.render(containerId, trimmed);
    wrapper.replaceChildren(interactiveSvg(svg));
    setupDagNodeClickHandlers(wrapper);
    return true;
  } catch (err) {
    console.error("[Clew] Mermaid render error:", err);
    const fallback = document.createElement("pre");
    fallback.className = "dag-mermaid-code";
    fallback.textContent = trimmed;
    wrapper.replaceChildren(fallback);
    return false;
  }
}

export function renderImageFile(
  dagArea: HTMLElement,
  filePath: string,
  projectId: string | null,
) {
  const url = new URL(`/api/workspace/file-content/${encodeURIComponent(filePath)}`, location.origin);
  if (projectId !== null) url.searchParams.set("project_id", projectId);
  const wrapper = document.createElement("div");
  wrapper.className = "dag-mermaid-wrapper";
  const image = document.createElement("img");
  image.src = url.href;
  image.alt = "Clew DAG";
  image.style.maxWidth = "100%";
  image.style.height = "auto";
  wrapper.append(image);
  dagArea.replaceChildren(wrapper);
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
  const wrapper = document.createElement("div");
  wrapper.className = "dag-placeholder";
  const symbol = document.createElement("i");
  symbol.className = `fas ${icon} fa-3x`;
  const heading = document.createElement("h3");
  heading.textContent = title;
  const description = document.createElement("p");
  description.textContent = message;
  wrapper.append(symbol, heading, description);
  dagArea.replaceChildren(wrapper);
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
  showPlaceholder(dagArea, "fa-exclamation-triangle", "Error", message);
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
      const label = (node.querySelector(".nodeLabel") ?? node.querySelector(".label"))
        ?.textContent?.trim();
      if (label) {
        document.dispatchEvent(
          new CustomEvent("fileSelected", { detail: { path: label } }),
        );
      }
    });
  });
}
