/**
 * Scholar workspace initialization
 * File tree is now handled by shared/workspace-tree-init (auto-init).
 * This file keeps scholar-specific imports and lazy-loaded modules.
 */

// Import PDF download handler (auto-initializes on DOM ready)
import "./search/pdf-download";

// Import search main functionality (auto-initializes on DOM ready)
import "./search/search-main";

document.addEventListener("DOMContentLoaded", async () => {
  // Lazy-load Library tab module on first activation
  const libraryTab = document.querySelector('[data-tab="library"]');
  if (libraryTab) {
    libraryTab.addEventListener(
      "click",
      async () => {
        try {
          const { initLibraryManager } =
            await import("./library/library-manager");
          initLibraryManager();
          console.log("[Scholar] Library manager initialized");
        } catch (error) {
          console.error("[Scholar] Failed to load library manager:", error);
        }
      },
      { once: true },
    );
  }

  console.log("[Scholar] Workspace initialized");
});
