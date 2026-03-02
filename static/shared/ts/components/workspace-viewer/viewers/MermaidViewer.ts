/**
 * MermaidViewer - Fetches .mmd file content and renders it as a Mermaid diagram.
 * Uses lazy import of mermaid to avoid bundling overhead in other entry points.
 */

import type { Viewer } from "../types";
import { getFileUrl } from "../_file-loader";

export class MermaidViewer implements Viewer {
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
      const { default: mermaid } = await import("mermaid");
      mermaid.initialize({
        startOnLoad: false,
        theme:
          document.documentElement.getAttribute("data-theme") === "dark"
            ? "dark"
            : "default",
        securityLevel: "loose",
      });

      const id = `mmd-${Date.now()}`;
      const wrapper = document.createElement("div");
      wrapper.style.cssText = "padding:16px; overflow:auto; height:100%;";
      wrapper.innerHTML = `<div class="mermaid" id="${id}">${code}</div>`;

      container.innerHTML = "";
      container.appendChild(wrapper);

      await mermaid.run({ nodes: [wrapper.querySelector(".mermaid")!] });
    } catch (err) {
      console.error("[MermaidViewer] Render error:", err);
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
