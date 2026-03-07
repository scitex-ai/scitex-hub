/**
 * Module Tab Context Menu — right-click on module tabs or apps nav to manage them.
 *
 * Actions: Disable, Uninstall, Accent Color, View in Apps, View in Hub.
 * Uses existing apps API endpoints.
 */

const APPS_API = "/apps/api";

const COLOR_SWATCHES = [
  { name: "Default", value: "" },
  { name: "Blue", value: "#388bfd" },
  { name: "Green", value: "#3d7a5e" },
  { name: "Purple", value: "#6a5a8a" },
  { name: "Amber", value: "#a07040" },
  { name: "Teal", value: "#2e7070" },
  { name: "Rose", value: "#7a5a6a" },
  { name: "Red", value: "#d35050" },
  { name: "Slate", value: "#5a6a8a" },
];

function getCsrfToken(): string {
  return (
    document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
      ?.value ||
    document.cookie
      .split("; ")
      .find((c) => c.startsWith("csrftoken="))
      ?.split("=")[1] ||
    ""
  );
}

async function apiPost(
  url: string,
  body?: object,
): Promise<{ success: boolean; error?: string; message?: string }> {
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    credentials: "same-origin",
    body: body ? JSON.stringify(body) : undefined,
  });
  return resp.json();
}

let activeMenu: HTMLDivElement | null = null;

function hideMenu(): void {
  if (activeMenu) {
    activeMenu.remove();
    activeMenu = null;
  }
}

function showMenu(x: number, y: number, moduleName: string): void {
  hideMenu();

  const menu = document.createElement("div");
  menu.className = "module-ctx-menu";

  const items = [
    {
      label: "Disable",
      icon: "fa-eye-slash",
      cls: "module-ctx-disable",
      action: () => toggleModule(moduleName),
    },
    {
      label: "Uninstall",
      icon: "fa-trash-alt",
      cls: "module-ctx-uninstall",
      action: () => uninstallModule(moduleName),
    },
    { separator: true },
    {
      label: "Accent Color",
      icon: "fa-palette",
      cls: "module-ctx-color",
      action: () => showColorSubmenu(menu, moduleName),
    },
    { separator: true },
    {
      label: "View in Apps",
      icon: "fa-store",
      cls: "",
      action: () => {
        window.location.href = `/apps/${moduleName}/`;
      },
    },
    {
      label: "View in Hub",
      icon: "fa-code-branch",
      cls: "",
      action: () => {
        window.location.href = `/hub/#browse/${moduleName}`;
      },
    },
  ];

  // Dev apps get a "Submit to App Store" option
  if (moduleName.startsWith("dev__")) {
    items.push({ separator: true });
    items.push({
      label: "Submit to App Store",
      icon: "fa-upload",
      cls: "module-ctx-submit",
      action: () => submitDevApp(moduleName),
    });
  }

  for (const item of items) {
    if (item.separator) {
      const sep = document.createElement("div");
      sep.className = "module-ctx-separator";
      menu.appendChild(sep);
      continue;
    }

    const el = document.createElement("div");
    el.className = `module-ctx-item ${item.cls || ""}`;
    el.innerHTML = `
      <span class="module-ctx-icon"><i class="fas ${item.icon}"></i></span>
      <span class="module-ctx-label">${item.label}</span>
    `;
    el.addEventListener("click", (e) => {
      e.stopPropagation();
      if (item.cls !== "module-ctx-color") {
        hideMenu();
      }
      item.action!();
    });
    menu.appendChild(el);
  }

  menu.style.position = "fixed";
  menu.style.left = `${x}px`;
  menu.style.top = `${y}px`;
  menu.style.zIndex = "99999";
  document.body.appendChild(menu);

  // Adjust if off-screen
  const rect = menu.getBoundingClientRect();
  if (rect.right > window.innerWidth) {
    menu.style.left = `${window.innerWidth - rect.width - 10}px`;
  }
  if (rect.bottom > window.innerHeight) {
    menu.style.top = `${window.innerHeight - rect.height - 10}px`;
  }

  activeMenu = menu;
}

function showColorSubmenu(parentMenu: HTMLElement, moduleName: string): void {
  // Toggle: remove if already open
  const existing = parentMenu.querySelector(".module-ctx-color-panel");
  if (existing) {
    existing.remove();
    return;
  }

  const panel = document.createElement("div");
  panel.className = "module-ctx-color-panel";

  for (const swatch of COLOR_SWATCHES) {
    const dot = document.createElement("button");
    dot.className = "module-ctx-swatch";
    dot.title = swatch.name;
    if (swatch.value) {
      dot.style.background = swatch.value;
    } else {
      dot.classList.add("module-ctx-swatch-default");
    }
    dot.addEventListener("click", (e) => {
      e.stopPropagation();
      hideMenu();
      setModuleColor(moduleName, swatch.value);
    });
    panel.appendChild(dot);
  }
  parentMenu.appendChild(panel);
}

async function setModuleColor(
  moduleName: string,
  color: string,
): Promise<void> {
  const data = await apiPost(`${APPS_API}/${moduleName}/config/`, {
    config: { accent_color: color || null },
  });
  if (!data.success) {
    console.error("[module-ctx] Config error:", data.error);
    return;
  }
  applyModuleColor(moduleName, color);
}

function applyModuleColor(moduleName: string, color: string): void {
  // Apply to tab bar + apps nav items
  const sel = `[data-module="${moduleName}"]`;
  document.querySelectorAll<HTMLElement>(sel).forEach((el) => {
    if (color) {
      el.style.setProperty("--module-accent-color", color);
    } else {
      el.style.removeProperty("--module-accent-color");
    }
  });

  // Apply to the module pane top accent bar (#main-content[data-module-accent])
  const pane = document.querySelector<HTMLElement>(
    `#main-content[data-module-accent="${moduleName}"]`,
  );
  if (pane) {
    if (color) {
      pane.style.setProperty("--module-accent-color", color);
    } else {
      pane.style.removeProperty("--module-accent-color");
    }
  }
}

function applySavedColors(): void {
  const colors = (window as any).SCITEX_MODULE_COLORS || {};
  for (const [name, color] of Object.entries(colors)) {
    if (color) applyModuleColor(name, color as string);
  }
}

async function submitDevApp(moduleName: string): Promise<void> {
  // Parse dev__<owner>__<repo>
  const parts = moduleName.split("__");
  if (parts.length < 3) {
    alert("Invalid dev app name format.");
    return;
  }
  const owner = parts[1];
  const repo = parts.slice(2).join("__");

  try {
    const data = await apiPost(`${APPS_API}/dev/${owner}/${repo}/submit/`);
    if (data.success) {
      const prUrl = (data as any).pr_url;
      alert(`App submitted! Review PR opened:\n${prUrl}`);
    } else {
      const errors = (data as any).errors;
      if (errors && Array.isArray(errors)) {
        alert(`Validation failed:\n\n${errors.join("\n")}`);
      } else {
        alert(data.error || "Submission failed.");
      }
    }
  } catch (err) {
    console.error("[module-ctx] Submit error:", err);
    alert("Failed to submit app.");
  }
}

async function toggleModule(name: string): Promise<void> {
  try {
    const data = await apiPost(`${APPS_API}/${name}/toggle/`);
    if (data.success) {
      location.reload();
    } else {
      alert(data.error || "Failed to toggle module.");
    }
  } catch (err) {
    console.error("[module-ctx] Toggle error:", err);
    alert("Failed to toggle module.");
  }
}

async function uninstallModule(name: string): Promise<void> {
  try {
    const data = await apiPost(`${APPS_API}/${name}/uninstall/`);
    if (data.success) {
      location.reload();
    } else {
      alert(data.error || "Failed to uninstall module.");
    }
  } catch (err) {
    console.error("[module-ctx] Uninstall error:", err);
    alert("Failed to uninstall module.");
  }
}

function handleContextMenu(selector: string) {
  return (e: Event) => {
    const target = (e.target as HTMLElement).closest(
      selector,
    ) as HTMLElement | null;
    if (!target) return;
    const moduleName = target.dataset.module;
    if (!moduleName) return;
    e.preventDefault();
    showMenu((e as MouseEvent).clientX, (e as MouseEvent).clientY, moduleName);
  };
}

function init(): void {
  // Tab bar
  const tabBar = document.querySelector(".module-tab-bar");
  if (tabBar) {
    tabBar.addEventListener(
      "contextmenu",
      handleContextMenu(".module-tab-btn"),
    );
  }

  // Apps nav pane
  const appsNav = document.querySelector(".ws-apps-nav");
  if (appsNav) {
    appsNav.addEventListener(
      "contextmenu",
      handleContextMenu(".ws-apps-nav-item"),
    );
  }

  // Dismiss on click outside or Escape
  document.addEventListener("mousedown", (e) => {
    if (activeMenu && !activeMenu.contains(e.target as Node)) {
      hideMenu();
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") hideMenu();
  });

  // Apply saved accent colors
  applySavedColors();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
