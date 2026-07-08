/**
 * Workspace Shell — Tab switching without page reload.
 * AI Agent pane and Worktree pane remain cached in DOM.
 * Only #ws-module-pane is replaced on tab click.
 */

import { initNewPanels } from "@/components/workspace-panel-resizer";

const STORAGE_KEY = "ws-active-module";
const DEFAULT_MODULE = "home";
const CONTENT_BASE = "/apps/workspace/content/";

/** Read module names from the DOM data attribute set by the registry context processor. */
function getKnownModules(): string[] {
  const nav = document.querySelector("[data-workspace-modules]");
  if (nav) {
    const csv = (nav as HTMLElement).dataset.workspaceModules ?? "";
    if (csv) return csv.split(",");
  }
  // Fallback: use data-module attributes on tab buttons
  const names: string[] = [];
  document.querySelectorAll(".module-tab-btn").forEach((btn) => {
    const mod = (btn as HTMLElement).dataset.module;
    if (mod) names.push(mod);
  });
  return names;
}

let KNOWN_MODULES: string[] = [];

async function switchModule(name: string): Promise<void> {
  const pane = document.getElementById("ws-module-pane");
  const loading = document.getElementById("ws-module-loading");
  if (!pane) return;

  // Show loading
  if (loading) loading.style.display = "flex";
  pane.style.opacity = "0.5";

  try {
    const resp = await fetch(`${CONTENT_BASE}${name}/`, {
      headers: { "X-Workspace-Shell": "1" },
      credentials: "same-origin",
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const html = await resp.text();
    pane.innerHTML = html;
    reLoadStyles(pane);
    reExecScripts(pane);
    // Wire up resize handles inside the injected partial. Auto-init
    // ran on DOMContentLoaded, long before this content existed —
    // without the late init, injected [data-panel-resizer] /
    // [data-v-resizer] handles show the resize cursor (CSS) but have
    // no drag listeners (nav-404 batch #10). Same dance as
    // module-tab-switcher.ts.
    document.dispatchEvent(
      new CustomEvent("workspace:module-injected", {
        detail: { module: name },
      }),
    );
    (window as any).initNewResizers?.();
    initNewPanels();
    updateActiveTab(name);
    window._appNav?.push({ module: name });
    localStorage.setItem(STORAGE_KEY, name);
    document
      .getElementById("workspace-shell")
      ?.setAttribute("data-active-module", name);
    // Update module pane accent for top-border highlight
    const mainEl = document.getElementById("main-content");
    if (mainEl) mainEl.setAttribute("data-app-accent", name);
  } catch (err) {
    console.error("[workspace-shell] Failed to load module:", name, err);
    pane.innerHTML = `<div style="padding:2rem;color:var(--text-muted)">
      <i class="fas fa-exclamation-triangle"></i> Failed to load ${name}.
    </div>`;
  } finally {
    if (loading) loading.style.display = "none";
    pane.style.opacity = "";
  }
}

function reExecScripts(container: HTMLElement): void {
  container.querySelectorAll("script").forEach((old) => {
    const s = document.createElement("script");
    Array.from(old.attributes).forEach((a) => s.setAttribute(a.name, a.value));
    s.textContent = old.textContent;
    old.replaceWith(s);
  });
}

/** Move <link rel="stylesheet"> from AJAX-injected content into <head>.
 *  Browsers ignore <link> tags set via innerHTML; we must re-inject them. */
function reLoadStyles(container: HTMLElement): void {
  container.querySelectorAll('link[rel="stylesheet"]').forEach((link) => {
    const href = link.getAttribute("href");
    if (!href) return;
    // Skip if already loaded in <head>
    if (document.querySelector(`head link[href="${href}"]`)) {
      link.remove();
      return;
    }
    const el = document.createElement("link");
    el.rel = "stylesheet";
    el.href = href;
    document.head.appendChild(el);
    link.remove();
  });
}

function updateActiveTab(name: string): void {
  document.querySelectorAll(".module-tab-btn").forEach((btn) => {
    const href = btn.getAttribute("href") ?? "";
    const isActive =
      href.includes(`/${name}/`) || btn.getAttribute("data-module") === name;
    btn.classList.toggle("active", isActive);
  });
}

function initTabBar(): void {
  document.querySelectorAll(".module-tab-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const href = (btn as HTMLAnchorElement).href ?? "";
      // Detect module name from href pattern /<module>/
      const match = href.match(/\/([a-z0-9_-]+)\/?(?:\?.*)?$/i);
      if (!match) return;
      const module = match[1];
      if (KNOWN_MODULES.includes(module)) {
        e.preventDefault();
        void switchModule(module);
      }
    });
  });
}

// Pane hints routed through /chat/ and /files/ — they select a shell
// pane, not a registry module, so they must not be fetched as module
// content (there is no /apps/workspace/content/chat/).
const PANE_HINTS = ["chat", "editor"];

function getInitialModule(): string {
  // 1. Server-rendered active module — set from the URL by the view.
  //    Module index routes like /apps/discovery/ render the shell
  //    directly and do NOT match the /workspace/<module>/ pattern
  //    below; without this the shell fell through to localStorage and
  //    loaded whatever module the user last used (usually "home"),
  //    so the Discovery tile appeared to navigate to /apps/home/
  //    (nav-404 batch #2).
  const served = document
    .getElementById("workspace-shell")
    ?.getAttribute("data-active-module");
  if (served && !PANE_HINTS.includes(served)) return served;
  // 2. From URL path: /apps/workspace/<module>/ or /workspace/<module>/
  const pathMatch = location.pathname.match(/\/workspace\/([a-z0-9_-]+)\/?$/i);
  if (pathMatch && !PANE_HINTS.includes(pathMatch[1])) return pathMatch[1];
  // 3. From localStorage
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) return saved;
  // 4. Default
  return DEFAULT_MODULE;
}

function init(): void {
  KNOWN_MODULES = getKnownModules();
  initTabBar();
  const module = getInitialModule();
  void switchModule(module);

  // Handle browser back/forward via unified navigation engine
  window._appNav?.onRestore((state) => {
    if (state.module && KNOWN_MODULES.includes(state.module)) {
      void switchModule(state.module);
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
