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
  registerFontSizeZoom,
  registerFontZoom,
  registerZoomZone,
} from "./context-zoom";

/** Pane definitions: selector → localStorage key (CSS zoom mode) */
const FONT_ZOOM_ZONES: Array<{ selector: string; key: string }> = [
  // AI panel (whole sidebar — CSS neutralizes zoom when collapsed)
  // NOTE: #scitex-ai-console-terminal is NOT listed here — xterm.js terminals
  // register their own custom zoom zones (adjusting terminal fontSize) in
  // console-mode.ts and console-terminal-factory.ts.
  { selector: "#scitex-ai-panel", key: "scitex-ai-panel-zoom" },
  // NOTE: #ws-viewer-sidebar is NOT here — it uses Monaco font-size zoom (registered below)
  // Module (center) pane
  { selector: "#main-content", key: "scitex-module-zoom" },
];

/** Font-size zoom zones — zoom text only, not the container.
 *  target: CSS selector for elements whose font-size is adjusted.
 *  group: zones in the same group synchronize their zoom level. */
const FONT_SIZE_ZOOM_ZONES: Array<{
  selector: string;
  key: string;
  target?: string;
  group?: string;
  defaultSize?: number;
}> = [
  // Worktree pane — zoom file paths in both Files tree and Recent pane
  {
    selector: "#ws-worktree-sidebar",
    key: "scitex-worktree-font-zoom",
    target: ".ws-worktree-split",
    group: "worktree",
    defaultSize: 13,
  },
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
  // CSS-zoom zones (scale everything uniformly)
  for (const { selector, key } of FONT_ZOOM_ZONES) {
    if (registeredSelectors.has(selector)) continue;
    if (registerFontZoom(selector, key)) {
      registeredSelectors.add(selector);
      count++;
      console.debug(`[zoom] CSS-zoom registered: ${selector} (key=${key})`);
    }
  }
  // Font-size zones (scale text only, with target + group support)
  for (const {
    selector,
    key,
    target,
    group,
    defaultSize,
  } of FONT_SIZE_ZOOM_ZONES) {
    if (registeredSelectors.has(selector)) continue;
    if (registerFontSizeZoom(selector, key, { target, group, defaultSize })) {
      registeredSelectors.add(selector);
      count++;
      console.debug(
        `[zoom] font-size registered: ${selector} → target=${target}, group=${group}, default=${defaultSize}px`,
      );
      // Debug: check computed state
      const el = document.querySelector<HTMLElement>(selector);
      const tgt = target ? el?.querySelector<HTMLElement>(target) : el;
      if (tgt) {
        const saved = localStorage.getItem(key);
        console.debug(
          `[zoom]   target computed fontSize=${getComputedStyle(tgt).fontSize}, ` +
            `style.fontSize=${tgt.style.fontSize}, localStorage=${saved}`,
        );
      }
    }
  }
  // Cleanup: remove stale values from old zoom systems
  const wsSidebar = document.getElementById("ws-worktree-sidebar");
  if (wsSidebar && wsSidebar.style.zoom) {
    console.debug(
      `[zoom] clearing stale style.zoom="${wsSidebar.style.zoom}" on #ws-worktree-sidebar`,
    );
    wsSidebar.style.zoom = "";
    localStorage.removeItem("scitex-worktree-zoom");
  }
  // Cleanup: remove stale inline fontSize from old ResizeHandler on .workspace-files-tree
  const filesTree = wsSidebar?.querySelector<HTMLElement>(
    ".workspace-files-tree",
  );
  if (filesTree && filesTree.style.fontSize) {
    console.debug(
      `[zoom] clearing stale style.fontSize="${filesTree.style.fontSize}" on .workspace-files-tree (old ResizeHandler)`,
    );
    filesTree.style.fontSize = "";
    filesTree.style.removeProperty("--wft-icon-size");
  }
  // Remove old ResizeHandler localStorage keys + migrate font-zoom to default
  for (const key of Object.keys(localStorage)) {
    if (key.startsWith("scitex-tree-font-size-")) {
      console.debug(`[zoom] removing old localStorage key: ${key}`);
      localStorage.removeItem(key);
      // One-time migration: reset font-zoom to default since old handler had different scale
      localStorage.removeItem("scitex-worktree-font-zoom");
    }
  }
  // Viewer pane: Monaco font-size zoom (not CSS zoom on sidebar)
  // Uses scale factor (1.0 = 14px default) so indicator shows xx%.
  if (!registeredSelectors.has("#ws-viewer-sidebar")) {
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
      registeredSelectors.add("#ws-viewer-sidebar");
      count++;
    }
  }
  // PDF viewer: passthrough — has its own Ctrl+Wheel zoom via PDF.js
  if (!registeredSelectors.has("#pdf-view")) {
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
      registeredSelectors.add("#pdf-view");
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
  // +font-size zones, +1 viewer sidebar, +1 PDF viewer
  const totalZones = FONT_ZOOM_ZONES.length + FONT_SIZE_ZOOM_ZONES.length + 2;
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
