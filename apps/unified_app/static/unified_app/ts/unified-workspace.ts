/**
 * Unified Workspace - module tab switching and state management.
 */

const STORAGE_KEY = "scitex-unified-active-module";

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

    // Update active tab in UI
    document.querySelectorAll(".unified-tab-btn").forEach((btn) => {
      btn.classList.toggle(
        "active",
        (btn as HTMLElement).dataset.module === name,
      );
    });

    // Update URL without full reload
    const newUrl = `/unified/${name === "files" ? "" : name + "/"}`;
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

    console.log(`[Unified] Switched to module: ${name}`);
  } catch (err) {
    center.innerHTML = `<div class="unified-center-error p-4 text-danger">Error loading module: ${String(err)}</div>`;
    console.error("[Unified] Module load error:", err);
  }
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
  return "files";
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
      autoLoadInitialModule();
    });
  } else {
    initTabBar();
    autoLoadInitialModule();
  }
}

export { switchModule, initTabBar };
