/**
 * App Navigation History — unified navigation engine using browser history API.
 *
 * Single source of truth for in-app navigation. Mouse buttons 3/4 call
 * history.back()/forward(), which triggers popstate, which dispatches to
 * registered restore handlers.
 *
 * Modules integrate via:
 *   window._appNav.push({ module: "writer" })   — new history entry
 *   window._appNav.replace({ file: "foo.py" })   — update current entry
 *   window._appNav.onRestore(state => { ... })    — handle back/forward
 */

export {};

interface NavState {
  _scitex: true;
  module: string;
  file?: string;
  aiMode?: string;
  timestamp: number;
}

type RestoreHandler = (state: NavState) => void;

const DEBOUNCE_MS = 300;

class AppNavigationHistory {
  private handlers: RestoreHandler[] = [];
  private restoring = false;
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
  private pendingPush: NavState | null = null;

  constructor() {
    this.seedInitialState();
    this.listenPopstate();
    this.interceptMouseButtons();
  }

  /** Push a new history entry (module switch, file open). */
  push(partial: Partial<Omit<NavState, "_scitex" | "timestamp">>): void {
    if (this.restoring) return;

    const merged = this.mergeState(partial);

    // Skip duplicate
    const cur = this.current();
    if (cur && this.statesEqual(cur, merged)) return;

    // Debounce rapid file-only changes
    if (
      cur &&
      merged.module === cur.module &&
      merged.file !== cur.file &&
      !this.moduleChanged(cur, merged)
    ) {
      this.pendingPush = merged;
      // Immediately update current state so UI reflects the change
      history.replaceState(merged, "", this.buildUrl(merged));
      if (this.debounceTimer) clearTimeout(this.debounceTimer);
      this.debounceTimer = setTimeout(() => {
        if (this.pendingPush) {
          history.pushState(
            this.pendingPush,
            "",
            this.buildUrl(this.pendingPush),
          );
          this.pendingPush = null;
        }
      }, DEBOUNCE_MS);
      return;
    }

    // Flush any pending debounced push before a new distinct push
    this.flushPending();
    history.pushState(merged, "", this.buildUrl(merged));
  }

  /** Update current history entry in-place (AI mode, supplementary data). */
  replace(partial: Partial<Omit<NavState, "_scitex" | "timestamp">>): void {
    if (this.restoring) return;
    const merged = this.mergeState(partial);
    history.replaceState(merged, "", this.buildUrl(merged));
  }

  /** Register a handler called on back/forward navigation. */
  onRestore(handler: RestoreHandler): void {
    this.handlers.push(handler);
  }

  /** Get the current navigation state. */
  current(): NavState | null {
    const s = history.state;
    return s && s._scitex ? (s as NavState) : null;
  }

  // ── Private ──────────────────────────────────────────────

  private mergeState(
    partial: Partial<Omit<NavState, "_scitex" | "timestamp">>,
  ): NavState {
    const cur = this.current();
    return {
      _scitex: true,
      module: partial.module ?? cur?.module ?? this.detectModule(),
      file: partial.file ?? cur?.file,
      aiMode: partial.aiMode ?? cur?.aiMode,
      timestamp: Date.now(),
    };
  }

  private seedInitialState(): void {
    if (!history.state?._scitex) {
      const state: NavState = {
        _scitex: true,
        module: this.detectModule(),
        timestamp: Date.now(),
      };
      history.replaceState(state, "", location.href);
    }
  }

  private listenPopstate(): void {
    window.addEventListener("popstate", (e) => {
      const state = e.state as NavState | null;
      if (!state?._scitex) return;
      this.dispatch(state);
    });
  }

  private interceptMouseButtons(): void {
    // Mouse button 3 = back, 4 = forward
    window.addEventListener(
      "mouseup",
      (e: MouseEvent) => {
        if (e.button === 3) {
          e.preventDefault();
          history.back();
        } else if (e.button === 4) {
          e.preventDefault();
          history.forward();
        }
      },
      { capture: true },
    );

    // Prevent default browser back/forward on auxiliary click
    window.addEventListener(
      "auxclick",
      (e: MouseEvent) => {
        if (e.button === 3 || e.button === 4) {
          e.preventDefault();
        }
      },
      { capture: true },
    );
  }

  private dispatch(state: NavState): void {
    this.restoring = true;
    try {
      for (const handler of this.handlers) {
        handler(state);
      }
    } finally {
      this.restoring = false;
    }
  }

  private flushPending(): void {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }
    if (this.pendingPush) {
      history.pushState(this.pendingPush, "", this.buildUrl(this.pendingPush));
      this.pendingPush = null;
    }
  }

  private buildUrl(state: NavState): string {
    const isWorkspaceShell = location.pathname.startsWith("/apps/workspace/");
    if (isWorkspaceShell) {
      return `/apps/workspace/${state.module}/`;
    }
    return `/apps/${state.module}/`;
  }

  private detectModule(): string {
    const match = location.pathname.match(
      /^\/(?:apps\/|workspace\/)?([a-z][a-z0-9_-]+)\//,
    );
    return match ? match[1] : "writer";
  }

  private statesEqual(a: NavState, b: NavState): boolean {
    return a.module === b.module && a.file === b.file && a.aiMode === b.aiMode;
  }

  private moduleChanged(a: NavState, b: NavState): boolean {
    return a.module !== b.module;
  }
}

// ── Singleton & Global ──────────────────────────────────────

const appNav = new AppNavigationHistory();

declare global {
  interface Window {
    _appNav: AppNavigationHistory;
  }
}

window._appNav = appNav;

console.debug(
  "[AppNav] Unified navigation engine active — mouse back/forward + history API",
);
