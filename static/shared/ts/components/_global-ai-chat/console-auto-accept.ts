/**
 * Console Auto-Accept Integration
 *
 * Bridges the AutoResponseManager (ported from emacs-claude-code)
 * with the AI panel console terminal. Handles toggle button, state
 * indicator, config UI, and localStorage persistence.
 */

import { AutoResponseManager } from "../../../../../apps/console_app/static/console_app/ts/_workspace/terminal/AutoResponseManager";

const STORAGE_KEY = "scitex-auto-accept";
const INTERVAL_KEY = "scitex-auto-accept-interval";
const SAFETY_KEY = "scitex-auto-accept-safety";

const SAFETY_PRESETS: Record<
  string,
  { burstLimit: number; sameStateDelay: number; burstWindow: number }
> = {
  conservative: { burstLimit: 5, sameStateDelay: 3000, burstWindow: 5000 },
  normal: { burstLimit: 10, sameStateDelay: 1500, burstWindow: 3000 },
  aggressive: { burstLimit: 20, sameStateDelay: 800, burstWindow: 2000 },
};

export interface AutoAcceptDeps {
  getWs: () => WebSocket | null;
  getTerminal: () => any;
}

/**
 * Initialize auto-accept: create AutoResponseManager, wire button + config, restore state.
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

  // Restore saved config
  const savedInterval = localStorage.getItem(INTERVAL_KEY);
  const savedSafety = localStorage.getItem(SAFETY_KEY);
  if (savedInterval || savedSafety) {
    const partial: Record<string, number> = {};
    if (savedInterval) partial.interval = parseInt(savedInterval, 10);
    if (savedSafety && SAFETY_PRESETS[savedSafety]) {
      Object.assign(partial, SAFETY_PRESETS[savedSafety]);
    }
    manager.updateConfig(partial);
  }

  // Restore enabled state
  if (localStorage.getItem(STORAGE_KEY) === "true") {
    manager.enable();
    btn?.classList.add("active");
  }

  btn?.addEventListener("click", () => {
    const enabled = manager.toggle();
    btn.classList.toggle("active", enabled);
    localStorage.setItem(STORAGE_KEY, String(enabled));
  });

  // Wire config UI selects
  wireConfigSelects(manager);

  return manager;
}

function wireConfigSelects(manager: AutoResponseManager): void {
  const intervalSel = document.getElementById(
    "ai-auto-accept-interval",
  ) as HTMLSelectElement | null;
  const safetySel = document.getElementById(
    "ai-auto-accept-safety",
  ) as HTMLSelectElement | null;

  // Restore UI from saved values
  const savedInterval = localStorage.getItem(INTERVAL_KEY);
  const savedSafety = localStorage.getItem(SAFETY_KEY);
  if (intervalSel && savedInterval) intervalSel.value = savedInterval;
  if (safetySel && savedSafety) safetySel.value = savedSafety;

  intervalSel?.addEventListener("change", () => {
    const val = parseInt(intervalSel.value, 10);
    localStorage.setItem(INTERVAL_KEY, intervalSel.value);
    manager.updateConfig({ interval: val });
  });

  safetySel?.addEventListener("change", () => {
    const preset = SAFETY_PRESETS[safetySel.value];
    if (!preset) return;
    localStorage.setItem(SAFETY_KEY, safetySel.value);
    manager.updateConfig(preset);
  });
}
