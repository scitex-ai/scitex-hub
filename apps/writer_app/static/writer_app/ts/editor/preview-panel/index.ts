/**
 * Preview Panel Module
 * Central export point for all preview panel functionality
 *
 * @version 2.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/editor/preview-panel/index.ts loaded",
);

// Export types
export type {
  CompilationData,
  CompilationResponse,
  CompilationStatus,
  LatexTemplates,
  PreviewPanelConfig,
} from "./types";

export { LATEX_TEMPLATES } from "./types";

// Export classes
export { PreviewRenderer } from "./_rendering";
export { PreviewNavigation } from "./_navigation";
export { PreviewSync } from "./_sync";
export { PreviewPanelManager } from "./manager";

// Global export for backward compatibility
declare global {
  interface Window {
    PreviewPanelManager: typeof import("./manager").PreviewPanelManager;
    previewPanelManager?: import("./manager").PreviewPanelManager;
  }
}

import { PreviewPanelManager } from "./manager";

// Export to window for access from templates
window.PreviewPanelManager = PreviewPanelManager;

// Auto-initialize from data attributes if config element exists
document.addEventListener("DOMContentLoaded", () => {
  const configEl = document.getElementById("preview-panel-config");
  if (configEl) {
    const config = {
      quickCompileUrl: configEl.dataset.quickCompileUrl || "",
      compilationStatusUrl: configEl.dataset.compilationStatusUrl || "",
      csrfToken:
        document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
          ?.value || "",
    };
    const previewPanel = new PreviewPanelManager(config);
    previewPanel.initialize();
    window.previewPanelManager = previewPanel;
  }
});
