/**
 * Site dock — behaviour for the one dock on every page (operator, 2026-09-14).
 *
 * Markup: templates/global_base_partials/site_dock.html
 * Styles: static/shared/css/components/site-dock.css
 *
 * 1. Anchors the dock to <body>, so no transformed / zoomed ancestor can turn
 *    its position:fixed into "floats mid-screen" (the iOS failure the old
 *    launcher dock hit, operator msgs 608-610).
 * 2. Drag: the grabber moves the dock anywhere in the viewport. The position is
 *    remembered per device in localStorage. A double-click or double-tap on the
 *    grabber, or dropping the dock back at the bottom, docks it again.
 * 3. Back / Forward: history.back() / history.forward(), enabled from the
 *    in-site history stack (_site-dock/history-stack.ts). Where the browser has
 *    the Navigation API its canGoBack / canGoForward answer is used directly.
 *
 * Every storage access is wrapped: private windows and blocked site data throw,
 * and the dock must work without memory.
 */

import {
  canGoBack,
  canGoForward,
  type HistoryStack,
  type NavigationKind,
  parseStack,
  recordVisit,
} from "./_site-dock/history-stack";
import { initChatPanel } from "./_site-dock/chat-panel";
import {
  type DockPosition,
  fromPixels,
  parsePosition,
  toPixels,
} from "./_site-dock/position";

const POSITION_KEY = "stx-site-dock-position";
const HISTORY_KEY = "stx-site-dock-history";
const DOUBLE_TAP_MS = 320;
const KEY_STEP_PX = 24;

interface NavigationApi {
  canGoBack?: boolean;
  canGoForward?: boolean;
  addEventListener?: (type: string, cb: () => void) => void;
}

function readStorage(store: () => Storage, key: string): string | null {
  try {
    return store().getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(
  store: () => Storage,
  key: string,
  value: string | null,
): void {
  try {
    if (value === null) store().removeItem(key);
    else store().setItem(key, value);
  } catch {
    /* storage unavailable: the dock simply forgets */
  }
}

const local = () => window.localStorage;
const session = () => window.sessionStorage;

function currentUrl(): string {
  return window.location.pathname + window.location.search;
}

function navigationKind(): NavigationKind {
  try {
    const entry = performance.getEntriesByType("navigation")[0] as
      PerformanceNavigationTiming | undefined;
    if (entry?.type) return entry.type as NavigationKind;
  } catch {
    /* fall through */
  }
  return "navigate";
}

class SiteDock {
  private dock: HTMLElement;
  private grabber: HTMLElement | null;
  private back: HTMLButtonElement | null;
  private forward: HTMLButtonElement | null;
  private stack: HistoryStack;
  private lastTap = 0;

  constructor(dock: HTMLElement) {
    this.dock = dock;
    this.grabber = dock.querySelector<HTMLElement>("[data-dock-grabber]");
    this.back = dock.querySelector<HTMLButtonElement>("[data-dock-back]");
    this.forward = dock.querySelector<HTMLButtonElement>("[data-dock-forward]");
    this.stack = parseStack(readStorage(session, HISTORY_KEY));
  }

  init(): void {
    if (this.dock.parentElement !== document.body) {
      document.body.appendChild(this.dock);
    }
    this.restorePosition();
    window.addEventListener("resize", () => this.restorePosition());
    this.initDrag();
    this.initHistory();
    initChatPanel(this.dock);
  }

  /* ── Position ───────────────────────────────────────────── */

  private viewport() {
    return { width: window.innerWidth, height: window.innerHeight };
  }

  private box() {
    const r = this.dock.getBoundingClientRect();
    return { width: r.width, height: r.height };
  }

  private restorePosition(): void {
    const pos = parsePosition(readStorage(local, POSITION_KEY));
    if (!pos) {
      this.dockToBottom();
      return;
    }
    this.float(pos);
  }

  private float(pos: DockPosition): void {
    this.dock.classList.add("site-dock--floating");
    const { left, top } = toPixels(pos, this.box(), this.viewport());
    this.dock.style.left = `${left}px`;
    this.dock.style.top = `${top}px`;
  }

  private dockToBottom(): void {
    this.dock.classList.remove("site-dock--floating");
    this.dock.style.removeProperty("left");
    this.dock.style.removeProperty("top");
  }

  private reset(): void {
    writeStorage(local, POSITION_KEY, null);
    this.dockToBottom();
  }

  private settle(left: number, top: number): void {
    const pos = fromPixels(left, top, this.box(), this.viewport());
    writeStorage(local, POSITION_KEY, pos ? JSON.stringify(pos) : null);
    this.restorePosition();
  }

  private initDrag(): void {
    const grabber = this.grabber;
    if (!grabber) return;

    grabber.addEventListener("dblclick", (e) => {
      e.preventDefault();
      this.reset();
    });

    grabber.addEventListener("pointerdown", (down: PointerEvent) => {
      if (down.pointerType === "mouse" && down.button !== 0) return;
      down.preventDefault();

      const start = this.dock.getBoundingClientRect();
      const offsetX = down.clientX - start.left;
      const offsetY = down.clientY - start.top;
      let moved = false;
      let left = start.left;
      let top = start.top;

      try {
        grabber.setPointerCapture(down.pointerId);
      } catch {
        /* capture is best-effort */
      }

      const onMove = (e: PointerEvent) => {
        if (e.pointerId !== down.pointerId) return;
        if (
          !moved &&
          Math.hypot(e.clientX - down.clientX, e.clientY - down.clientY) < 4
        ) {
          return;
        }
        if (!moved) {
          moved = true;
          this.dock.classList.add("site-dock--floating", "site-dock--dragging");
        }
        const vp = this.viewport();
        left = Math.min(
          Math.max(0, e.clientX - offsetX),
          vp.width - start.width,
        );
        top = Math.min(
          Math.max(0, e.clientY - offsetY),
          vp.height - start.height,
        );
        this.dock.style.left = `${left}px`;
        this.dock.style.top = `${top}px`;
      };

      const onUp = (e: PointerEvent) => {
        if (e.pointerId !== down.pointerId) return;
        grabber.removeEventListener("pointermove", onMove);
        grabber.removeEventListener("pointerup", onUp);
        grabber.removeEventListener("pointercancel", onUp);
        this.dock.classList.remove("site-dock--dragging");
        if (moved) {
          this.settle(left, top);
          return;
        }
        // A tap, not a drag: two taps in quick succession reset (touch has no
        // reliable dblclick).
        const now = Date.now();
        if (e.pointerType !== "mouse" && now - this.lastTap < DOUBLE_TAP_MS) {
          this.reset();
          this.lastTap = 0;
        } else {
          this.lastTap = now;
        }
      };

      grabber.addEventListener("pointermove", onMove);
      grabber.addEventListener("pointerup", onUp);
      grabber.addEventListener("pointercancel", onUp);
    });

    // Keyboard: arrows move the dock, Escape docks it again.
    grabber.addEventListener("keydown", (e: KeyboardEvent) => {
      const delta: Record<string, [number, number]> = {
        ArrowLeft: [-KEY_STEP_PX, 0],
        ArrowRight: [KEY_STEP_PX, 0],
        ArrowUp: [0, -KEY_STEP_PX],
        ArrowDown: [0, KEY_STEP_PX],
      };
      if (e.key === "Escape") {
        e.preventDefault();
        this.reset();
        return;
      }
      const step = delta[e.key];
      if (!step) return;
      e.preventDefault();
      const r = this.dock.getBoundingClientRect();
      this.settle(r.left + step[0], r.top + step[1]);
    });
  }

  /* ── Back / Forward ─────────────────────────────────────── */

  private record(kind: NavigationKind): void {
    this.stack = recordVisit(this.stack, currentUrl(), kind);
    writeStorage(session, HISTORY_KEY, JSON.stringify(this.stack));
    this.syncHistoryButtons();
  }

  private syncHistoryButtons(): void {
    const nav = (window as unknown as { navigation?: NavigationApi })
      .navigation;
    const back =
      typeof nav?.canGoBack === "boolean"
        ? nav.canGoBack
        : canGoBack(this.stack);
    const forward =
      typeof nav?.canGoForward === "boolean"
        ? nav.canGoForward
        : canGoForward(this.stack);
    if (this.back) this.back.disabled = !back;
    if (this.forward) this.forward.disabled = !forward;
  }

  private initHistory(): void {
    this.record(navigationKind());

    this.back?.addEventListener("click", () => history.back());
    this.forward?.addEventListener("click", () => history.forward());

    // Restored from the back/forward cache: the page did not reload, but the
    // user did move along the history.
    window.addEventListener("pageshow", (e: PageTransitionEvent) => {
      if (e.persisted) this.record("back_forward");
    });
    // Same-document moves: workspace modules switch with pushState
    // (app-navigation-history.ts), and Back / Forward over those fire popstate.
    window.addEventListener("popstate", () => this.record("back_forward"));
    const push = history.pushState.bind(history);
    history.pushState = (...args: Parameters<History["pushState"]>) => {
      push(...args);
      this.record("navigate");
    };
    // replaceState rewrites the CURRENT entry's URL; keep the record in step,
    // or a later Back would look for a URL the history no longer holds.
    const replace = history.replaceState.bind(history);
    history.replaceState = (...args: Parameters<History["replaceState"]>) => {
      replace(...args);
      const { entries, index } = this.stack;
      if (index >= 0) {
        const next = entries.slice();
        next[index] = currentUrl();
        this.stack = { entries: next, index };
        writeStorage(session, HISTORY_KEY, JSON.stringify(this.stack));
      }
    };

    const nav = (window as unknown as { navigation?: NavigationApi })
      .navigation;
    nav?.addEventListener?.("currententrychange", () =>
      this.syncHistoryButtons(),
    );
  }
}

function initSiteDock(): void {
  const dock = document.querySelector<HTMLElement>("[data-site-dock]");
  if (!dock || dock.dataset.siteDockReady === "1") return;
  dock.dataset.siteDockReady = "1";
  new SiteDock(dock).init();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initSiteDock);
} else {
  initSiteDock();
}

export { SiteDock };
