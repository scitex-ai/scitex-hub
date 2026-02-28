/**
 * App Navigation History — in-app action history for mouse back/forward buttons.
 *
 * Tracks user actions (module switches, file opens, panel changes) and lets
 * mouse buttons 3 (back) and 4 (forward) navigate through them instead of
 * triggering browser-level history navigation.
 *
 * Modules push entries via window._appNav.push({ module, action, data }).
 * Navigation handlers restore state via registered callbacks.
 */

// Make this file a module so `declare global` works
export {};

interface NavEntry {
  module: string;
  action: string;
  data: unknown;
  timestamp: number;
}

type NavHandler = (entry: NavEntry) => void;

const MAX_STACK_SIZE = 100;

class AppNavigationHistory {
  private stack: NavEntry[] = [];
  private cursor = -1;
  private handlers: NavHandler[] = [];
  private navigating = false;

  /** Push a new navigation entry. Truncates forward history. */
  push(entry: Omit<NavEntry, "timestamp">): void {
    if (this.navigating) return;

    const full: NavEntry = { ...entry, timestamp: Date.now() };

    // Don't push duplicate of current entry
    if (this.cursor >= 0) {
      const current = this.stack[this.cursor];
      if (
        current.module === full.module &&
        current.action === full.action &&
        JSON.stringify(current.data) === JSON.stringify(full.data)
      ) {
        return;
      }
    }

    // Truncate forward history
    this.stack = this.stack.slice(0, this.cursor + 1);
    this.stack.push(full);

    // Cap size
    if (this.stack.length > MAX_STACK_SIZE) {
      this.stack = this.stack.slice(this.stack.length - MAX_STACK_SIZE);
    }

    this.cursor = this.stack.length - 1;
  }

  /** Navigate back. Returns the entry navigated to, or null. */
  back(): NavEntry | null {
    if (this.cursor <= 0) return null;
    this.cursor--;
    const entry = this.stack[this.cursor];
    this.dispatch(entry);
    return entry;
  }

  /** Navigate forward. Returns the entry navigated to, or null. */
  forward(): NavEntry | null {
    if (this.cursor >= this.stack.length - 1) return null;
    this.cursor++;
    const entry = this.stack[this.cursor];
    this.dispatch(entry);
    return entry;
  }

  /** Register a handler called when navigating back/forward. */
  onNavigate(handler: NavHandler): void {
    this.handlers.push(handler);
  }

  /** Current entry (for debugging). */
  current(): NavEntry | null {
    return this.cursor >= 0 ? this.stack[this.cursor] : null;
  }

  private dispatch(entry: NavEntry): void {
    this.navigating = true;
    try {
      for (const handler of this.handlers) {
        handler(entry);
      }
    } finally {
      this.navigating = false;
    }
  }
}

const appNav = new AppNavigationHistory();

// ---------------------------------------------------------------------------
// Mouse button interception (buttons 3 = back, 4 = forward)
// ---------------------------------------------------------------------------
window.addEventListener(
  "mouseup",
  (e: MouseEvent) => {
    if (e.button === 3) {
      e.preventDefault();
      appNav.back();
    } else if (e.button === 4) {
      e.preventDefault();
      appNav.forward();
    }
  },
  { capture: true },
);

// Also prevent the default browser back/forward on auxiliary click
window.addEventListener(
  "auxclick",
  (e: MouseEvent) => {
    if (e.button === 3 || e.button === 4) {
      e.preventDefault();
    }
  },
  { capture: true },
);

// ---------------------------------------------------------------------------
// Default navigation handler — module switching
// ---------------------------------------------------------------------------
appNav.onNavigate((entry: NavEntry) => {
  if (entry.action === "switch-module") {
    const currentModule = extractCurrentModule();
    if (currentModule !== entry.module) {
      window.location.href = `/${entry.module}/`;
    }
  }
});

function extractCurrentModule(): string | null {
  const match = window.location.pathname.match(/^\/([a-z]+)\//);
  return match ? match[1] : null;
}

// ---------------------------------------------------------------------------
// Auto-track module page loads
// ---------------------------------------------------------------------------
function trackCurrentModule(): void {
  const mod = extractCurrentModule();
  if (mod) {
    appNav.push({ module: mod, action: "switch-module", data: null });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", trackCurrentModule);
} else {
  trackCurrentModule();
}

// ---------------------------------------------------------------------------
// Expose globally
// ---------------------------------------------------------------------------
declare global {
  interface Window {
    _appNav: AppNavigationHistory;
  }
}

window._appNav = appNav;

console.debug(
  "[AppNav] Navigation history active — mouse back/forward enabled",
);
