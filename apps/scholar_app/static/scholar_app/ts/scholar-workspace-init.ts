/**
 * Scholar workspace initialization
 * File tree is now handled by shared/workspace-tree-init (auto-init).
 * This file keeps scholar-specific imports and lazy-loaded modules.
 */

// Import PDF download handler (auto-initializes on DOM ready)
import "./search/pdf-download";

// Import search main functionality (auto-initializes on DOM ready)
import "./search/search-main";

// Inline resizers migrated to unified resizer system (data-h-resizer auto-init)

async function initScholarWorkspace(): Promise<void> {
  // Library tab initialization
  let libraryInitialized = false;
  const loadLibrary = async () => {
    if (libraryInitialized) return;
    libraryInitialized = true;
    try {
      const { initLibraryManager } = await import("./library/library-manager");
      initLibraryManager();
      console.log("[Scholar] Library manager initialized");
    } catch (error) {
      console.error("[Scholar] Failed to load library manager:", error);
    }
  };

  // Lazy-load on tab click
  const libraryTab = document.querySelector('[data-tab="library"]');
  if (libraryTab) {
    libraryTab.addEventListener("click", loadLibrary, { once: true });
  }

  // Also init immediately if library is the active tab (default landing)
  const hash = window.location.hash.slice(1);
  if (!hash || hash === "library") {
    loadLibrary();
  }

  console.log("[Scholar] Workspace initialized");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", function () {
    initScholarWorkspace();
  });
} else {
  initScholarWorkspace();
}
