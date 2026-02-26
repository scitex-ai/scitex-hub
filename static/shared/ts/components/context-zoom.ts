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
  setSize: (val: number) => void;
  min: number;
  max: number;
  default: number;
  storageKey: string;
  /** Step per scroll tick (default 1 for px, 0.05 for CSS zoom) */
  step?: number;
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

function adjustZoom(zone: ZoomZone, direction: number): void {
  if (zone.passthrough) return;
  const step = zone.step ?? 1;
  const current = zone.getSize();
  const raw = current + direction * step;
  // Round to avoid float drift (e.g. 1.0500000000000003)
  const next = Math.min(
    zone.max,
    Math.max(zone.min, Math.round(raw * 1000) / 1000),
  );
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
      if (!e.ctrlKey) return;
      if (!activeZone) return;
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
}

/**
 * Convenience: register a CSS-zoom zone by selector.
 * Uses the `zoom` property so ALL content (text, padding, borders) scales uniformly,
 * even when child elements have explicit px font sizes.
 * Returns true if the element was found and registered.
 */
export function registerFontZoom(
  selector: string,
  storageKey: string,
  _defaultSize = 13,
  opts?: { passthrough?: boolean; min?: number; max?: number },
): boolean {
  const el = document.querySelector<HTMLElement>(selector);
  if (!el) return false;
  registerZoomZone({
    el,
    getSize: () => parseFloat(el.style.zoom || "1"),
    setSize: (val) => {
      el.style.zoom = String(val);
    },
    min: opts?.min ?? 0.6,
    max: opts?.max ?? 2.0,
    default: 1.0,
    step: 0.05,
    storageKey,
    passthrough: opts?.passthrough,
  });
  return true;
}
