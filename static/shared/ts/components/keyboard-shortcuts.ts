/**
 * Centralized Keyboard Shortcuts for SciTeX — command-ID wired.
 *
 * Every shell action below is registered under a STABLE command ID (the same
 * IDs served by `GET /accounts/api/keymap/` and customized in Settings >
 * Keyboard Shortcuts). Keyboard dispatch, buttons, and agents converge on
 * `runHubCommand(id, via)` — no caller invokes an action directly.
 *
 * Default chords (overridable per user, same IDs):
 *
 * Alt+A          — ai-panel:toggle (Toggle AI panel + focus chat input)
 * Alt+T          — pane:cycle-next (Cycle focus to next pane)
 * Alt+Shift+T    — pane:cycle-prev (Cycle focus to previous pane)
 * Alt+Right      — pane:focus-next (Focus next (right) pane)
 * Alt+Left       — pane:focus-prev (Focus previous (left) pane)
 * Alt+Shift+Right — pane:collapse-right (Collapse current pane rightward)
 * Alt+Shift+Left  — pane:collapse-left (Collapse current pane leftward)
 * Ctrl+U         — file:upload (Upload files to AI chat)
 *
 * Hub globals fire inside inputs too (the chat input focuses/owns several of
 * these chords) — preserved from the pre-wiring handler. The server refuses
 * same-scope conflicts at bind time, so an applied payload is conflict-free
 * by construction.
 */

/** Stable command IDs — mirrors scitex-ui `keymap_defaults()` keys. */
export const HUB_COMMAND_IDS = [
  "ai-panel:toggle",
  "pane:cycle-next",
  "pane:cycle-prev",
  "pane:focus-next",
  "pane:focus-prev",
  "pane:collapse-right",
  "pane:collapse-left",
  "file:upload",
] as const;

export type HubCommandId = (typeof HUB_COMMAND_IDS)[number];

/** Who dispatched a command — the seam a future macro layer keys off. */
export type HubCommandCaller = "keyboard" | "button" | "agent" | "program";

/** Raw KeyboardEvent terms, as served by the keymap API `match` field. */
export interface ChordMatch {
  key: string;
  ctrl: boolean;
  alt: boolean;
  shift: boolean;
  meta: boolean;
}

interface PaneInfo {
  el: HTMLElement;
  toggleBtn: HTMLElement | null;
  isCollapsed: () => boolean;
  toggle: () => void;
}

function getOrderedPanes(): PaneInfo[] {
  const panes: PaneInfo[] = [];

  // AI panel (leftmost)
  const aiPanel = document.getElementById("stx-shell-ai-panel");
  if (aiPanel) {
    const aiToggle =
      document.getElementById("stx-shell-ai-toggle") ??
      document.getElementById("stx-shell-ai-fab");
    panes.push({
      el: aiPanel,
      toggleBtn: aiToggle,
      isCollapsed: () => aiPanel.classList.contains("collapsed"),
      toggle: () => aiToggle?.click(),
    });
  }

  // Main content (center — never collapsible)
  const main = document.getElementById("main-content");
  if (main) {
    panes.push({
      el: main,
      toggleBtn: null,
      isCollapsed: () => false,
      toggle: () => {},
    });
  }

  // Workspace sidebar panels (right side) — detected via data-panel-resizer
  const resizers = document.querySelectorAll<HTMLElement>(
    "[data-panel-resizer]:not(#stx-shell-ai-resizer)",
  );
  for (const r of resizers) {
    const target = r.dataset.target;
    if (!target) continue;
    const panel = document.querySelector<HTMLElement>(target);
    if (!panel || panel === aiPanel) continue;

    const toggleId = r.dataset.toggleBtn;
    const toggleBtn = toggleId ? document.getElementById(toggleId) : null;
    panes.push({
      el: panel,
      toggleBtn,
      isCollapsed: () => panel.classList.contains("collapsed"),
      toggle: () => toggleBtn?.click(),
    });
  }

  return panes;
}

let focusedPaneIndex = -1;

function focusPane(pane: PaneInfo): void {
  const focusable = pane.el.querySelector<HTMLElement>(
    "textarea, input:not([type=hidden]), [tabindex]",
  );
  if (focusable) {
    focusable.focus();
  } else {
    pane.el.focus();
  }
}

function cyclePanes(direction: 1 | -1): void {
  const panes = getOrderedPanes();
  if (panes.length === 0) return;

  // Find current focus
  const active = document.activeElement as HTMLElement;
  let idx = panes.findIndex((p) => p.el.contains(active));
  if (idx < 0) idx = focusedPaneIndex >= 0 ? focusedPaneIndex : 0;

  const next = (idx + direction + panes.length) % panes.length;
  const target = panes[next];

  // Expand if collapsed
  if (target.isCollapsed()) target.toggle();

  focusedPaneIndex = next;
  focusPane(target);
}

function curtainCollapse(direction: "left" | "right"): void {
  const panes = getOrderedPanes();
  if (direction === "left") {
    // Collapse leftward: find rightmost expanded collapsible pane
    for (let i = panes.length - 1; i >= 0; i--) {
      if (panes[i].toggleBtn && !panes[i].isCollapsed()) {
        panes[i].toggle();
        return;
      }
    }
  } else {
    // Collapse rightward: find leftmost expanded collapsible pane
    for (let i = 0; i < panes.length; i++) {
      if (panes[i].toggleBtn && !panes[i].isCollapsed()) {
        panes[i].toggle();
        return;
      }
    }
  }
}

function toggleAIPanel(): void {
  const fab = document.getElementById("stx-shell-ai-fab");
  const toggle = document.getElementById("stx-shell-ai-toggle");
  const panel = document.getElementById("stx-shell-ai-panel");
  const input = document.getElementById(
    "stx-shell-ai-input",
  ) as HTMLTextAreaElement | null;
  const terminal = document.getElementById("stx-shell-ai-console-terminal");

  if (panel?.classList.contains("collapsed")) {
    // Expand panel and focus the active mode (chat input or console)
    (fab ?? toggle)?.click();
    setTimeout(() => {
      const isConsole = terminal?.closest(".stx-shell-ai-view.active");
      if (isConsole && (window as any).aiPanelConsole) {
        (window as any).aiPanelConsole.focus();
      } else {
        input?.focus();
      }
    }, 260);
  } else {
    // Panel is open — check if focus is already inside
    const hasFocus = panel?.contains(document.activeElement);
    if (hasFocus) {
      // Already focused inside panel → collapse it
      (fab ?? toggle)?.click();
    } else {
      // Focus is elsewhere → bring focus to panel
      const isConsole = terminal?.closest(".stx-shell-ai-view.active");
      if (isConsole && (window as any).aiPanelConsole) {
        (window as any).aiPanelConsole.focus();
      } else {
        input?.focus();
      }
    }
  }
}

function triggerFileUpload(): void {
  // Create a temporary file input
  const input = document.createElement("input");
  input.type = "file";
  input.multiple = true;
  input.style.display = "none";

  input.addEventListener("change", async () => {
    if (!input.files || input.files.length === 0) return;

    const form = new FormData();
    for (let i = 0; i < input.files.length; i++) {
      form.append("files", input.files[i]);
    }

    const csrf =
      document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
        ?.value ??
      (document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "");

    try {
      const resp = await fetch("/apps/llm/api/upload/", {
        method: "POST",
        headers: { "X-CSRFToken": csrf },
        body: form,
      });
      if (!resp.ok) throw new Error(`Upload failed: ${resp.status}`);
      const data = (await resp.json()) as { paths: string[] };

      // Insert paths into chat input
      const chatInput = document.getElementById(
        "stx-shell-ai-input",
      ) as HTMLTextAreaElement | null;
      if (chatInput && data.paths.length > 0) {
        const label =
          data.paths.length === 1
            ? `Uploaded file: ${data.paths[0]}`
            : `Uploaded files:\n${data.paths.map((p) => `  ${p}`).join("\n")}`;
        const existing = chatInput.value.trim();
        chatInput.value = existing ? `${existing}\n${label}` : label;
        chatInput.focus();
      }
    } catch (err) {
      console.error("[Shortcuts] File upload error:", err);
    }

    input.remove();
  });

  document.body.appendChild(input);
  input.click();
}

/** Default chords in raw event terms — exactly the pre-wiring behavior. */
const DEFAULT_MATCHERS: Record<HubCommandId, ChordMatch> = {
  "ai-panel:toggle": { key: "a", ctrl: false, alt: true, shift: false, meta: false },
  "pane:cycle-next": { key: "t", ctrl: false, alt: true, shift: false, meta: false },
  "pane:cycle-prev": { key: "t", ctrl: false, alt: true, shift: true, meta: false },
  "pane:focus-next": { key: "ArrowRight", ctrl: false, alt: true, shift: false, meta: false },
  "pane:focus-prev": { key: "ArrowLeft", ctrl: false, alt: true, shift: false, meta: false },
  "pane:collapse-right": { key: "ArrowRight", ctrl: false, alt: true, shift: true, meta: false },
  "pane:collapse-left": { key: "ArrowLeft", ctrl: false, alt: true, shift: true, meta: false },
  "file:upload": { key: "u", ctrl: true, alt: false, shift: false, meta: false },
};

/** Live matchers: defaults until the keymap API payload is applied. */
const liveMatchers: Map<HubCommandId, ChordMatch | null> = new Map(
  HUB_COMMAND_IDS.map((id) => [id, { ...DEFAULT_MATCHERS[id] }]),
);

/** Command actions — the single dispatch target. */
const commandActions: Record<HubCommandId, () => void> = {
  "ai-panel:toggle": toggleAIPanel,
  "pane:cycle-next": () => cyclePanes(1),
  "pane:cycle-prev": () => cyclePanes(-1),
  "pane:focus-next": () => cyclePanes(1),
  "pane:focus-prev": () => cyclePanes(-1),
  "pane:collapse-right": () => curtainCollapse("right"),
  "pane:collapse-left": () => curtainCollapse("left"),
  "file:upload": triggerFileUpload,
};

/**
 * Run a hub command by stable ID. Keyboard, buttons, and agents converge
 * here. Returns true when a registered, currently-bound command ran.
 */
export function runHubCommand(
  id: string,
  _via: HubCommandCaller = "program",
): boolean {
  if (!isHubCommandId(id)) return false;
  if (liveMatchers.get(id) === null) return false; // explicitly unbound
  commandActions[id]();
  return true;
}

function isHubCommandId(id: string): id is HubCommandId {
  return (HUB_COMMAND_IDS as readonly string[]).includes(id);
}

function eventMatches(
  ev: { key: string; ctrlKey: boolean; altKey: boolean; shiftKey: boolean; metaKey: boolean },
  matcher: ChordMatch,
): boolean {
  if (
    ev.ctrlKey !== matcher.ctrl ||
    ev.altKey !== matcher.alt ||
    ev.shiftKey !== matcher.shift ||
    ev.metaKey !== matcher.meta
  ) {
    return false;
  }
  // Single letters match case-insensitively (Shift state is already compared
  // above, so "t" covers both Alt+T and Alt+Shift+T slots distinctly).
  if (matcher.key.length === 1 && ev.key.length === 1) {
    return ev.key.toLowerCase() === matcher.key.toLowerCase();
  }
  return ev.key === matcher.key;
}

function resolveCommandForEvent(ev: {
  key: string;
  ctrlKey: boolean;
  altKey: boolean;
  shiftKey: boolean;
  metaKey: boolean;
}): HubCommandId | null {
  for (const id of HUB_COMMAND_IDS) {
    const matcher = liveMatchers.get(id);
    if (matcher && eventMatches(ev, matcher)) return id;
  }
  return null;
}

export interface KeymapApiCommand {
  scope: string;
  sequence: string | null;
  match: ChordMatch | null;
  bound: boolean;
}

/**
 * Apply a `GET /accounts/api/keymap/` payload: per-user overrides replace
 * default chords, unbound commands stop responding. Unknown IDs are ignored
 * so leaf-app page-mode commands never disturb the shell table.
 */
export function applyKeymapPayload(
  commands: Record<string, KeymapApiCommand>,
): void {
  for (const id of HUB_COMMAND_IDS) {
    const entry = commands[id];
    if (!entry) continue;
    if (!entry.bound || !entry.match) {
      liveMatchers.set(id, null);
    } else {
      liveMatchers.set(id, { ...entry.match });
    }
  }
}

/** Reset live matchers to defaults (tests + teardown). */
export function resetKeymapMatchers(): void {
  for (const id of HUB_COMMAND_IDS) {
    liveMatchers.set(id, { ...DEFAULT_MATCHERS[id] });
  }
}

async function fetchAndApplyUserKeymap(): Promise<void> {
  let response: Response;
  try {
    response = await fetch("/accounts/api/keymap/", { credentials: "same-origin" });
  } catch (error) {
    console.warn("[Shortcuts] User keymap unreachable, keeping defaults:", error);
    return;
  }
  const contentType = response.headers.get("content-type") ?? "";
  if (!response.ok || !contentType.includes("application/json")) {
    console.warn(
      `[Shortcuts] User keymap unavailable (HTTP ${response.status}), keeping defaults.`,
    );
    return;
  }
  try {
    const payload = (await response.json()) as { commands?: Record<string, KeymapApiCommand> };
    if (payload && typeof payload.commands === "object") {
      applyKeymapPayload(payload.commands);
    }
  } catch (error) {
    console.warn("[Shortcuts] User keymap unreadable, keeping defaults:", error);
  }
}

export function initKeyboardShortcuts(): void {
  document.addEventListener("keydown", (e) => {
    const id = resolveCommandForEvent(e);
    if (id === null) return;
    e.preventDefault();
    runHubCommand(id, "keyboard");
  });
  // Defaults are live immediately; the user's overrides swap in when the
  // fetch resolves. Failure keeps defaults (see fetchAndApplyUserKeymap).
  void fetchAndApplyUserKeymap();
}
