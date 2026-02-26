/**
 * Context-Aware Zoom
 *
 * Tracks which pane the mouse cursor is over and intercepts
 * Ctrl+Wheel / Ctrl++/-/0 to apply zone-specific zoom
 * (font size or scale) instead of browser-wide zoom.
 */

export interface ZoomZone {
  el: HTMLElement;
  getSize: () => number;
  setSize: (px: number) => void;
  min: number;
  max: number;
  default: number;
  storageKey: string;
  /** If true, zone handles zoom internally — just preventDefault */
  passthrough?: boolean;
}

const zones: ZoomZone[] = [];
let activeZone: ZoomZone | null = null;

/**
 * Register a DOM element as a zoom zone.
 * When the cursor is over this element, Ctrl+Wheel and Ctrl++/-/0
 * adjust its font size (or delegate to internal handler for passthrough zones).
 */
export function registerZoomZone(zone: ZoomZone): void {
  zones.push(zone);

  // Restore saved size
  const saved = localStorage.getItem(zone.storageKey);
  if (saved) {
    const size = parseFloat(saved);
    if (size >= zone.min && size <= zone.max) {
      zone.setSize(size);
    }
  }

  zone.el.addEventListener("mouseenter", () => {
    activeZone = zone;
  });
  zone.el.addEventListener("mouseleave", () => {
    if (activeZone === zone) activeZone = null;
  });
}

function adjustZoom(zone: ZoomZone, delta: number): void {
  if (zone.passthrough) return;
  const current = zone.getSize();
  const next = Math.min(zone.max, Math.max(zone.min, current + delta));
  zone.setSize(next);
  localStorage.setItem(zone.storageKey, String(next));
}

function resetZoom(zone: ZoomZone): void {
  if (zone.passthrough) return;
  zone.setSize(zone.default);
  localStorage.setItem(zone.storageKey, String(zone.default));
}

/**
 * Initialize global event listeners for context-aware zoom.
 * Call once at app startup.
 */
export function initContextZoom(): void {
  // Ctrl+Wheel — zoom the zone under the cursor
  document.addEventListener(
    "wheel",
    (e) => {
      if (!e.ctrlKey || !activeZone) return;
      e.preventDefault();
      if (activeZone.passthrough) return;
      const delta = e.deltaY < 0 ? 1 : -1;
      adjustZoom(activeZone, delta);
    },
    { passive: false },
  );

  // Ctrl++/-/0 — zoom the zone under the cursor
  document.addEventListener("keydown", (e) => {
    if (!e.ctrlKey || e.altKey || !activeZone) return;

    if (e.key === "=" || e.key === "+") {
      e.preventDefault();
      adjustZoom(activeZone, 1);
      return;
    }
    if (e.key === "-") {
      e.preventDefault();
      adjustZoom(activeZone, -1);
      return;
    }
    if (e.key === "0") {
      e.preventDefault();
      resetZoom(activeZone);
    }
  });

  console.log("[ContextZoom] Initialized");
}

/**
 * Convenience: register a CSS font-size zoom zone by selector.
 * Returns true if the element was found and registered.
 */
export function registerFontZoom(
  selector: string,
  storageKey: string,
  defaultSize = 13,
  opts?: { passthrough?: boolean; min?: number; max?: number },
): boolean {
  const el = document.querySelector<HTMLElement>(selector);
  if (!el) return false;
  registerZoomZone({
    el,
    getSize: () => parseFloat(getComputedStyle(el).fontSize) || defaultSize,
    setSize: (px) => {
      el.style.fontSize = `${px}px`;
    },
    min: opts?.min ?? 10,
    max: opts?.max ?? 24,
    default: defaultSize,
    storageKey,
    passthrough: opts?.passthrough,
  });
  return true;
}
