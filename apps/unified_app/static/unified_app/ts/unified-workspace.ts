/**
 * Unified Workspace - module tab switching and state management.
 * Header nav links act as tab switchers on /unified/ pages.
 */

const STORAGE_KEY = "scitex-unified-active-module";

/** Maps header nav href → unified module name */
const HREF_TO_MODULE: Record<string, string> = {
  "/writer/": "writer",
  "/scholar/": "scholar",
  "/vis/": "vis",
  "/vis/editor/": "vis",
  "/console/": "console",
  "/console/workspace/": "console",
  "/clew/": "clew",
  "/hub/": "hub",
};

const moduleInitializers: Map<string, () => void> = new Map();

/** Register a module initialization function (plugin API). */
export function registerModuleInit(name: string, fn: () => void): void {
  moduleInitializers.set(name, fn);
}

function getCsrfToken(): string {
  const meta = document.querySelector(
    'meta[name="csrf-token"]',
  ) as HTMLMetaElement;
  if (meta) return meta.content;
  const input = document.querySelector(
    'input[name="csrfmiddlewaretoken"]',
  ) as HTMLInputElement;
  if (input) return input.value;
  const cookie = document.cookie
    .split(";")
    .find((c) => c.trim().startsWith("csrftoken="));
  return cookie ? cookie.split("=")[1].trim() : "";
}

async function switchModule(name: string, partialUrl: string): Promise<void> {
  const center = document.getElementById("unified-center");
  if (!center) return;

  center.innerHTML =
    '<div class="unified-center-loading"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';

  try {
    const response = await fetch(partialUrl, {
      headers: {
        "X-Unified-Module": "1",
        "X-CSRFToken": getCsrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
    });

    if (!response.ok) {
      center.innerHTML = `<div class="unified-center-error p-4 text-danger">Failed to load module (${response.status})</div>`;
      return;
    }

    const html = await response.text();
    center.innerHTML = html;

    // Move injected <link rel="stylesheet"> tags to <head> so browser fetches CSS
    center.querySelectorAll('link[rel="stylesheet"]').forEach((link) => {
      const href = (link as HTMLLinkElement).href;
      if (href && !document.querySelector(`link[href="${href}"]`)) {
        document.head.appendChild(link); // moves node from center to head
      } else {
        link.remove(); // duplicate — discard
      }
    });

    // Execute injected <script> tags (innerHTML doesn't run them natively)
    center.querySelectorAll("script").forEach((oldScript) => {
      const newScript = document.createElement("script");
      if ((oldScript as HTMLScriptElement).src) {
        newScript.src = (oldScript as HTMLScriptElement).src;
        newScript.type = oldScript.type || "text/javascript";
        newScript.async = false;
      } else {
        if (oldScript.type) newScript.type = oldScript.type;
        newScript.textContent = oldScript.textContent;
      }
      Array.from(oldScript.attributes)
        .filter((a) => a.name !== "src" && a.name !== "type")
        .forEach((a) => newScript.setAttribute(a.name, a.value));
      oldScript.replaceWith(newScript);
    });

    // Update active tab in UI
    document.querySelectorAll(".unified-tab-btn").forEach((btn) => {
      btn.classList.toggle(
        "active",
        (btn as HTMLElement).dataset.module === name,
      );
    });

    // Update URL without full reload
    const newUrl = `/unified/${name === "hub" ? "" : name + "/"}`;
    history.pushState({ module: name }, "", newUrl);

    // Save to localStorage
    localStorage.setItem(STORAGE_KEY, name);

    // Call module init if registered
    const initFn = moduleInitializers.get(name);
    if (initFn) {
      try {
        initFn();
      } catch (e) {
        console.warn(`[Unified] Module init failed for ${name}:`, e);
      }
    }

    // Update header nav active state
    updateHeaderNavActive(name);

    // Dispatch resize so canvas/xterm re-render to correct dimensions
    setTimeout(() => window.dispatchEvent(new Event("resize")), 100);

    // Notify cached ES modules (they don't re-run on second switch)
    document.dispatchEvent(
      new CustomEvent("unified:module:switched", { detail: { module: name } }),
    );

    console.log(`[Unified] Switched to module: ${name}`);
  } catch (err) {
    center.innerHTML = `<div class="unified-center-error p-4 text-danger">Error loading module: ${String(err)}</div>`;
    console.error("[Unified] Module load error:", err);
  }
}

function updateHeaderNavActive(moduleName: string): void {
  document.querySelectorAll(".header-nav-item").forEach((el) => {
    const href = (el as HTMLAnchorElement).getAttribute("href") || "";
    const mapped = HREF_TO_MODULE[href] || HREF_TO_MODULE[href + "/"];
    el.classList.toggle("active", mapped === moduleName);
  });
}

/** Intercept global header nav clicks on /unified/ pages to switch modules inline. */
function interceptHeaderNav(): void {
  document.querySelectorAll(".header-nav-item").forEach((link) => {
    link.addEventListener("click", (e) => {
      const href = (link as HTMLAnchorElement).getAttribute("href") || "";
      const moduleName = HREF_TO_MODULE[href] || HREF_TO_MODULE[href + "/"];
      if (!moduleName) return; // not a known module — let it navigate normally

      const btn = document.querySelector(
        `[data-module="${moduleName}"][data-mode="partial"]`,
      ) as HTMLElement | null;
      if (btn && btn.dataset.partialUrl) {
        e.preventDefault();
        e.stopPropagation();
        switchModule(moduleName, btn.dataset.partialUrl);
      }
    });
  });
}

function initTabBar(): void {
  const tabBar = document.getElementById("unified-tab-bar");
  if (!tabBar) return;

  tabBar.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest(
      "[data-module]",
    ) as HTMLElement;
    if (!btn) return;

    const mode = btn.dataset.mode;
    if (mode === "external") return; // Let the <a> tag handle navigation

    e.preventDefault();
    e.stopPropagation();

    const moduleName = btn.dataset.module;
    const partialUrl = btn.dataset.partialUrl;
    if (moduleName && partialUrl) {
      switchModule(moduleName, partialUrl);
    }
  });
}

function getInitialModule(): string {
  // 1. From URL path: /unified/scholar/ -> "scholar"
  const pathMatch = window.location.pathname.match(/^\/unified\/([^/]+)\//);
  if (pathMatch && pathMatch[1]) return pathMatch[1];

  // 2. From localStorage
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) return saved;

  // 3. Default
  return "hub";
}

function autoLoadInitialModule(): void {
  const center = document.getElementById("unified-center");
  if (!center) return;

  const moduleName = getInitialModule();
  const btn = document.querySelector(
    `[data-module="${moduleName}"][data-mode="partial"]`,
  ) as HTMLElement | null;

  if (btn && btn.dataset.partialUrl) {
    switchModule(moduleName, btn.dataset.partialUrl);
  }
}

// Auto-initialize on DOMContentLoaded
if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      initTabBar();
      interceptHeaderNav();
      autoLoadInitialModule();
    });
  } else {
    initTabBar();
    interceptHeaderNav();
    autoLoadInitialModule();
  }
}

export { switchModule, initTabBar };
