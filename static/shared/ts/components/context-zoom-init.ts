/**
 * Context-Aware Zoom — Centralized Zone Registration
 *
 * Registers ALL workspace panes as zoom zones so that
 * Ctrl+Wheel / Ctrl++/-/0 apply per-pane zoom.
 *
 * Import and call initAllZoomZones() once at app startup
 * (after initContextZoom()).
 */

import {
  initContextZoom,
  registerFontZoom,
  registerZoomZone,
} from "./context-zoom";

/** Pane definitions: selector → localStorage key */
const FONT_ZOOM_ZONES: Array<{ selector: string; key: string }> = [
  // AI panel views
  { selector: "#scitex-ai-chat-view", key: "scitex-ai-chat-zoom" },
  { selector: "#scitex-ai-jobs-list", key: "scitex-ai-jobs-zoom" },
  { selector: ".scitex-ai-config-content", key: "scitex-ai-config-zoom" },
  // NOTE: #scitex-ai-console-terminal is NOT listed here — xterm.js terminals
  // register their own custom zoom zones (adjusting terminal fontSize) in
  // console-mode.ts and console-terminal-factory.ts.
  // Worktree pane
  { selector: ".ws-worktree-tree-area", key: "scitex-worktree-zoom" },
  { selector: ".ws-repo-monitor-area", key: "scitex-repo-monitor-zoom" },
  // Viewer pane
  { selector: "#ws-viewer-preview", key: "scitex-viewer-preview-zoom" },
  { selector: "#ws-viewer-media", key: "scitex-viewer-media-zoom" },
  // Module (center) pane
  { selector: "#main-content", key: "scitex-module-zoom" },
];

/** Show a brief zoom-level badge near the cursor */
let indicatorEl: HTMLElement | null = null;
let indicatorTimer = 0;

function showZoomIndicator(pct: string, x: number, y: number): void {
  if (!indicatorEl) {
    indicatorEl = document.createElement("div");
    indicatorEl.className = "context-zoom-indicator";
    document.body.appendChild(indicatorEl);
  }
  indicatorEl.textContent = pct;
  indicatorEl.style.left = `${x}px`;
  indicatorEl.style.top = `${y}px`;
  indicatorEl.classList.add("visible");
  clearTimeout(indicatorTimer);
  indicatorTimer = window.setTimeout(() => {
    indicatorEl?.classList.remove("visible");
  }, 800);
}

/**
 * Initialize context-aware zoom engine + register all pane zones.
 * Call once at app startup (DOMContentLoaded).
 */
export function initAllZoomZones(): void {
  // Core engine (global Ctrl+Wheel / Ctrl++/-/0 interception)
  initContextZoom();

  // Register font-zoom zones
  for (const { selector, key } of FONT_ZOOM_ZONES) {
    registerFontZoom(selector, key);
  }

  // Monaco: passthrough — it handles its own Ctrl+Wheel zoom
  const monacoEl = document.getElementById("ws-viewer-monaco");
  if (monacoEl) {
    registerZoomZone({
      el: monacoEl,
      getSize: () => 13,
      setSize: () => {},
      min: 8,
      max: 32,
      default: 13,
      storageKey: "scitex-monaco-passthrough",
      passthrough: true,
    });
  }

  // Zoom indicator: listen for zoom changes via wheel/keyboard
  attachZoomIndicator();
}

function attachZoomIndicator(): void {
  let lastMouseX = 0;
  let lastMouseY = 0;

  document.addEventListener("mousemove", (e) => {
    lastMouseX = e.clientX;
    lastMouseY = e.clientY;
  });

  // Ctrl+Wheel indicator
  document.addEventListener(
    "wheel",
    (e) => {
      if (!e.ctrlKey) return;
      // Show indicator after a microtask so the zoom value is updated
      requestAnimationFrame(() => {
        const target = document.elementFromPoint(lastMouseX, lastMouseY);
        if (!target) return;
        const zoomEl = target.closest<HTMLElement>("[style*='zoom']");
        if (zoomEl) {
          const val = parseFloat(zoomEl.style.zoom || "1");
          showZoomIndicator(
            `${Math.round(val * 100)}%`,
            lastMouseX + 16,
            lastMouseY - 24,
          );
        }
      });
    },
    { passive: true },
  );

  // Ctrl++/-/0 indicator
  document.addEventListener("keydown", (e) => {
    if (!e.ctrlKey || e.altKey) return;
    if (e.key === "=" || e.key === "+" || e.key === "-" || e.key === "0") {
      requestAnimationFrame(() => {
        const target = document.elementFromPoint(lastMouseX, lastMouseY);
        if (!target) return;
        const zoomEl = target.closest<HTMLElement>("[style*='zoom']");
        if (zoomEl) {
          const val = parseFloat(zoomEl.style.zoom || "1");
          showZoomIndicator(
            `${Math.round(val * 100)}%`,
            lastMouseX + 16,
            lastMouseY - 24,
          );
        }
      });
    }
  });
}
