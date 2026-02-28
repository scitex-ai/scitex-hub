/**
 * Module Tab Context Menu — right-click on module tabs to manage them.
 *
 * Actions: Disable, Uninstall, View in Apps.
 * Uses existing apps API endpoints.
 */

const APPS_API = "/apps/api";

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
): Promise<{ success: boolean; error?: string; message?: string }> {
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    credentials: "same-origin",
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
      label: "View in Apps",
      icon: "fa-store",
      cls: "",
      action: () => {
        window.location.href = `/apps/${moduleName}/`;
      },
    },
  ];

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
      hideMenu();
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

function init(): void {
  const tabBar = document.querySelector(".module-tab-bar");
  if (!tabBar) return;

  tabBar.addEventListener("contextmenu", (e) => {
    const target = (e.target as HTMLElement).closest(
      ".module-tab-btn",
    ) as HTMLElement | null;
    if (!target) return;

    const moduleName = target.dataset.module;
    if (!moduleName) return;

    e.preventDefault();
    showMenu((e as MouseEvent).clientX, (e as MouseEvent).clientY, moduleName);
  });

  // Dismiss on click outside or Escape
  document.addEventListener("mousedown", (e) => {
    if (activeMenu && !activeMenu.contains(e.target as Node)) {
      hideMenu();
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") hideMenu();
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
