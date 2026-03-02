/**
 * Console Auto-Accept Integration
 *
 * Bridges the AutoResponseManager (ported from emacs-claude-code)
 * with the AI panel console terminal. Handles toggle button, state
 * indicator, and localStorage persistence.
 */

import { AutoResponseManager } from "../../../../../apps/console_app/static/console_app/ts/_workspace/terminal/AutoResponseManager";

const STORAGE_KEY = "scitex-auto-accept";

export interface AutoAcceptDeps {
  getWs: () => WebSocket | null;
  getTerminal: () => any;
}

/**
 * Initialize auto-accept: create AutoResponseManager, wire button, restore state.
 * Returns the manager instance for external control.
 */
export function setupAutoAccept(deps: AutoAcceptDeps): AutoResponseManager {
  const btn = document.getElementById("scitex-ai-auto-accept");
  const stateEl = document.getElementById("scitex-ai-auto-accept-state");

  const manager = new AutoResponseManager(
    (text: string) => {
      const ws = deps.getWs();
      if (ws?.readyState === WebSocket.OPEN) ws.send(text);
    },
    () => deps.getTerminal(),
  );

  manager.onStateChange((state, enabled) => {
    if (stateEl) stateEl.textContent = enabled ? state || "" : "";
  });

  manager.onResponseSent((state, response) => {
    console.log(`[Console] Auto-accept: ${state} → "${response || "↵"}"`);
  });

  // Restore saved preference
  if (localStorage.getItem(STORAGE_KEY) === "true") {
    manager.enable();
    btn?.classList.add("active");
  }

  btn?.addEventListener("click", () => {
    const enabled = manager.toggle();
    btn.classList.toggle("active", enabled);
    localStorage.setItem(STORAGE_KEY, String(enabled));
  });

  return manager;
}
