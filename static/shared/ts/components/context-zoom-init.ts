/**
 * Context-Aware Zoom — Centralized Zone Registration
 *
 * Uses scitex-ui's bootstrapContextZoom for standard zones,
 * plus custom zones for Monaco editor and PDF viewer.
 *
 * Self-initializing: auto-runs on DOMContentLoaded when loaded via
 * {% vite_script %}.
 */

import { bootstrapContextZoom, registerZoomZone } from "./context-zoom";

// ── Standard zones (handled by bootstrapContextZoom) ────────────────

const FONT_ZOOM_ZONES = [
  // AI panel (whole sidebar)
  // NOTE: xterm.js terminals register their own zones in console-mode.ts
  { selector: "#scitex-ai-panel", storageKey: "scitex-ai-panel-zoom" },
  // Module (center) pane
  { selector: "#main-content", storageKey: "scitex-module-zoom" },
];

const FONT_SIZE_ZOOM_ZONES = [
  // Worktree pane — zoom file paths
  {
    selector: "#ws-worktree-sidebar",
    storageKey: "scitex-worktree-font-zoom",
    target: ".ws-worktree-split",
    group: "worktree",
    defaultSize: 13,
  },
];

// ── Custom zones (registered after bootstrap) ───────────────────────

function registerCustomZones(): void {
  // Viewer pane: Monaco font-size zoom via scale factor
  const viewerSidebar = document.getElementById("ws-viewer-sidebar");
  if (viewerSidebar) {
    // Clean up stale CSS zoom from old system
    if (viewerSidebar.style.zoom) {
      viewerSidebar.style.zoom = "";
      localStorage.removeItem("scitex-viewer-zoom");
    }
    const BASE_FONT = 14;
    const STORAGE_KEY = "scitex-viewer-font-zoom";
    registerZoomZone({
      el: viewerSidebar,
      getSize: () => {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved ? parseFloat(saved) : 1.0;
      },
      setSize: (scale) => {
        const fontSize = Math.round(scale * BASE_FONT);
        const monaco = (window as any).monaco;
        if (monaco) {
          for (const ed of monaco.editor.getEditors()) {
            if (viewerSidebar.contains(ed.getDomNode())) {
              ed.updateOptions({ fontSize });
            }
          }
        }
      },
      min: 0.6,
      max: 2.5,
      default: 1.0,
      step: 0.05,
      storageKey: STORAGE_KEY,
    });
  }

  // PDF viewer: passthrough — PDF.js handles its own Ctrl+Wheel zoom
  const pdfEl = document.getElementById("pdf-view");
  if (pdfEl) {
    registerZoomZone({
      el: pdfEl,
      getSize: () => 1,
      setSize: () => {},
      min: 0.5,
      max: 3.0,
      default: 1.0,
      storageKey: "scitex-pdf-passthrough",
      passthrough: true,
    });
  }
}

// ── Legacy cleanup ──────────────────────────────────────────────────

function cleanupLegacyZoomState(): void {
  const wsSidebar = document.getElementById("ws-worktree-sidebar");
  if (wsSidebar?.style.zoom) {
    wsSidebar.style.zoom = "";
    localStorage.removeItem("scitex-worktree-zoom");
  }
  const filesTree = wsSidebar?.querySelector<HTMLElement>(
    ".workspace-files-tree",
  );
  if (filesTree?.style.fontSize) {
    filesTree.style.fontSize = "";
    filesTree.style.removeProperty("--wft-icon-size");
  }
  for (const key of Object.keys(localStorage)) {
    if (key.startsWith("scitex-tree-font-size-")) {
      localStorage.removeItem(key);
      localStorage.removeItem("scitex-worktree-font-zoom");
    }
  }
}

// ── Initialize ──────────────────────────────────────────────────────

function init(): void {
  cleanupLegacyZoomState();
  bootstrapContextZoom(FONT_ZOOM_ZONES, FONT_SIZE_ZOOM_ZONES);
  // Custom zones need MutationObserver too (Monaco/PDF load lazily)
  const observer = new MutationObserver(() => {
    registerCustomZones();
  });
  observer.observe(document.body, { childList: true, subtree: true });
  setTimeout(() => observer.disconnect(), 30_000);
  // Try immediately too
  registerCustomZones();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
