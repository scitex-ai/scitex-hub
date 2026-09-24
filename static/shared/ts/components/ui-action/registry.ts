/**
 * Named UI Action Registry — the Emacs `M-x` layer for the SciTeX web UI.
 *
 * Every user-facing UI mutation should be invocable BY NAME, by humans
 * (future command palette) and by agents alike:
 *
 *   SciTeX.actions.list()                       // [{name, description, args}]
 *   await SciTeX.actions.invoke("chat.send", {text: "hello"})
 *   SciTeX.actions.macro("demo", [{action:"chat.send", args:{...}}])
 *
 * Agents reach it through the existing transports without new backend:
 *   - `eval_js` API  →  `SciTeX.actions.invoke("chat.send", {...})`
 *   - `ui_action` tool → raw verbs (navigate/click/fill/...) for one-shots
 *
 * Macros persist in localStorage (`scitex.macros.v1`) so users and agents
 * can record once and replay by name.
 */

export interface ActionArgSpec {
  [arg: string]: string;
}

export interface ActionDef {
  name: string;
  description: string;
  args?: ActionArgSpec;
  run: (args: Record<string, unknown>) => unknown | Promise<unknown>;
}

export interface MacroStep {
  action: string;
  args?: Record<string, unknown>;
}

const registry = new Map<string, ActionDef>();
const MACRO_KEY = "scitex.macros.v1";

export function defineAction(def: ActionDef): void {
  registry.set(def.name, def);
}

export function listActions(): Array<{
  name: string;
  description: string;
  args?: ActionArgSpec;
}> {
  return Array.from(registry.values()).map((d) => ({
    name: d.name,
    description: d.description,
    ...(d.args ? { args: d.args } : {}),
  }));
}

export async function invokeAction(
  name: string,
  args: Record<string, unknown> = {},
): Promise<{ ok: boolean; result?: unknown; error?: string }> {
  const def = registry.get(name);
  if (!def) return { ok: false, error: `unknown action: ${name}` };
  try {
    const result = await def.run(args);
    return { ok: true, result: result ?? null };
  } catch (err) {
    return { ok: false, error: String(err) };
  }
}

/* ── macros ─────────────────────────────────────────────────────────── */

function readMacros(): Record<string, MacroStep[]> {
  try {
    return JSON.parse(localStorage.getItem(MACRO_KEY) || "{}");
  } catch {
    return {};
  }
}

export function defineMacro(name: string, steps: MacroStep[]): void {
  const all = readMacros();
  all[name] = steps;
  try {
    localStorage.setItem(MACRO_KEY, JSON.stringify(all));
  } catch {
    /* storage unavailable — macro lives for this page only */
  }
  defineAction({
    name: `macro.${name}`,
    description: `Recorded macro (${steps.length} steps).`,
    run: () => runMacro(name),
  });
}

export async function runMacro(name: string): Promise<unknown[]> {
  const steps = readMacros()[name];
  if (!steps) throw new Error(`unknown macro: ${name}`);
  const out: unknown[] = [];
  for (const s of steps) {
    const r = await invokeAction(s.action, s.args || {});
    out.push(r);
    if (!r.ok) break;
  }
  return out;
}

/* ── builtins ───────────────────────────────────────────────────────── */

function el(sel: unknown): HTMLElement {
  const node = document.querySelector(String(sel ?? ""));
  if (!node) throw new Error(`no element: ${sel}`);
  return node as HTMLElement;
}

function snapshot(): Record<string, unknown> {
  const pick = (s: string, n: number): string[] =>
    Array.from(document.querySelectorAll(s))
      .slice(0, n)
      .map((e) => {
        const h = e as HTMLElement;
        const label = (
          h.getAttribute("aria-label") ||
          h.textContent ||
          ""
        ).trim().replace(/\s+/g, " ").slice(0, 60);
        return `${s}[${label}]`;
      });
  return {
    title: document.title,
    url: location.href,
    buttons: pick("button", 40),
    inputs: pick("input,textarea,select", 20),
    headings: pick("h1,h2,h3", 15),
  };
}

function registerBuiltins(): void {
  defineAction({
    name: "ui.snapshot",
    description: "Readable summary of the current page (title, url, buttons, inputs, headings) so an agent can decide what to do next.",
    run: () => snapshot(),
  });
  defineAction({
    name: "ui.click",
    description: "Click the first element matching a CSS selector.",
    args: { selector: "css selector" },
    run: ({ selector }) => {
      el(selector).click();
      return true;
    },
  });
  defineAction({
    name: "ui.fill",
    description: "Set the value of an input/textarea and fire input events.",
    args: { selector: "css selector", value: "text to type" },
    run: ({ selector, value }) => {
      const node = el(selector) as HTMLInputElement;
      node.focus();
      (node as HTMLInputElement).value = String(value ?? "");
      node.dispatchEvent(new Event("input", { bubbles: true }));
      node.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    },
  });
  defineAction({
    name: "ui.navigate",
    description: "Go to a path within this SciTeX Cloud site.",
    args: { url: "/path or full url" },
    run: ({ url }) => {
      location.href = String(url);
      return true;
    },
  });
  defineAction({
    name: "chat.send",
    description: "Send a chat message via whichever chat composer is present.",
    args: { text: "message text" },
    run: async ({ text }) => {
      const box = document.querySelector(
        "#chat-welcome-input,#chat-input,#stx-shell-ai-input,#appmaker-chat-input",
      ) as HTMLTextAreaElement | null;
      if (!box) throw new Error("no chat composer on this page");
      box.focus();
      box.value = String(text ?? "");
      box.dispatchEvent(new Event("input", { bubbles: true }));
      const form = box.closest("form");
      if (form) {
        form.requestSubmit();
      } else {
        box.dispatchEvent(
          new KeyboardEvent("keydown", { key: "Enter", bubbles: true }),
        );
      }
      return true;
    },
  });
  // Re-register persisted macros as macro.<name> actions.
  for (const [name, steps] of Object.entries(readMacros())) {
    defineAction({
      name: `macro.${name}`,
      description: `Recorded macro (${(steps as MacroStep[]).length} steps).`,
      run: () => runMacro(name),
    });
  }
}

/** Call once at boot (alongside initEvalJsRelay). Idempotent. */
export function initActionRegistry(): void {
  if ((window as unknown as { __scitexActions?: unknown }).__scitexActions)
    return;
  registerBuiltins();
  const api = {
    list: listActions,
    invoke: invokeAction,
    define: defineAction,
    macro: defineMacro,
  };
  (window as unknown as { __scitexActions?: unknown }).__scitexActions = api;
  const scitex = ((window as unknown as { SciTeX?: Record<string, unknown> }).SciTeX =
    (window as unknown as { SciTeX?: Record<string, unknown> }).SciTeX || {});
  scitex["actions"] = api;
}
