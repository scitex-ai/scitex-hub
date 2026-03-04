/**
 * Module tab switcher — intercepts tab bar clicks on workspace pages.
 *
 * When the three-column workspace layout is active, clicking a module tab
 * fetches the module partial from /workspace/content/<module>/ and injects
 * it into #main-content without a full page reload.
 * The AI pane and Worktree pane are never re-rendered.
 */

const CONTENT_BASE = "/workspace/content/";

/** Read module names from the DOM data attribute set by the registry context processor. */
function getKnownModules(): Set<string> {
  const nav = document.querySelector("[data-workspace-modules]");
  if (nav) {
    const csv = (nav as HTMLElement).dataset.workspaceModules ?? "";
    if (csv) return new Set(csv.split(","));
  }
  // Fallback: extract from tab bar links
  const names = new Set<string>();
  document.querySelectorAll(".module-tab-btn").forEach((btn) => {
    const href = (btn as HTMLAnchorElement).getAttribute("href") ?? "";
    const match = href.match(/^\/([a-z0-9_-]+)\/?$/i);
    if (match) names.add(match[1]);
  });
  return names;
}

let KNOWN_MODULES: Set<string>;

/** Extract the first path segment from a pathname, e.g. "/_writer/" -> "writer". */
function extractModule(path: string): string | null {
  const match = path.match(/^\/([a-z0-9_-]+)\//i);
  return match ? match[1] : null;
}

/** Fetch module partial and inject into #main-content. */
async function switchModule(name: string): Promise<void> {
  const pane = document.getElementById("main-content");
  if (!pane) return;

  // Skip if the full-page template already rendered this module's content.
  // The server-rendered page includes module-specific elements (e.g. .scholar-main)
  // that the partial does not — replacing them would destroy the details panel.
  const alreadyLoaded = pane.querySelector(`.${name}-workspace, .${name}-main`);
  if (alreadyLoaded && !pane.classList.contains("switching")) {
    updateActiveTab(name);
    return;
  }

  pane.classList.add("switching");

  // Lock height to prevent layout shift during content swap.
  const prevHeight = pane.offsetHeight;
  pane.style.minHeight = `${prevHeight}px`;

  try {
    const resp = await fetch(`${CONTENT_BASE}${name}/`, {
      headers: { "X-Workspace-Shell": "1" },
      credentials: "same-origin",
    });

    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }

    const html = await resp.text();
    pane.innerHTML = html;
    reExecScripts(pane);
    window._appNav?.push({ module: name });
    updateActiveTab(name);
  } catch (err) {
    console.error("[module-tab-switcher] Failed to load module:", name, err);
    // Fall back to normal navigation so the user still reaches the page.
    location.href = `/${name}/`;
  } finally {
    pane.classList.remove("switching");
    // Release height lock after new content has rendered.
    requestAnimationFrame(() => {
      pane.style.minHeight = "";
    });
  }
}

/**
 * Re-execute inline <script> elements injected via innerHTML.
 * Browsers do not run scripts inserted this way automatically.
 * Skips import maps (only one allowed per document) and link/style tags.
 */
function reExecScripts(container: HTMLElement): void {
  container.querySelectorAll("script").forEach((old) => {
    // Skip import maps — they conflict with the already-registered map
    if (old.type === "importmap") {
      old.remove();
      return;
    }
    const replacement = document.createElement("script");
    Array.from(old.attributes).forEach((attr) =>
      replacement.setAttribute(attr.name, attr.value),
    );
    replacement.textContent = old.textContent;
    old.replaceWith(replacement);
  });
}

/** Toggle the `active` class on tab buttons to reflect the new module. */
function updateActiveTab(name: string): void {
  document.querySelectorAll(".module-tab-btn").forEach((btn) => {
    const href = (btn as HTMLAnchorElement).href ?? "";
    const isActive = href.includes(`/${name}/`);
    btn.classList.toggle("active", isActive);
  });
  // Set module accent on the pane — workspace-sidebar.css [data-module-accent] selectors
  // resolve --module-accent-color which drives both tab highlight and pane top border.
  const pane = document.getElementById("main-content");
  if (pane) {
    pane.setAttribute("data-module-accent", name);
    // CSS [data-module-accent="<name>"] rules handle --module-accent-color resolution.
    // Clear any stale inline override so CSS takes effect.
    pane.style.removeProperty("--module-accent-color");
  }
}

function init(): void {
  // Always set accent for the initially active module (server-rendered).
  const activeTab = document.querySelector(".module-tab-btn.active");
  if (activeTab) {
    const mod =
      (activeTab as HTMLElement).dataset.module ??
      extractModule(
        (activeTab as HTMLAnchorElement).getAttribute("href") ?? "",
      );
    if (mod) updateActiveTab(mod);
  }

  // Tab switching via fetch only works with three-column workspace layout.
  if (!document.querySelector("#workspace-three-col.workspace-three-col"))
    return;

  // Populate known modules from DOM (set by registry context processor).
  KNOWN_MODULES = getKnownModules();

  // Intercept tab bar clicks.
  document.querySelectorAll(".module-tab-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const href = (btn as HTMLAnchorElement).href ?? "";
      const match = href.match(/\/([a-z0-9_-]+)\/?(?:\?.*)?$/i);
      if (!match) return;
      const mod = match[1];
      if (KNOWN_MODULES.has(mod)) {
        e.preventDefault();
        void switchModule(mod);
      }
    });
  });

  // Handle browser back/forward via unified navigation engine.
  window._appNav?.onRestore((state) => {
    const currentMod = extractModule(location.pathname);
    if (
      state.module &&
      state.module !== currentMod &&
      KNOWN_MODULES.has(state.module)
    ) {
      void switchModule(state.module);
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
