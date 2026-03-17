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

const FONT_ZOOM_ZONES: import("./context-zoom").FontZoomDef[] = [
  // Note: AI panel and module pane use custom registration below
  // to exclude title bars from zoom
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

/** Register zones where mouse-tracking covers the full panel but zoom
 *  applies only to the content area (excluding title/header bars). */
function registerContentOnlyZoomZones(): void {
  // AI panel: track #scitex-ai-panel, zoom .scitex-ai-body only
  const aiPanel = document.getElementById("scitex-ai-panel");
  const aiBody = aiPanel?.querySelector<HTMLElement>(".scitex-ai-body");
  if (aiPanel && aiBody) {
    registerZoomZone({
      el: aiPanel,
      getSize: () => parseFloat(aiBody.style.zoom || "1"),
      setSize: (val) => {
        aiBody.style.zoom = String(val);
      },
      min: 0.6,
      max: 2.0,
      default: 1.0,
      step: 0.05,
      storageKey: "scitex-ai-panel-zoom",
    });
  }

  // Module pane: track #main-content, zoom .pane-content only
  const mainContent = document.getElementById("main-content");
  const paneContent = mainContent?.querySelector<HTMLElement>(".pane-content");
  if (mainContent && paneContent) {
    registerZoomZone({
      el: mainContent,
      getSize: () => parseFloat(paneContent.style.zoom || "1"),
      setSize: (val) => {
        paneContent.style.zoom = String(val);
      },
      min: 0.6,
      max: 2.0,
      default: 1.0,
      step: 0.05,
      storageKey: "scitex-module-zoom",
    });
  }
}

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
  // Clean stale zoom from panels (zoom now targets content only, not whole panel)
  const aiPanel = document.getElementById("scitex-ai-panel");
  if (aiPanel?.style.zoom) aiPanel.style.zoom = "";
  const mainContent = document.getElementById("main-content");
  if (mainContent?.style.zoom) mainContent.style.zoom = "";

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

/** Track which zones have been registered to avoid duplicate registration. */
const registeredZones = new Set<string>();

function registerOnce(fn: () => void, ...keys: string[]): void {
  const unregistered = keys.filter((k) => !registeredZones.has(k));
  if (unregistered.length === 0) return;
  fn();
  for (const k of keys) registeredZones.add(k);
}

function init(): void {
  cleanupLegacyZoomState();
  bootstrapContextZoom(FONT_ZOOM_ZONES, FONT_SIZE_ZOOM_ZONES);
  // Content-only zoom zones (title bars excluded)
  registerContentOnlyZoomZones();
  registeredZones.add("scitex-ai-panel-zoom");
  registeredZones.add("scitex-module-zoom");
  // Custom zones need MutationObserver too (Monaco/PDF load lazily)
  registerCustomZones();

  const observer = new MutationObserver(() => {
    registerOnce(
      registerContentOnlyZoomZones,
      "scitex-ai-panel-zoom",
      "scitex-module-zoom",
    );
    registerOnce(
      registerCustomZones,
      "scitex-viewer-font-zoom",
      "scitex-pdf-passthrough",
    );
    // Disconnect once all zones are registered
    if (registeredZones.size >= 4) {
      observer.disconnect();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
  setTimeout(() => observer.disconnect(), 30_000);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
