/**
 * MermaidViewer
 * Renders .mmd / .mermaid files as Mermaid diagrams in the code workspace.
 */

export class MermaidViewer {
  /**
   * Display a Mermaid diagram file.
   * @param wrapper - Container element
   * @param filePath - Path to the .mmd file (used to fetch content)
   * @param createToolbar - Optional toolbar factory from MediaViewerManager
   */
  async display(
    wrapper: HTMLElement,
    filePath: string,
    createToolbar?: (filePath: string, fileType: string) => HTMLElement,
  ): Promise<void> {
    wrapper.className = "media-viewer-mermaid-wrapper";

    if (createToolbar) {
      wrapper.appendChild(createToolbar(filePath, "mermaid"));
    }

    const content = document.createElement("div");
    content.className = "media-viewer-mermaid-content";
    content.innerHTML =
      '<div class="media-viewer-loading">Loading diagram…</div>';
    wrapper.appendChild(content);

    try {
      // Fetch raw file text from the console API
      const projectData = document.getElementById("project-data");
      const projectId = projectData?.dataset.projectId || "";
      const url = `/code/api/file-content/${filePath}?project_id=${projectId}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const code = (data.content || "").trim();

      if (!code) {
        content.innerHTML =
          '<div class="media-viewer-placeholder">Empty diagram file</div>';
        return;
      }

      // Lazy-import mermaid to keep bundle size minimal
      const { default: mermaid } = await import("mermaid");
      mermaid.initialize({
        startOnLoad: false,
        theme: document.documentElement.classList.contains("dark-mode")
          ? "dark"
          : "default",
        securityLevel: "loose",
      });

      const id = `mmd-${Date.now()}`;
      const diagramEl = document.createElement("div");
      diagramEl.className = "mermaid";
      diagramEl.id = id;
      diagramEl.textContent = code;
      content.innerHTML = "";
      content.appendChild(diagramEl);

      await mermaid.run({ nodes: [diagramEl] });
    } catch (err) {
      console.error("[MermaidViewer] Error:", err);
      content.innerHTML = `
        <div class="media-viewer-placeholder">
          <i class="fas fa-exclamation-triangle"></i>
          <p>Failed to render: ${err instanceof Error ? err.message : String(err)}</p>
        </div>
      `;
    }
  }
}
