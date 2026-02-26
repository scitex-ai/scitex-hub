/**
 * GraphvizViewer - Fetches .dot/.gv file content and renders as a Graphviz diagram.
 * Uses lazy import of @hpcc-js/wasm-graphviz to avoid bundling overhead.
 */

import type { Viewer } from "../types.ts";
import { getFileUrl } from "../file-loader.ts";

export class GraphvizViewer implements Viewer {
  private abortController: AbortController | null = null;

  async render(
    container: HTMLElement,
    filePath: string,
    projectId: string,
  ): Promise<void> {
    const apiUrl = getFileUrl(filePath, projectId, false);

    container.innerHTML =
      '<div style="color:#888; padding:10px;">Loading diagram...</div>';
    this.abortController = new AbortController();

    let code: string;
    try {
      const resp = await fetch(apiUrl, { signal: this.abortController.signal });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const ct = resp.headers.get("content-type") || "";
      if (ct.includes("application/json")) {
        const json = await resp.json();
        code = (json.content ?? "").trim();
      } else {
        code = (await resp.text()).trim();
      }
    } catch (err: any) {
      if (err.name === "AbortError") return;
      container.innerHTML = `<div style="color:#e55; padding:10px;">Failed to load: ${filePath}</div>`;
      return;
    }

    if (!code) {
      container.innerHTML =
        '<div style="color:#888; padding:10px;">Empty diagram file</div>';
      return;
    }

    try {
      const { Graphviz } = await import("@hpcc-js/wasm-graphviz");
      const graphviz = await Graphviz.load();
      const svg = graphviz.dot(code);

      const wrapper = document.createElement("div");
      wrapper.style.cssText = "padding:16px; overflow:auto; height:100%;";
      wrapper.innerHTML = svg;

      container.innerHTML = "";
      container.appendChild(wrapper);
    } catch (err) {
      console.error("[GraphvizViewer] Render error:", err);
      container.innerHTML = `
        <div style="color:#e55; padding:10px;">
          Failed to render diagram: ${err instanceof Error ? err.message : String(err)}
        </div>
      `;
    }
  }

  destroy(): void {
    this.abortController?.abort();
    this.abortController = null;
  }
}
