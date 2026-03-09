/**
 * Scholar workspace initialization
 * File tree is now handled by shared/workspace-tree-init (auto-init).
 * This file keeps scholar-specific imports and lazy-loaded modules.
 */

// Library tab init (deferred until tab is visible, persistent MutationObserver)
import "./library/library-init";

// Import PDF download handler (auto-initializes on DOM ready)
import "./search/_pdf-download";

// Import search main functionality (auto-initializes on DOM ready)
import "./search/_search-main";

// Inline resizers migrated to unified resizer system (data-h-resizer auto-init)

if (document.readyState !== "loading") {
  console.log("[Scholar] Workspace initialized");
} else {
  document.addEventListener("DOMContentLoaded", () => {
    console.log("[Scholar] Workspace initialized");
  });
}
