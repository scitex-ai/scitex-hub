/**
 * Context-Aware Zoom — Centralized Zone Registration
 *
 * Registers ALL workspace panes as zoom zones so that
 * Ctrl+Wheel / Ctrl++/-/0 apply per-pane zoom.
 *
 * Self-initializing: auto-runs on DOMContentLoaded when loaded via
 * {% vite_script %}.  Also watches for lazy-loaded panes via
 * MutationObserver so dynamically-added elements get zoom too.
 */

import {
  getActiveZone,
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
  // Viewer pane (whole pane — covers empty state, preview, and media)
  { selector: "#ws-viewer-pane", key: "scitex-viewer-zoom" },
  // Module (center) pane
  { selector: "#main-content", key: "scitex-module-zoom" },
];

/** Track which selectors have been successfully registered */
const registeredSelectors = new Set<string>();

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

/** Format current zoom level for the indicator badge. Works for all zone types. */
function getZoomLabel(): string | null {
  const zone = getActiveZone();
  if (!zone || zone.passthrough) return null;
  const val = zone.getSize();
  // CSS zoom zones: value is a scale factor (e.g. 1.0 = 100%)
  if (zone.step && zone.step < 1) {
    return `${Math.round(val * 100)}%`;
  }
  // Pixel-based zones (e.g. terminal fontSize): show "13px"
  return `${Math.round(val)}px`;
}

/** Try to register any not-yet-registered zones. Returns count of newly registered. */
function registerPendingZones(): number {
  let count = 0;
  for (const { selector, key } of FONT_ZOOM_ZONES) {
    if (registeredSelectors.has(selector)) continue;
    if (registerFontZoom(selector, key)) {
      registeredSelectors.add(selector);
      count++;
    }
  }
  // Monaco: passthrough — it handles its own Ctrl+Wheel zoom
  if (!registeredSelectors.has("#ws-viewer-monaco")) {
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
      registeredSelectors.add("#ws-viewer-monaco");
      count++;
    }
  }
  return count;
}

/**
 * Initialize context-aware zoom engine + register all pane zones.
 * Idempotent — safe to call multiple times.
 */
let initialized = false;
export function initAllZoomZones(): void {
  if (initialized) return;
  initialized = true;

  // Core engine (global Ctrl+Wheel / Ctrl++/-/0 interception)
  initContextZoom();

  // Register all currently-available zones
  registerPendingZones();

  // Watch for lazy-loaded panes via MutationObserver
  const totalZones = FONT_ZOOM_ZONES.length + 1; // +1 for Monaco
  if (registeredSelectors.size < totalZones) {
    const observer = new MutationObserver(() => {
      const newCount = registerPendingZones();
      if (newCount > 0 && registeredSelectors.size >= totalZones) {
        observer.disconnect();
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    // Safety: stop observing after 30s even if not all zones found
    setTimeout(() => observer.disconnect(), 30_000);
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

  // Unified indicator: show zoom level for the active zone (any type)
  function showActiveZoneIndicator(): void {
    requestAnimationFrame(() => {
      const label = getZoomLabel();
      if (label) {
        showZoomIndicator(label, lastMouseX + 16, lastMouseY - 24);
      }
    });
  }

  // Ctrl+Wheel indicator
  document.addEventListener(
    "wheel",
    (e) => {
      if (!e.ctrlKey) return;
      showActiveZoneIndicator();
    },
    { passive: true },
  );

  // Ctrl++/-/0 indicator
  document.addEventListener("keydown", (e) => {
    if (!e.ctrlKey || e.altKey) return;
    if (e.key === "=" || e.key === "+" || e.key === "-" || e.key === "0") {
      showActiveZoneIndicator();
    }
  });
}

// ── Self-initialize on DOM ready ──────────────────────────────────────
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => initAllZoomZones());
} else {
  initAllZoomZones();
}
