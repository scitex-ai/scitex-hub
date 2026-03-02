/**
 * MermaidViewer - Renders .mmd files as Mermaid diagrams
 *
 * Fetches the raw file content, then renders it with mermaid.js.
 * Reuses the mermaid library already bundled via package.json.
 */

import type { MediaViewerConfig } from "./types";

export class MermaidViewer {
  private config: MediaViewerConfig;

  constructor(config: MediaViewerConfig) {
    this.config = config;
  }

  async render(container: HTMLElement, filePath: string): Promise<void> {
    container.innerHTML =
      '<div class="media-viewer-loading">Loading diagram…</div>';

    try {
      // Fetch file content
      const url = this.config.getFileUrl(filePath, true);
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const ct = response.headers.get("content-type") || "";
      let code: string;
      if (ct.includes("application/json")) {
        const json = await response.json();
        code = (json.content ?? "").trim();
      } else {
        code = (await response.text()).trim();
      }

      if (!code) {
        container.innerHTML =
          '<div class="media-viewer-placeholder">Empty diagram file</div>';
        return;
      }

      // Initialize mermaid (lazy import to avoid bundling in every entry point)
      const { default: mermaid } = await import("mermaid");
      mermaid.initialize({
        startOnLoad: false,
        theme:
          document.documentElement.getAttribute("data-theme") === "dark"
            ? "dark"
            : "default",
        securityLevel: "loose",
      });

      // Build wrapper and render
      const id = `mmd-${Date.now()}`;
      const wrapper = document.createElement("div");
      wrapper.className = "mermaid-viewer-wrapper";
      wrapper.innerHTML = `<div class="mermaid" id="${id}">${code}</div>`;
      container.innerHTML = "";
      container.appendChild(wrapper);

      await mermaid.run({ nodes: [wrapper.querySelector(".mermaid")!] });
    } catch (err) {
      console.error("[MermaidViewer] Render error:", err);
      container.innerHTML = `
        <div class="media-viewer-placeholder">
          <i class="fas fa-exclamation-triangle"></i>
          <p>Failed to render diagram: ${err instanceof Error ? err.message : String(err)}</p>
        </div>
      `;
    }
  }
}
