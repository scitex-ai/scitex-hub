/**
 * figrecipe-bridge-init — entry point for mounting the figrecipe React editor.
 *
 * Replaces the old iframe + postMessage integration.
 * Auto-discovers mount point and project context from DOM data attributes.
 */

import {
  mountFigrecipeEditor,
  wireVisEditorBridge,
  switchRecipeFile,
} from "./_figrecipe-bridge/index";

const RECIPE_EXTS = [".yaml", ".yml"];

function init(): void {
  const mount = document.getElementById("figrecipe-mount");
  if (!mount) return;

  const isEmbedded = mount.dataset.embedded === "true";
  const workingDir = mount.dataset.workingDir;
  const splitView = document.querySelector(
    ".workspace-split-view",
  ) as HTMLElement | null;

  if (isEmbedded) {
    // Embedded mode: mount React editor immediately
    mountFigrecipeEditor({
      container: mount,
      workingDir,
      darkMode: document.body.classList.contains("dark-theme"),
    });

    // Wire bridge to VisEditor when it becomes available
    const checkVisEditor = setInterval(() => {
      const ve = (window as any).visEditor;
      if (ve?.instance) {
        wireVisEditorBridge(ve.instance);
        clearInterval(checkVisEditor);
      }
    }, 200);
    // Stop checking after 10s
    setTimeout(() => clearInterval(checkVisEditor), 10000);
  } else {
    // Standalone mode: mount on demand when recipe file is clicked
    function openInFigrecipe(recipePath: string): void {
      if (!mount || !splitView) return;
      mount.style.display = "block";
      splitView.style.display = "none";
      mountFigrecipeEditor({
        container: mount,
        workingDir,
        recipe: recipePath,
        darkMode: document.body.classList.contains("dark-theme"),
      });
    }

    function closeFigrecipe(): void {
      if (!mount || !splitView) return;
      mount.style.display = "none";
      splitView.style.display = "";
    }

    (window as any).openInFigrecipe = openInFigrecipe;
    (window as any).closeFigrecipe = closeFigrecipe;

    // Intercept file tree clicks for recipe files
    document.addEventListener("click", (e: Event) => {
      const link = (e.target as Element)?.closest("[data-file-path]");
      if (!link) return;

      const path = link.getAttribute("data-file-path") || "";
      const ext = path.substring(path.lastIndexOf(".")).toLowerCase();

      if (RECIPE_EXTS.includes(ext)) {
        e.preventDefault();
        e.stopPropagation();
        openInFigrecipe(path);
      }
    });
  }
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
