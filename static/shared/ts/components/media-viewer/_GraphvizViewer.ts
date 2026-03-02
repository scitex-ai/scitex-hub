/**
 * GraphvizViewer - Renders .dot/.gv files as Graphviz diagrams
 *
 * Fetches the raw file content, then renders with @hpcc-js/wasm-graphviz.
 */

import type { MediaViewerConfig } from "./types";

export class GraphvizViewer {
  private config: MediaViewerConfig;

  constructor(config: MediaViewerConfig) {
    this.config = config;
  }

  async render(container: HTMLElement, filePath: string): Promise<void> {
    container.innerHTML =
      '<div class="media-viewer-loading">Loading diagram...</div>';

    try {
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

      const { Graphviz } = await import("@hpcc-js/wasm-graphviz");
      const graphviz = await Graphviz.load();
      const svg = graphviz.dot(code);

      const wrapper = document.createElement("div");
      wrapper.className = "graphviz-viewer-wrapper";
      wrapper.innerHTML = svg;
      container.innerHTML = "";
      container.appendChild(wrapper);
    } catch (err) {
      console.error("[GraphvizViewer] Render error:", err);
      container.innerHTML = `
        <div class="media-viewer-placeholder">
          <i class="fas fa-exclamation-triangle"></i>
          <p>Failed to render diagram: ${err instanceof Error ? err.message : String(err)}</p>
        </div>
      `;
    }
  }
}
