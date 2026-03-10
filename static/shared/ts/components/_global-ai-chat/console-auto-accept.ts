/**
 * Console Auto-Accept Integration
 *
 * Bridges the AutoResponseManager (ported from emacs-claude-code)
 * with the AI panel console terminal. Handles toggle button, state
 * indicator, config UI, and localStorage persistence.
 *
 * Response commands (waiting, y_n, y_y_n) are loaded from the server
 * API and saved back on change, with localStorage as fallback.
 */

import { AutoResponseManager } from "../../../../../apps/workspace/console_app/static/console_app/ts/_workspace/terminal/AutoResponseManager";
import { getCsrfToken } from "../../utils/csrf";
import { API_URLS } from "../../utils/api-urls";

const STORAGE_KEY = "scitex-auto-accept";
const INTERVAL_KEY = "scitex-auto-accept-interval";
const SAFETY_KEY = "scitex-auto-accept-safety";
const RESPONSES_KEY = "scitex-auto-accept-responses";

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

  manager.onResponseSent((_state, _response) => {});

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

  // Load and wire response config from server
  loadResponsePrefs(manager);

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

// --- Response config (server-backed) ---

interface ResponsePrefs {
  y_n: string;
  y_y_n: string;
  waiting: string;
  suggestion: string;
}

function applyResponses(
  manager: AutoResponseManager,
  prefs: ResponsePrefs,
): void {
  manager.updateConfig({
    responses: {
      y_n: prefs.y_n,
      y_y_n: prefs.y_y_n,
      waiting: prefs.waiting,
      suggestion: prefs.suggestion,
    },
  } as any);
}

function populateResponseUI(prefs: ResponsePrefs): void {
  const waitingInput = document.getElementById(
    "ai-auto-response-waiting",
  ) as HTMLInputElement | null;
  const ynSel = document.getElementById(
    "ai-auto-response-yn",
  ) as HTMLSelectElement | null;
  const yynSel = document.getElementById(
    "ai-auto-response-yyn",
  ) as HTMLSelectElement | null;

  if (waitingInput) waitingInput.value = prefs.waiting || "";
  if (ynSel) ynSel.value = prefs.y_n || "1";
  if (yynSel) yynSel.value = prefs.y_y_n || "2";
}

let saveTimer: ReturnType<typeof setTimeout> | null = null;

function saveResponsePrefs(prefs: ResponsePrefs): void {
  localStorage.setItem(RESPONSES_KEY, JSON.stringify(prefs));

  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    fetch(API_URLS.accounts.autoResponsePrefs, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(prefs),
    }).catch(() => {});
  }, 800);
}

function wireResponseInputs(manager: AutoResponseManager): void {
  const waitingInput = document.getElementById(
    "ai-auto-response-waiting",
  ) as HTMLInputElement | null;
  const ynSel = document.getElementById(
    "ai-auto-response-yn",
  ) as HTMLSelectElement | null;
  const yynSel = document.getElementById(
    "ai-auto-response-yyn",
  ) as HTMLSelectElement | null;

  const getCurrentPrefs = (): ResponsePrefs => ({
    y_n: ynSel?.value || "1",
    y_y_n: yynSel?.value || "2",
    waiting: waitingInput?.value || "/speak-signature",
    suggestion: "",
  });

  const onChanged = () => {
    const prefs = getCurrentPrefs();
    applyResponses(manager, prefs);
    saveResponsePrefs(prefs);
  };

  waitingInput?.addEventListener("change", onChanged);
  ynSel?.addEventListener("change", onChanged);
  yynSel?.addEventListener("change", onChanged);
}

function loadResponsePrefs(manager: AutoResponseManager): void {
  // Try localStorage first for immediate apply
  const cached = localStorage.getItem(RESPONSES_KEY);
  if (cached) {
    try {
      const prefs = JSON.parse(cached) as ResponsePrefs;
      applyResponses(manager, prefs);
      populateResponseUI(prefs);
    } catch {
      // ignore parse errors
    }
  }

  // Then fetch from server (authoritative)
  fetch(API_URLS.accounts.autoResponsePrefs)
    .then((r) => (r.ok ? r.json() : null))
    .then((data) => {
      if (!data?.responses) return;
      const prefs = data.responses as ResponsePrefs;
      applyResponses(manager, prefs);
      populateResponseUI(prefs);
      localStorage.setItem(RESPONSES_KEY, JSON.stringify(prefs));
    })
    .catch(() => {})
    .finally(() => {
      wireResponseInputs(manager);
    });
}
