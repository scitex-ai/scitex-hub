/**
 * Pull-to-refresh for the installed PWA (standalone display mode).
 *
 * An iOS home-screen web app has no browser chrome, so there is no native
 * pull-to-refresh and no reload button (operator, 2026-09-15: they refresh
 * often while developing). A browser tab keeps its own, so this stays off
 * there. Site-wide: Home and every app page.
 *
 * A pull counts when it starts where nothing can still scroll up and moves
 * mostly DOWN by more than PULL_THRESHOLD px. It never starts inside a text
 * editing surface or while the dock is being dragged, and a mostly-horizontal
 * gesture (the Home page swipe) cancels it.
 */

export const PULL_THRESHOLD = 70;
/** Movement before the gesture's direction is decided. */
export const DIRECTION_SLOP = 10;
/** Vertical must beat horizontal by this factor to count as a pull. */
export const VERTICAL_DOMINANCE = 1.5;

const EDITING_SURFACES = [
  "textarea",
  "input",
  "select",
  '[contenteditable]:not([contenteditable="false"])',
  ".cm-editor",
  ".CodeMirror",
  ".monaco-editor",
  "canvas",
].join(", ");

const DOCK_DRAG = ".site-dock-grabber, .site-dock--dragging";

/** True when a pull may not start at `target`. */
export function pullBlockedAt(target: Element | null, doc: Document): boolean {
  if (!target) return true;
  if (target.closest(EDITING_SURFACES)) return true;
  if (target.closest(DOCK_DRAG) || doc.querySelector(".site-dock--dragging")) {
    return true;
  }
  // Any ancestor scrolled away from its top can still scroll up, so the finger
  // belongs to that scroller. An element that cannot scroll has scrollTop 0.
  for (let el: Element | null = target; el; el = el.parentElement) {
    if (el.scrollTop > 0) return true;
  }
  const root = doc.scrollingElement;
  return !!root && root.scrollTop > 0;
}

type Phase = "idle" | "pending" | "pulling" | "cancelled";

/** The gesture itself: numbers in, decision out. */
export class PullGesture {
  private phase: Phase = "idle";
  private x0 = 0;
  private y0 = 0;
  private dy = 0;

  start(x: number, y: number, blocked: boolean): void {
    this.phase = blocked ? "cancelled" : "pending";
    this.x0 = x;
    this.y0 = y;
    this.dy = 0;
  }

  /** Returns the current pull distance (0 unless pulling). */
  move(x: number, y: number): number {
    if (this.phase === "idle" || this.phase === "cancelled") return 0;
    const dx = x - this.x0;
    const dy = y - this.y0;
    if (this.phase === "pending") {
      if (Math.abs(dx) < DIRECTION_SLOP && Math.abs(dy) < DIRECTION_SLOP) {
        return 0;
      }
      const vertical = dy > 0 && dy >= Math.abs(dx) * VERTICAL_DOMINANCE;
      this.phase = vertical ? "pulling" : "cancelled";
      if (!vertical) return 0;
    }
    this.dy = Math.max(0, dy);
    return this.dy;
  }

  /** True when the released gesture should refresh. */
  end(): boolean {
    const refresh = this.phase === "pulling" && this.dy > PULL_THRESHOLD;
    this.phase = "idle";
    this.dy = 0;
    return refresh;
  }

  get pulling(): boolean {
    return this.phase === "pulling";
  }
}

export function isStandalone(win: Window): boolean {
  const nav = win.navigator as Navigator & { standalone?: boolean };
  if (nav.standalone === true) return true;
  try {
    return win.matchMedia("(display-mode: standalone)").matches;
  } catch {
    return false;
  }
}

function buildIndicator(doc: Document): HTMLElement {
  const el = doc.createElement("div");
  el.className = "pull-refresh-indicator";
  el.setAttribute("aria-hidden", "true");
  el.style.cssText = [
    "position:fixed",
    "left:50%",
    "top:calc(env(safe-area-inset-top, 0px) + 8px)",
    "z-index:10060",
    "width:32px",
    "height:32px",
    "margin-left:-16px",
    "border-radius:50%",
    "background:var(--bg-secondary, #1c1f28)",
    "box-shadow:0 2px 10px rgba(0,0,0,.3)",
    "display:none",
    "align-items:center",
    "justify-content:center",
    "pointer-events:none",
    "transition:opacity .15s ease",
  ].join(";");
  el.innerHTML =
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="2.5" stroke-linecap="round" style="color:var(--text-primary, #fff)">' +
    '<path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/></svg>';
  doc.body.appendChild(el);
  return el;
}

export interface PullToRefreshOptions {
  reload?: () => void;
}

/** Wires PullGesture to touch events and a small spinner. */
export function installPullToRefresh(
  win: Window,
  options: PullToRefreshOptions = {},
): () => void {
  const doc = win.document;
  const reload = options.reload ?? (() => win.location.reload());
  const gesture = new PullGesture();
  let indicator: HTMLElement | null = null;
  let svg: SVGElement | null = null;

  const show = (distance: number, spinning: boolean) => {
    indicator ??= buildIndicator(doc);
    svg ??= indicator.querySelector("svg");
    const progress = Math.min(1, distance / PULL_THRESHOLD);
    indicator.style.display = distance > 0 || spinning ? "flex" : "none";
    indicator.style.opacity = String(spinning ? 1 : 0.4 + 0.6 * progress);
    indicator.style.transform = `translateY(${Math.min(distance, PULL_THRESHOLD) * 0.6}px)`;
    if (svg) {
      svg.style.transform = `rotate(${progress * 270}deg)`;
      svg.style.animation = spinning
        ? "pull-refresh-spin .7s linear infinite"
        : "";
    }
  };

  if (!doc.getElementById("pull-refresh-style")) {
    const style = doc.createElement("style");
    style.id = "pull-refresh-style";
    style.textContent =
      "@keyframes pull-refresh-spin{to{transform:rotate(360deg)}}";
    doc.head.appendChild(style);
  }

  const onStart = (e: TouchEvent) => {
    if (e.touches.length !== 1) {
      gesture.start(0, 0, true);
      return;
    }
    const t = e.touches[0];
    gesture.start(
      t.clientX,
      t.clientY,
      pullBlockedAt(e.target as Element | null, doc),
    );
  };
  const onMove = (e: TouchEvent) => {
    const t = e.touches[0];
    if (!t) return;
    const distance = gesture.move(t.clientX, t.clientY);
    if (gesture.pulling) show(distance, false);
  };
  const onEnd = () => {
    if (gesture.end()) {
      show(PULL_THRESHOLD, true);
      reload();
    } else if (indicator) {
      show(0, false);
    }
  };

  doc.addEventListener("touchstart", onStart, { passive: true });
  doc.addEventListener("touchmove", onMove, { passive: true });
  doc.addEventListener("touchend", onEnd, { passive: true });
  doc.addEventListener("touchcancel", onEnd, { passive: true });
  return () => {
    doc.removeEventListener("touchstart", onStart);
    doc.removeEventListener("touchmove", onMove);
    doc.removeEventListener("touchend", onEnd);
    doc.removeEventListener("touchcancel", onEnd);
  };
}

function autoInstall(): void {
  if (typeof window === "undefined") return;
  const touch = "ontouchstart" in window || navigator.maxTouchPoints > 0;
  if (!touch || !isStandalone(window)) return;
  installPullToRefresh(window);
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoInstall, { once: true });
  } else {
    autoInstall();
  }
}
